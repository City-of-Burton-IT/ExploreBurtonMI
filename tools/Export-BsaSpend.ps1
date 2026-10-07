<#
.SYNOPSIS
    Export what the City paid its vendors, by fiscal year and spending category,
    from the BS&A Accounts Payable database for the City Finances dashboard.
    Aggregates only; never vendor names, invoice numbers or line descriptions.

.DESCRIPTION
    Runs on a workstation with the read-only BS&A helper and credential
    (C:\utils\BsaSql; db_datareader on D011BURTON). Writes
    tools/data/bsa-spend.json, read by tools/fetch_finances.py.

    Source: dbo.Invoices (voided = 0; invoiceDate sets the fiscal year, July
    through June, so FY2026 is July 2025 to June 2026) joined to
    dbo.InvoiceLineItemDistributions, whose GLNum is fund-department-object
    (101-265-818.000). Each fund-object cell is assigned a spending category
    from the object code with a few fund-specific rules (see Get-SpendCategory;
    the same map is replayed by the builder from the exported cells).

    Fund 703 is the tax collection agency fund: property taxes the Treasurer
    collects for the schools, the County and the State and passes on (objects
    222.x and 225.x). It is most of the dollars and none of it is City spending,
    so it is reported as its own pass-through line and kept out of every City
    category and total.

    Vendor concentration is exported as a share only (the ten largest payees'
    share of City spending); no payee is ever named or counted individually.

.EXAMPLE
    .\tools\Export-BsaSpend.ps1 -FirstFiscalYear 2016
