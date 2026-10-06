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

# --- Revenue by source (uniform chart of accounts ranges), General Fund and all
# governmental funds (fund types 0 general, 1 special revenue, 2 debt, 3 capital),
# by fiscal year; and General Fund spending by department by fiscal year; and the
# Water (591) and Sewer (590) enterprise funds by year in resident-facing groups.
$sourcesSql = @"
WITH hist AS (
    SELECT YEAR(h.yearEnd) AS fy, h.fund, LEFT(h.account, 3) AS acct, -SUM(d.debitActivity - d.creditActivity) AS amt
    FROM dbo.GLHistoryPeriodDetails d JOIN dbo.GLHistory h ON h.id = d.glHistoryID
    WHERE h.accountCategory = 3 GROUP BY YEAR(h.yearEnd), h.fund, LEFT(h.account, 3)
),
cur AS (
    SELECT CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END AS fy, g.fund, LEFT(g.account, 3) AS acct,
           -SUM(p.debitActivity - p.creditActivity) AS amt
    FROM dbo.GLPeriodDetails p JOIN dbo.GL_GeneralLedger g ON g.id = p.generalLedgerID
    WHERE g.accountCategory = 3
    GROUP BY CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END, g.fund, LEFT(g.account, 3)
),
a AS (SELECT * FROM hist WHERE fy <= (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)
      UNION ALL SELECT * FROM cur WHERE fy > (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)),
g AS (SELECT a.fy, a.acct, a.amt, CASE WHEN a.fund = '101' THEN 1 ELSE 0 END AS gf,
             CASE WHEN f.type IN (0, 1, 2, 3) THEN 1 ELSE 0 END AS govt
      FROM a LEFT JOIN dbo.GL_Funds f ON f.fund = a.fund)
SELECT fy, scope,
    SUM(CASE WHEN acct BETWEEN '400' AND '449' THEN amt ELSE 0 END) AS taxes,
    SUM(CASE WHEN acct BETWEEN '450' AND '499' THEN amt ELSE 0 END) AS licenses_permits,
    SUM(CASE WHEN acct BETWEEN '500' AND '539' THEN amt ELSE 0 END) AS federal,
    SUM(CASE WHEN acct BETWEEN '540' AND '579' THEN amt ELSE 0 END) AS state_,
    SUM(CASE WHEN acct BETWEEN '580' AND '599' THEN amt ELSE 0 END) AS local_units,
    SUM(CASE WHEN acct BETWEEN '600' AND '654' THEN amt ELSE 0 END) AS charges,
    SUM(CASE WHEN acct BETWEEN '655' AND '663' THEN amt ELSE 0 END) AS fines,
    SUM(CASE WHEN acct BETWEEN '664' AND '669' THEN amt ELSE 0 END) AS interest,
    SUM(CASE WHEN acct BETWEEN '670' AND '694' THEN amt ELSE 0 END) AS other_,
    SUM(CASE WHEN acct BETWEEN '695' AND '699' THEN amt ELSE 0 END) AS transfers_in,
    SUM(CASE WHEN acct < '400' OR acct > '699' THEN amt ELSE 0 END) AS unclassified,
    SUM(amt) AS total
FROM (SELECT fy, acct, amt, 'general_fund' AS scope FROM g WHERE gf = 1
      UNION ALL SELECT fy, acct, amt, 'governmental' FROM g WHERE govt = 1) x
WHERE fy BETWEEN 2008 AND $priorEnd
GROUP BY fy, scope ORDER BY fy, scope
"@

$deptHistorySql = @"
WITH hist AS (
    SELECT YEAR(h.yearEnd) AS fy, h.department AS dept, SUM(d.debitActivity - d.creditActivity) AS amt
    FROM dbo.GLHistoryPeriodDetails d JOIN dbo.GLHistory h ON h.id = d.glHistoryID
    WHERE h.fund = '101' AND h.accountCategory = 4 GROUP BY YEAR(h.yearEnd), h.department
),
cur AS (
    SELECT CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END AS fy, g.department AS dept,
           SUM(p.debitActivity - p.creditActivity) AS amt
    FROM dbo.GLPeriodDetails p JOIN dbo.GL_GeneralLedger g ON g.id = p.generalLedgerID
    WHERE g.fund = '101' AND g.accountCategory = 4
    GROUP BY CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END, g.department
),
a AS (SELECT * FROM hist WHERE fy <= (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)
      UNION ALL SELECT * FROM cur WHERE fy > (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory))
