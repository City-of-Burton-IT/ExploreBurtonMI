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

$funds = @(Invoke-BsaQuery -Database $Database -Sql $fundSql)
$depts = @(Invoke-BsaQuery -Database $Database -Sql $deptSql)
$transfers = @(Invoke-BsaQuery -Database $Database -Sql $transferSql)

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

$json = $out | ConvertTo-Json -Depth 6
$tmp = Join-Path $env:TEMP 'bsa-budget.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  {0}: revenue {1:N0}, expenditure {2:N0} (transfers out {3:N0}), {4} funds" -f $out.label, $totalRev, $totalExp, $totalXfer, $funds.Count)
Write-Host ("  General Fund: revenue {0:N0}, expenditure {1:N0}, transfers out {2:N0}, {3} departments" -f $out.general_fund.revenue, $out.general_fund.expenditure, $out.general_fund.transfers_out, $depts.Count)