#>
[CmdletBinding()]
param(
    [string]$Database = 'D011BURTON',

    [ValidateRange(2008, 2100)]
    [int]$FirstFiscalYear = 2016,

    [string]$OutPath = (Join-Path $PSScriptRoot 'data\bsa-spend.json')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

if ($Database -notmatch '^D011[A-Za-z0-9]+$') { throw "Unexpected Accounts Payable database name: $Database" }

$Categories = [ordered]@{
    passthrough        = 'Taxes collected for schools, the County and the State'
    water_purchase     = 'Water bought from the regional system'
    sewage_treatment   = 'Sewage treatment by the County'
    trash              = 'Trash and recycling pickup'
    streets            = 'Street and road projects'
    utility_projects   = 'Water and sewer system projects'
    debt               = 'Loan and bond payments'
    insurance_benefits = 'Insurance, pensions and employee benefits'
    utilities          = 'Utilities and street lighting'
    vehicles_equipment = 'Vehicles, equipment, buildings and parks'
    services           = 'Contracted and professional services'
    supplies           = 'Supplies and materials'
    other_operations   = 'Repairs, rentals, training and other operations'
    refunds_deposits   = 'Refunds, deposits returned and other payments'
    other              = 'Other'
}
$StreetFunds = @('202', '203', '451')
$UtilityFunds = @('590', '591')
$FundGroups = [ordered]@{
    '101' = 'General Fund'; '202' = 'Streets'; '203' = 'Streets'; '206' = 'Fire'; '207' = 'Police'
    '226' = 'Rubbish'; '590' = 'Sewer'; '591' = 'Water'; '661' = 'Motor Pool'; '636' = 'Information Technology'
}

function Get-SpendCategory([string]$Fund, [string]$Obj) {
    # Reference copy lives in tools/fetch_finances.py (classify_spend); keep both in step.
    $o = [int]$Obj
    if ($Fund -eq '703') { return 'passthrough' }
    if ($Fund -eq '591' -and $o -eq 816) { return 'water_purchase' }
    if ($Fund -eq '590' -and $o -eq 928) { return 'sewage_treatment' }
    if ($Fund -eq '226' -and $o -eq 830) { return 'trash' }
    if ($StreetFunds -contains $Fund -and ($o -in @(802, 818, 988) -or ($o -ge 970 -and $o -le 989))) { return 'streets' }
    # 562 and 582 are the state revolving-fund (DWRF/SRF) construction accounts used before FY2019;
    # 300.x in the utility funds are the loan liabilities those projects are repaid against.
    if ($UtilityFunds -contains $Fund -and $o -in @(58, 132, 136, 158, 562, 582, 971, 975, 977, 985)) { return 'utility_projects' }
    if ($UtilityFunds -contains $Fund -and $o -eq 300) { return 'debt' }
    if ($o -in @(950, 952, 991, 993, 994, 999)) { return 'debt' }
    if ($o -in @(123, 231, 237, 238, 239, 719, 831, 874, 875)) { return 'insurance_benefits' }
    if ($o -ge 920 -and $o -le 929) { return 'utilities' }
    if ($o -in @(101, 140, 146, 148, 571, 850, 863, 867, 868, 934, 974, 983) -or ($o -ge 970 -and $o -le 989)) { return 'vehicles_equipment' }
    if ($o -ge 800 -and $o -le 899) { return 'services' }
    if ($o -ge 700 -and $o -le 799) { return 'supplies' }
    if ($o -ge 900 -and $o -le 969) { return 'other_operations' }
    if ($o -lt 400 -or ($o -ge 600 -and $o -le 699)) { return 'refunds_deposits' }
    return 'other'
}

function ConvertTo-WholeNumber([object]$v) { if ($null -eq $v) { return [long]0 }; return [long][math]::Round([double]$v) }

$today = Get-Date
# The fiscal year that ended last June 30 is the latest complete one.
$latestComplete = $today.Year - 1
if ($today.Month -ge 7) { $latestComplete = $today.Year }
$currentFy = $latestComplete + 1
$fromDate = '{0}-07-01' -f ($FirstFiscalYear - 1)
$toDate = '{0}-07-01' -f $currentFy
$fyExpr = 'CASE WHEN MONTH(i.invoiceDate) >= 7 THEN YEAR(i.invoiceDate) + 1 ELSE YEAR(i.invoiceDate) END'
$glShape = "d.GLNum LIKE '[0-9][0-9][0-9]-[0-9][0-9][0-9]-[0-9][0-9][0-9].[0-9][0-9][0-9]'"

# --- Fund-object cells per fiscal year ---------------------------------------------
$cellSql = @"
SELECT $fyExpr AS fy, LEFT(d.GLNum, 3) AS fund, SUBSTRING(d.GLNum, 9, 3) AS obj,
       SUM(d.Amount) AS amount, COUNT(*) AS lines
FROM dbo.InvoiceLineItemDistributions d
JOIN dbo.Invoices i ON i.id = d.InvoiceID
WHERE i.voided = 0 AND i.invoiceDate >= '$fromDate' AND i.invoiceDate < '$toDate' AND $glShape
GROUP BY $fyExpr, LEFT(d.GLNum, 3), SUBSTRING(d.GLNum, 9, 3)
"@
$cells = @(Invoke-BsaQuery -Database $Database -Sql $cellSql)
if ($cells.Count -lt 500) { throw "Cell query returned only $($cells.Count) rows; refusing to write." }

# --- Invoice-level totals per fiscal year (reconciliation and vendor concentration) ----
$invoiceSql = @"
SELECT $fyExpr AS fy, COUNT(*) AS invoices, SUM(i.amount) AS amount, COUNT(DISTINCT i.vendorCode) AS vendors
FROM dbo.Invoices i
WHERE i.voided = 0 AND i.invoiceDate >= '$fromDate' AND i.invoiceDate < '$toDate'
GROUP BY $fyExpr
"@
$invoiceRows = @(Invoke-BsaQuery -Database $Database -Sql $invoiceSql)
$concentrationSql = @"
WITH v AS (
    SELECT $fyExpr AS fy, i.vendorCode, SUM(d.Amount) AS amt
    FROM dbo.InvoiceLineItemDistributions d
    JOIN dbo.Invoices i ON i.id = d.InvoiceID
    WHERE i.voided = 0 AND i.invoiceDate >= '$fromDate' AND i.invoiceDate < '$toDate' AND $glShape AND LEFT(d.GLNum, 3) <> '703'
    GROUP BY $fyExpr, i.vendorCode
),
ranked AS (SELECT fy, amt, ROW_NUMBER() OVER (PARTITION BY fy ORDER BY amt DESC) AS rn FROM v)
SELECT fy, SUM(CASE WHEN rn <= 10 THEN amt ELSE 0 END) AS top10, SUM(amt) AS total, COUNT(*) AS payees
FROM ranked GROUP BY fy
"@
$concentration = @(Invoke-BsaQuery -Database $Database -Sql $concentrationSql)
$malformedSql = @"
SELECT COUNT(*) AS n, ISNULL(SUM(d.Amount), 0) AS amount
FROM dbo.InvoiceLineItemDistributions d JOIN dbo.Invoices i ON i.id = d.InvoiceID
WHERE i.voided = 0 AND i.invoiceDate >= '$fromDate' AND i.invoiceDate < '$toDate' AND NOT ($glShape)
"@
$malformed = Invoke-BsaQuery -Database $Database -Sql $malformedSql

# --- Aggregate ----------------------------------------------------------------------
$byFy = @{}
$cellMap = @{}
foreach ($c in $cells) {
    $fy = [int]$c.fy
    $fund = [string]$c.fund
    $obj = [string]$c.obj
    $cat = Get-SpendCategory $fund $obj
    $amt = [double]$c.amount
    if (-not $byFy.ContainsKey($fy)) {
        $e = [ordered]@{ fiscal_year = $fy; categories = [ordered]@{}; fund_groups = [ordered]@{} }
        foreach ($k in $Categories.Keys) { $e.categories[$k] = [double]0 }
        $byFy[$fy] = $e
    }
    $e = $byFy[$fy]
    $e.categories[$cat] += $amt
    if ($cat -ne 'passthrough') {
        $g = 'Other funds'
        if ($FundGroups.Contains($fund)) { $g = $FundGroups[$fund] }
        elseif ($fund -like '4*') { $g = 'Capital projects' }
        if (-not $e.fund_groups.Contains($g)) { $e.fund_groups[$g] = [double]0 }
        $e.fund_groups[$g] += $amt
    }
    $key = "$fund-$obj"
    if (-not $cellMap.ContainsKey($key)) { $cellMap[$key] = [ordered]@{ fund = $fund; object = $obj; category = $cat; amount = [double]0; lines = [int]0 } }
    $cellMap[$key].amount += $amt
    $cellMap[$key].lines += [int]$c.lines
}

$years = @()
foreach ($fy in ($byFy.Keys | Sort-Object)) {
    $e = $byFy[$fy]
    $inv = $invoiceRows | Where-Object { [int]$_.fy -eq $fy }
    $con = $concentration | Where-Object { [int]$_.fy -eq $fy }
    if (-not $inv -or -not $con) { throw "Fiscal year $fy has cells but no invoice or concentration row; refusing to write." }
    $distTotal = ($e.categories.Values | Measure-Object -Sum).Sum
    $cityTotal = $distTotal - $e.categories['passthrough']
    $cats = [ordered]@{}
    foreach ($k in $Categories.Keys) { if ($k -ne 'passthrough') { $cats[$k] = ConvertTo-WholeNumber $e.categories[$k] } }
    $groups = [ordered]@{}
    foreach ($g in ($e.fund_groups.Keys | Sort-Object { $e.fund_groups[$_] } -Descending)) { $groups[$g] = ConvertTo-WholeNumber $e.fund_groups[$g] }
    $years += [ordered]@{
        fiscal_year          = $fy
        complete             = ($fy -le $latestComplete)
        invoices             = [int]$inv.invoices
        invoice_total        = ConvertTo-WholeNumber $inv.amount
        distribution_total   = ConvertTo-WholeNumber $distTotal
        passthrough          = ConvertTo-WholeNumber $e.categories['passthrough']
        city_total           = ConvertTo-WholeNumber $cityTotal
        payees               = [int]$con.payees
        top10_share          = [math]::Round(([double]$con.top10 / [double]$con.total), 4)
        categories           = $cats
        fund_groups          = $groups
    }
}

$unmapped = @($cellMap.Values | Where-Object { $_.category -eq 'other' } | Sort-Object { $_.amount } -Descending | Select-Object -First 15)
Write-Host "Fund-object cells in 'other' (largest first):"
foreach ($u in $unmapped) { Write-Host ("    {0}-{1,-4} {2,14:N0}" -f $u.fund, $u.object, $u.amount) }
Write-Host ("Malformed GL numbers skipped: {0} lines, {1:N0}" -f [int]$malformed.n, [double]$malformed.amount)

# --- Plausibility -------------------------------------------------------------------
$complete = @($years | Where-Object { $_.complete })
if ($complete.Count -lt 8) { throw "Only $($complete.Count) complete fiscal years; need at least 8. Refusing to write." }
foreach ($y in $complete) {
    if ($y.invoices -lt 2000 -or $y.invoices -gt 20000) { throw "FY$($y.fiscal_year) has $($y.invoices) invoices (expected 2,000 to 20,000); refusing to write." }
    if ($y.city_total -lt 10000000 -or $y.city_total -gt 150000000) { throw "FY$($y.fiscal_year) City total $($y.city_total) is outside 10M to 150M; refusing to write." }
    $share = $y.passthrough / ($y.passthrough + $y.city_total)
    if ($share -lt 0.25 -or $share -gt 0.75) { throw "FY$($y.fiscal_year) pass-through share $share is outside 25 to 75 percent; refusing to write." }
    $gap = [math]::Abs($y.invoice_total - $y.distribution_total)
    if ($gap -gt 0.005 * $y.invoice_total + [double]$malformed.amount) { throw "FY$($y.fiscal_year): invoice total and distribution total differ by $gap; refusing to write." }
    if ($y.categories['other'] -gt 0.05 * $y.city_total) { throw "FY$($y.fiscal_year): 'other' is more than 5 percent of City spending; extend the category map first." }
}
$latest = $complete | Where-Object { $_.fiscal_year -eq $latestComplete }
if (-not $latest) { throw "No row for the latest complete fiscal year FY$latestComplete; refusing to write." }

$out = [ordered]@{
    _source              = [ordered]@{
        server   = 'BURBSA01\BSA'
        database = $Database
        tables   = 'dbo.Invoices (voided = 0), dbo.InvoiceLineItemDistributions'
        note     = 'aggregates only; fiscal year from invoiceDate (July to June); fund 703 pass-through kept out of City totals; no payee is named'
    }
    extracted            = $today.ToString('yyyy-MM-dd')
    latest_complete_fy   = $latestComplete
    category_labels      = $Categories
    fund_groups          = $FundGroups
    street_funds         = $StreetFunds
    utility_funds        = $UtilityFunds
    malformed_gl_lines   = [ordered]@{ lines = [int]$malformed.n; amount = ConvertTo-WholeNumber $malformed.amount }
    by_fiscal_year       = $years
    cells                = @($cellMap.Values | Where-Object { [math]::Abs($_.amount) -ge 1000 } | Sort-Object { $_.amount } -Descending | ForEach-Object {
        [ordered]@{ fund = $_.fund; object = $_.object; category = $_.category; amount = ConvertTo-WholeNumber $_.amount; lines = $_.lines }
    })
}

$json = $out | ConvertTo-Json -Depth 8
$tmp = Join-Path $env:TEMP 'bsa-spend.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  FY{0}: {1:N0} invoices, City spending {2:N0}, pass-through {3:N0}, {4} payees, top ten {5:P0}" -f $latest.fiscal_year, $latest.invoices, $latest.city_total, $latest.passthrough, $latest.payees, $latest.top10_share)
foreach ($k in $latest.categories.Keys) { Write-Host ("    {0,-50} {1,14:N0}" -f $Categories[$k], $latest.categories[$k]) }