SELECT a.fy, a.dept, MAX(n.d) AS name, SUM(a.amt) AS amt
FROM a LEFT JOIN (SELECT department, MAX(departmentDescription) AS d FROM dbo.GL_GeneralLedger WHERE fund = '101' GROUP BY department) n ON n.department = a.dept
WHERE a.fy BETWEEN 2008 AND $priorEnd
GROUP BY a.fy, a.dept HAVING SUM(a.amt) <> 0 ORDER BY a.fy, amt DESC
"@

$enterpriseSql = @"
WITH hist AS (
    SELECT YEAR(h.yearEnd) AS fy, h.fund, h.accountCategory AS cat, LEFT(h.account, 3) AS acct, SUM(d.debitActivity - d.creditActivity) AS amt
    FROM dbo.GLHistoryPeriodDetails d JOIN dbo.GLHistory h ON h.id = d.glHistoryID
    WHERE h.fund IN ('590', '591') AND h.accountCategory IN (3, 4) GROUP BY YEAR(h.yearEnd), h.fund, h.accountCategory, LEFT(h.account, 3)
),
cur AS (
    SELECT CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END AS fy, g.fund, g.accountCategory AS cat, LEFT(g.account, 3) AS acct,
           SUM(p.debitActivity - p.creditActivity) AS amt
    FROM dbo.GLPeriodDetails p JOIN dbo.GL_GeneralLedger g ON g.id = p.generalLedgerID
    WHERE g.fund IN ('590', '591') AND g.accountCategory IN (3, 4)
    GROUP BY CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END, g.fund, g.accountCategory, LEFT(g.account, 3)
),
a AS (SELECT * FROM hist WHERE fy <= (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)
      UNION ALL SELECT * FROM cur WHERE fy > (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory))
SELECT fy, fund,
    -SUM(CASE WHEN cat = 3 AND acct = '644' THEN amt ELSE 0 END) AS usage_fees,
    -SUM(CASE WHEN cat = 3 AND acct <> '644' THEN amt ELSE 0 END) AS other_revenue,
     SUM(CASE WHEN cat = 4 AND acct IN ('928', '816') THEN amt ELSE 0 END) AS treatment_purchase,
     SUM(CASE WHEN cat = 4 AND acct = '968' THEN amt ELSE 0 END) AS depreciation,
     SUM(CASE WHEN cat = 4 AND acct BETWEEN '990' AND '999' THEN amt ELSE 0 END) AS debt_and_transfers,
     SUM(CASE WHEN cat = 4 AND acct NOT IN ('928', '816', '968') AND NOT (acct BETWEEN '990' AND '999') THEN amt ELSE 0 END) AS operations
FROM a WHERE fy BETWEEN 2008 AND $priorEnd
GROUP BY fy, fund ORDER BY fund, fy
"@

$funds = @(Invoke-BsaQuery -Database $Database -Sql $fundSql)
$history = @(Invoke-BsaQuery -Database $Database -Sql $historySql -TimeoutSec 300)
$sources = @(Invoke-BsaQuery -Database $Database -Sql $sourcesSql -TimeoutSec 300)
$deptHistory = @(Invoke-BsaQuery -Database $Database -Sql $deptHistorySql -TimeoutSec 300)
$enterprise = @(Invoke-BsaQuery -Database $Database -Sql $enterpriseSql -TimeoutSec 300)

# Capital spending by year and fund group. Burton books construction in named
# project accounts (802.xxx), road preservation and repaving (818.200/818.500),
# CDBG paving (988.xxx) and capital outlay / equipment (700.xxx, 971, 977, 978).
# Loan principal (991.xxx) is debt service, not capital, and is excluded.
$capitalSql = @"
WITH hist AS (
    SELECT YEAR(h.yearEnd) AS fy, h.fund, h.account, SUM(d.debitActivity - d.creditActivity) AS amt
    FROM dbo.GLHistoryPeriodDetails d JOIN dbo.GLHistory h ON h.id = d.glHistoryID
    WHERE h.accountCategory = 4 GROUP BY YEAR(h.yearEnd), h.fund, h.account
),
cur AS (
    SELECT CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END AS fy, g.fund, g.account, SUM(p.debitActivity - p.creditActivity) AS amt
    FROM dbo.GLPeriodDetails p JOIN dbo.GL_GeneralLedger g ON g.id = p.generalLedgerID
    WHERE g.accountCategory = 4
    GROUP BY CASE WHEN MONTH(p.monthEnd) >= 7 THEN YEAR(p.monthEnd) + 1 ELSE YEAR(p.monthEnd) END, g.fund, g.account
),
a AS (SELECT * FROM hist WHERE fy <= (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)
      UNION ALL SELECT * FROM cur WHERE fy > (SELECT MAX(YEAR(yearEnd)) FROM dbo.GLHistory)),
