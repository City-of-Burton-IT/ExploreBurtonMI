<#
.SYNOPSIS
    Export adopted-budget aggregates from the City's BS&A General Ledger for the
    City Finances dashboard. Aggregates only (fund and department totals).

.DESCRIPTION
    Decision 2026-10-06: the General Ledger is the source of truth for the
    adopted budget on Explore Burton, replacing figures typed from the budget
    book. Runs only on a workstation with the read-only BS&A helper and
    credential (C:\utils\BsaSql, db_datareader on D014BURTON). Writes
    tools/data/bsa-budget.json, read by tools/fetch_finances.py --budget-file.

    Figures come from BudgetInfoAdopted.originalBudget for the fiscal year
    (year = fiscal year END, so 2027 = FY2026-27) joined to GL_GeneralLedger;
    accountCategory 3 = revenue (stored negative, sign flipped here) and
    4 = expenditure. Transfers out are the expenditure lines whose account
    description contains TRANSFER.

.PARAMETER FiscalYearEnd
    Fiscal year end (2027 = FY2026-27).

.EXAMPLE
    .\tools\Export-BsaBudget.ps1 -FiscalYearEnd 2027
#>
[CmdletBinding()]
param(
    [ValidateRange(2010, 2100)]
    [int]$FiscalYearEnd = 2027,

    [ValidatePattern('^D014[A-Za-z0-9]+$')]
    [string]$Database = 'D014BURTON',

    [string]$OutPath = (Join-Path $PSScriptRoot 'data\bsa-budget.json')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

$fundSql = @"
SELECT b.fund, MAX(f.description) AS name,
       -SUM(CASE WHEN g.accountCategory = 3 THEN b.originalBudget ELSE 0 END) AS revenue,
       SUM(CASE WHEN g.accountCategory = 4 THEN b.originalBudget ELSE 0 END) AS expenditure,
       SUM(CASE WHEN g.accountCategory = 4 AND g.accountDescription LIKE '%TRANSFER%' THEN b.originalBudget ELSE 0 END) AS transfers_out
FROM dbo.BudgetInfoAdopted b
JOIN dbo.GL_GeneralLedger g ON g.id = b.generalLedgerID
LEFT JOIN dbo.GL_Funds f ON f.fund = b.fund
WHERE b.year = $FiscalYearEnd AND g.accountCategory IN (3, 4)
GROUP BY b.fund
HAVING SUM(ABS(b.originalBudget)) > 0
ORDER BY expenditure DESC
"@

$deptSql = @"
SELECT g.department AS code, MAX(g.departmentDescription) AS name, SUM(b.originalBudget) AS amount
FROM dbo.BudgetInfoAdopted b
JOIN dbo.GL_GeneralLedger g ON g.id = b.generalLedgerID
WHERE b.year = $FiscalYearEnd AND b.fund = '101' AND g.accountCategory = 4
GROUP BY g.department
HAVING SUM(b.originalBudget) <> 0
ORDER BY amount DESC
"@

$transferSql = @"
SELECT g.account, MAX(g.accountDescription) AS name, SUM(b.originalBudget) AS amount
FROM dbo.BudgetInfoAdopted b
JOIN dbo.GL_GeneralLedger g ON g.id = b.generalLedgerID
WHERE b.year = $FiscalYearEnd AND b.fund = '101' AND g.accountCategory = 4
  AND g.accountDescription LIKE '%TRANSFER%'
GROUP BY g.account
HAVING SUM(b.originalBudget) <> 0
ORDER BY amount DESC
"@

# --- Actuals: prior fiscal year complete, current fiscal year to date ----------
# GLPeriodDetails holds month-end activity per GL line. Revenue lines (category 3)
# carry credits, so revenue = credits - debits; expenditure = debits - credits.
# The prior year compares against the AMENDED budget (original + amendments);
# the current year to date compares against the adopted original.
$priorEnd = $FiscalYearEnd - 1
$priorFrom = '{0}-07-01' -f ($priorEnd - 1)
$priorTo = '{0}-06-30' -f $priorEnd
$ytdFrom = '{0}-07-01' -f ($FiscalYearEnd - 1)
$today = Get-Date
$ytdThrough = (Get-Date -Year $today.Year -Month $today.Month -Day 1).AddDays(-1)   # last completed month
if ($ytdThrough -lt [datetime]$ytdFrom) { $ytdThrough = $null }

$actualSql = @"
SELECT g.fund, MAX(f.description) AS name,
  -SUM(CASE WHEN g.accountCategory = 3 AND p.monthEnd BETWEEN '$priorFrom' AND '$priorTo' THEN p.debitActivity - p.creditActivity ELSE 0 END) AS prior_rev_actual,
   SUM(CASE WHEN g.accountCategory = 4 AND p.monthEnd BETWEEN '$priorFrom' AND '$priorTo' THEN p.debitActivity - p.creditActivity ELSE 0 END) AS prior_exp_actual
FROM dbo.GLPeriodDetails p
JOIN dbo.GL_GeneralLedger g ON g.id = p.generalLedgerID
LEFT JOIN dbo.GL_Funds f ON f.fund = g.fund
WHERE g.accountCategory IN (3, 4)
GROUP BY g.fund
"@

$priorBudgetSql = @"
SELECT b.fund,
  -SUM(CASE WHEN g.accountCategory = 3 THEN b.originalBudget + b.budgetAmendments ELSE 0 END) AS prior_rev_budget,
   SUM(CASE WHEN g.accountCategory = 4 THEN b.originalBudget + b.budgetAmendments ELSE 0 END) AS prior_exp_budget
FROM dbo.BudgetInfoAdopted b
JOIN dbo.GL_GeneralLedger g ON g.id = b.generalLedgerID
WHERE b.year = $priorEnd AND g.accountCategory IN (3, 4)
GROUP BY b.fund
"@

$ytdSql = if ($ytdThrough) { @"
SELECT g.fund,
  -SUM(CASE WHEN g.accountCategory = 3 THEN p.debitActivity - p.creditActivity ELSE 0 END) AS ytd_rev_actual,
   SUM(CASE WHEN g.accountCategory = 4 THEN p.debitActivity - p.creditActivity ELSE 0 END) AS ytd_exp_actual
FROM dbo.GLPeriodDetails p
JOIN dbo.GL_GeneralLedger g ON g.id = p.generalLedgerID
WHERE g.accountCategory IN (3, 4) AND p.monthEnd BETWEEN '$ytdFrom' AND '$($ytdThrough.ToString('yyyy-MM-dd'))'
GROUP BY g.fund
"@ } else { $null }

# --- Multi-year history: actual revenue and spending plus amended budgets ------
# Closed years live in GLHistory/GLHistoryPeriodDetails (yearEnd = June 30 of the
# fiscal year); the two most recent years are still in GLPeriodDetails. FY2007 is a
# partial first year in the ledger and is excluded.
$historySql = @"
WITH hist AS (
    SELECT YEAR(h.yearEnd) AS fy, h.fund, h.accountCategory AS cat, SUM(d.debitActivity - d.creditActivity) AS net
    FROM dbo.GLHistoryPeriodDetails d JOIN dbo.GLHistory h ON h.id = d.glHistoryID
    WHERE h.accountCategory IN (3, 4) GROUP BY YEAR(h.yearEnd), h.fund, h.accountCategory
),
cur AS (
    SELECT CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END AS fy,
           g.fund, g.accountCategory AS cat, SUM(p.debitActivity - p.creditActivity) AS net
    FROM dbo.GLPeriodDetails p JOIN dbo.GL_GeneralLedger g ON g.id = p.generalLedgerID
    WHERE g.accountCategory IN (3, 4)
    GROUP BY CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END, g.fund, g.accountCategory
),
act AS (SELECT * FROM hist WHERE fy <= (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)
        UNION ALL SELECT * FROM cur WHERE fy > (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)),
bud AS (
    SELECT b.year AS fy, b.fund, g.accountCategory AS cat, SUM(b.originalBudget + b.budgetAmendments) AS amended
    FROM dbo.BudgetInfoAdopted b JOIN dbo.GL_GeneralLedger g ON g.id = b.generalLedgerID
    WHERE g.accountCategory IN (3, 4) GROUP BY b.year, b.fund, g.accountCategory
)
SELECT fy,
    -SUM(CASE WHEN src = 'a' AND cat = 3 THEN v ELSE 0 END) AS rev_actual_all,
     SUM(CASE WHEN src = 'a' AND cat = 4 THEN v ELSE 0 END) AS exp_actual_all,
    -SUM(CASE WHEN src = 'a' AND cat = 3 AND fund = '101' THEN v ELSE 0 END) AS rev_actual_gf,
     SUM(CASE WHEN src = 'a' AND cat = 4 AND fund = '101' THEN v ELSE 0 END) AS exp_actual_gf,
    -SUM(CASE WHEN src = 'b' AND cat = 3 AND fund = '101' THEN v ELSE 0 END) AS rev_amended_gf,
     SUM(CASE WHEN src = 'b' AND cat = 4 AND fund = '101' THEN v ELSE 0 END) AS exp_amended_gf,
     SUM(CASE WHEN src = 'b' AND cat = 4 THEN v ELSE 0 END) AS exp_amended_all
FROM (SELECT fy, fund, cat, net AS v, 'a' AS src FROM act
      UNION ALL SELECT fy, fund, cat, amended, 'b' FROM bud) x
WHERE fy BETWEEN 2008 AND $priorEnd
GROUP BY fy ORDER BY fy
"@

$funds = @(Invoke-BsaQuery -Database $Database -Sql $fundSql)
$history = @(Invoke-BsaQuery -Database $Database -Sql $historySql -TimeoutSec 300)
if ($history.Count -lt 5) { throw "History query returned only $($history.Count) years; refusing to write." }
$depts = @(Invoke-BsaQuery -Database $Database -Sql $deptSql)
$transfers = @(Invoke-BsaQuery -Database $Database -Sql $transferSql)
$priorActual = @(Invoke-BsaQuery -Database $Database -Sql $actualSql)
$priorBudget = @(Invoke-BsaQuery -Database $Database -Sql $priorBudgetSql)
$ytdActual = if ($ytdSql) { @(Invoke-BsaQuery -Database $Database -Sql $ytdSql) } else { @() }

if ($funds.Count -lt 10) { throw "Fund query returned only $($funds.Count) funds; refusing to write." }
$gf = $funds | Where-Object { $_.fund -eq '101' } | Select-Object -First 1
if (-not $gf) { throw 'General Fund (101) missing from the fund query; refusing to write.' }

function ConvertTo-WholeNumber([object]$v) { return [long][math]::Round([double]$v) }

$totalRev = ConvertTo-WholeNumber (($funds | Measure-Object revenue -Sum).Sum)
$totalExp = ConvertTo-WholeNumber (($funds | Measure-Object expenditure -Sum).Sum)
$totalXfer = ConvertTo-WholeNumber (($funds | Measure-Object transfers_out -Sum).Sum)

$out = [ordered]@{
    _source         = "City of Burton BS&A General Ledger ($Database), read-only aggregate export of BudgetInfoAdopted.originalBudget for fiscal year end $FiscalYearEnd (FY$($FiscalYearEnd - 1)-$($FiscalYearEnd.ToString().Substring(2))). Revenue = account category 3, expenditure = category 4; transfers out = expenditure lines described as TRANSFER."
    extracted       = (Get-Date).ToString('yyyy-MM-dd')
    fiscal_year_end = $FiscalYearEnd
    label           = "FY$($FiscalYearEnd - 1)-$($FiscalYearEnd.ToString().Substring(2))"
    totals          = [ordered]@{ revenue = $totalRev; expenditure = $totalExp; transfers_out = $totalXfer }
    funds           = @($funds | ForEach-Object {
        [ordered]@{ fund = [string]$_.fund; name = [string]$_.name; revenue = ConvertTo-WholeNumber $_.revenue; expenditure = ConvertTo-WholeNumber $_.expenditure; transfers_out = ConvertTo-WholeNumber $_.transfers_out }
    })
    general_fund    = [ordered]@{
        revenue       = ConvertTo-WholeNumber $gf.revenue
        expenditure   = ConvertTo-WholeNumber $gf.expenditure
        transfers_out = ConvertTo-WholeNumber $gf.transfers_out
        departments   = @($depts | ForEach-Object { [ordered]@{ code = [string]$_.code; name = [string]$_.name; amount = ConvertTo-WholeNumber $_.amount } })
        transfers     = @($transfers | ForEach-Object { [ordered]@{ account = [string]$_.account; name = [string]$_.name; amount = ConvertTo-WholeNumber $_.amount } })
    }
}

# Prior-year budget vs actual per fund (amended budget), and current year to date.
$budgetByFund = @{}
foreach ($r in $priorBudget) { $budgetByFund[[string]$r.fund] = $r }
$priorFunds = @($priorActual | Where-Object { $budgetByFund.ContainsKey([string]$_.fund) } | ForEach-Object {
    $pb = $budgetByFund[[string]$_.fund]
    [ordered]@{
        fund                = [string]$_.fund
        name                = [string]$_.name
        revenue_budget      = ConvertTo-WholeNumber $pb.prior_rev_budget
        expenditure_budget  = ConvertTo-WholeNumber $pb.prior_exp_budget
        revenue_actual      = ConvertTo-WholeNumber $_.prior_rev_actual
        expenditure_actual  = ConvertTo-WholeNumber $_.prior_exp_actual
    }
} | Sort-Object { $_.expenditure_budget } -Descending)
if ($priorFunds.Count -lt 5) { throw 'Prior-year budget vs actual produced fewer than five funds; refusing to write.' }

$actuals = [ordered]@{
    prior_year = [ordered]@{
        fiscal_year_end = $priorEnd
        label           = "FY$($priorEnd - 1)-$($priorEnd.ToString().Substring(2))"
        funds           = $priorFunds
    }
}
if ($ytdThrough -and $ytdActual.Count -gt 0) {
    $ytdStart = [datetime]$ytdFrom
    $months = (($ytdThrough.Year - $ytdStart.Year) * 12 + $ytdThrough.Month - $ytdStart.Month) + 1
    $actuals['year_to_date'] = [ordered]@{
        fiscal_year_end = $FiscalYearEnd
        through         = $ytdThrough.ToString('yyyy-MM-dd')
        through_label   = $ytdThrough.ToString('MMMM yyyy')
        months          = [int]$months
        funds           = @($ytdActual | ForEach-Object {
            [ordered]@{ fund = [string]$_.fund; revenue_actual = ConvertTo-WholeNumber $_.ytd_rev_actual; expenditure_actual = ConvertTo-WholeNumber $_.ytd_exp_actual }
        })
    }
}
$out['actuals'] = $actuals
$out['history'] = @($history | ForEach-Object {
    [ordered]@{
        fiscal_year_end = [int]$_.fy
        general_fund    = [ordered]@{
            revenue_actual      = ConvertTo-WholeNumber $_.rev_actual_gf
            expenditure_actual  = ConvertTo-WholeNumber $_.exp_actual_gf
            revenue_amended     = ConvertTo-WholeNumber $_.rev_amended_gf
            expenditure_amended = ConvertTo-WholeNumber $_.exp_amended_gf
        }
        all_funds       = [ordered]@{
            revenue_actual      = ConvertTo-WholeNumber $_.rev_actual_all
            expenditure_actual  = ConvertTo-WholeNumber $_.exp_actual_all
            expenditure_amended = ConvertTo-WholeNumber $_.exp_amended_all
        }
    }
})

$json = $out | ConvertTo-Json -Depth 6
$tmp = Join-Path $env:TEMP 'bsa-budget.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  {0}: revenue {1:N0}, expenditure {2:N0} (transfers out {3:N0}), {4} funds" -f $out.label, $totalRev, $totalExp, $totalXfer, $funds.Count)
Write-Host ("  General Fund: revenue {0:N0}, expenditure {1:N0}, transfers out {2:N0}, {3} departments" -f $out.general_fund.revenue, $out.general_fund.expenditure, $out.general_fund.transfers_out, $depts.Count)