c AS (SELECT fy, fund, amt FROM a
      WHERE LEFT(account, 3) IN ('802', '700', '971', '977', '978', '988') OR account IN ('818.200', '818.500'))
SELECT fy,
    SUM(amt) AS total,
    SUM(CASE WHEN fund IN ('202', '203') OR fund LIKE '35%' OR fund LIKE '45%' THEN amt ELSE 0 END) AS streets,
    SUM(CASE WHEN fund IN ('590', '591') THEN amt ELSE 0 END) AS water_sewer,
    SUM(CASE WHEN fund IN ('206', '207', '406') THEN amt ELSE 0 END) AS police_fire,
    SUM(CASE WHEN fund = '101' OR fund = '401' THEN amt ELSE 0 END) AS general,
    SUM(CASE WHEN fund = '661' THEN amt ELSE 0 END) AS motor_pool
FROM c WHERE fy BETWEEN 2008 AND $priorEnd GROUP BY fy ORDER BY fy
"@
$capital = @(Invoke-BsaQuery -Database $Database -Sql $capitalSql -TimeoutSec 300)
if ($capital.Count -lt 5) { throw 'Capital history returned too few years; refusing to write.' }
if ($sources.Count -lt 10 -or $deptHistory.Count -lt 20 -or $enterprise.Count -lt 10) { throw 'Revenue-source, department or enterprise history returned too few rows; refusing to write.' }
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

$sourceKeys = @('taxes', 'licenses_permits', 'federal', 'state_', 'local_units', 'charges', 'fines', 'interest', 'other_', 'transfers_in', 'unclassified', 'total')
$out['revenue_sources'] = @($sources | ForEach-Object {
    $row = [ordered]@{ fiscal_year_end = [int]$_.fy; scope = [string]$_.scope }
    foreach ($k in $sourceKeys) { $row[$k.TrimEnd('_')] = ConvertTo-WholeNumber $_.$k }
    $row
})
$out['department_history'] = @($deptHistory | ForEach-Object {
    [ordered]@{ fiscal_year_end = [int]$_.fy; code = [string]$_.dept; name = [string]$_.name; amount = ConvertTo-WholeNumber $_.amt }
})
$out['enterprise_funds'] = @($enterprise | ForEach-Object {
    [ordered]@{
        fiscal_year_end    = [int]$_.fy
        fund               = [string]$_.fund
        usage_fees         = ConvertTo-WholeNumber $_.usage_fees
        other_revenue      = ConvertTo-WholeNumber $_.other_revenue
        treatment_purchase = ConvertTo-WholeNumber $_.treatment_purchase
        operations         = ConvertTo-WholeNumber $_.operations
        depreciation       = ConvertTo-WholeNumber $_.depreciation
        debt_and_transfers = ConvertTo-WholeNumber $_.debt_and_transfers
    }
})
$out['capital_history'] = @($capital | ForEach-Object {
    [ordered]@{
        fiscal_year_end = [int]$_.fy
        total           = ConvertTo-WholeNumber $_.total
        streets         = ConvertTo-WholeNumber $_.streets
        water_sewer     = ConvertTo-WholeNumber $_.water_sewer
        police_fire     = ConvertTo-WholeNumber $_.police_fire
        general         = ConvertTo-WholeNumber $_.general
        motor_pool      = ConvertTo-WholeNumber $_.motor_pool
    }
})

$json = $out | ConvertTo-Json -Depth 6
$tmp = Join-Path $env:TEMP 'bsa-budget.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  {0}: revenue {1:N0}, expenditure {2:N0} (transfers out {3:N0}), {4} funds" -f $out.label, $totalRev, $totalExp, $totalXfer, $funds.Count)
Write-Host ("  General Fund: revenue {0:N0}, expenditure {1:N0}, transfers out {2:N0}, {3} departments" -f $out.general_fund.revenue, $out.general_fund.expenditure, $out.general_fund.transfers_out, $depts.Count)
