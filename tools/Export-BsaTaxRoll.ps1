<#
.SYNOPSIS
    Export tax-roll and taxable-value aggregates from the City's BS&A Tax and
    Assessing databases for the Property Taxes and City Finances dashboards.
    Aggregates only; never parcel rows.

.DESCRIPTION
    Runs on a workstation with the read-only BS&A helper and credential
    (C:\utils\BsaSql; db_datareader on the Tax and Assessing databases).
    Writes tools/data/bsa-taxroll.json, read by tools/build_propertytax.py and
    tools/fetch_finances.py.

    From the Tax module (one database per tax year, e.g. D004BURTON26):
      * City millage lines on the roll (tax unit classification 7, excluding
        the DDA district levy): code, mills, levy dollars, parcels billed.
      * Levy by taxing unit for the roll year (summer and winter where billed).
      * Median City tax on a homestead residential parcel (class 401, 100%
        principal residence exemption).
    From the Assessing module (D001City Of Burton <year>):
      * Taxable value total and by property class group on the current roll.
      * Taxable value and SEV history by year from ParcelPreviousYearTotals.

.EXAMPLE
    .\tools\Export-BsaTaxRoll.ps1 -TaxYear 2026
#>
[CmdletBinding()]
param(
    [ValidateRange(2010, 2100)]
    [int]$TaxYear = 2026,

    [string]$TaxDatabase,

    [string]$AssessingDatabase,

    [ValidateRange(2000, 2100)]
    [int]$HistoryFrom = 2010,

    [string]$OutPath = (Join-Path $PSScriptRoot 'data\bsa-taxroll.json')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

if (-not $TaxDatabase) { $TaxDatabase = 'D004BURTON{0}' -f $TaxYear.ToString().Substring(2) }
if (-not $AssessingDatabase) { $AssessingDatabase = 'D001City Of Burton {0}' -f $TaxYear }
if ($TaxDatabase -notmatch '^D004[A-Za-z0-9]+$') { throw "Unexpected Tax database name: $TaxDatabase" }
if ($AssessingDatabase -notmatch '^D001City Of Burton \d{4}$') { throw "Unexpected Assessing database name: $AssessingDatabase" }

function ConvertTo-WholeNumber([object]$v) { return [long][math]::Round([double]$v) }

# --- Tax module -----------------------------------------------------------------
$levySql = @"
SELECT d.taxHeaderCode AS code, d.tax_unit_classification AS classification, h.billing_type AS season,
       MAX(d.mills) AS mills, COUNT(DISTINCT b.parcelnumber) AS parcels, SUM(x.amount) AS levy
FROM dbo.ParcelTaxBillDetails x
JOIN dbo.UnitTaxNameDetails d ON d.id = x.idUnitTaxNameDetail
JOIN dbo.UnitTaxNameHeaders h ON h.id = d.idTaxNameHeader
JOIN dbo.ParcelTaxBills b ON b.id = x.idParcelTaxBill
GROUP BY d.taxHeaderCode, d.tax_unit_classification, h.billing_type
HAVING SUM(x.amount) > 0
ORDER BY levy DESC
"@

$homesteadSql = @"
WITH city AS (
    SELECT b.parcelnumber, SUM(x.amount) AS city_tax
    FROM dbo.ParcelTaxBillDetails x
    JOIN dbo.UnitTaxNameDetails d ON d.id = x.idUnitTaxNameDetail
    JOIN dbo.ParcelTaxBills b ON b.id = x.idParcelTaxBill
    JOIN dbo.Parcels p ON p.parcelnumber = b.parcelnumber
    WHERE d.tax_unit_classification = 7 AND d.taxHeaderCode <> 'DDA'
      AND p.prop_class = '401' AND p.homestead_percent >= 100 AND p.taxable_value > 0
    GROUP BY b.parcelnumber
),
ranked AS (SELECT city_tax, ROW_NUMBER() OVER (ORDER BY city_tax) AS rn, COUNT(*) OVER () AS n FROM city)
SELECT (SELECT COUNT(*) FROM city) AS parcels,
       (SELECT TOP 1 city_tax FROM ranked WHERE rn = (n + 1) / 2) AS median_city_tax
"@

# Collection to date for the current roll: what was billed per season, what is
# still owed, how many parcels are unpaid, and the weekly flow of payments.
# Season due dates come from the Units table (interest start date).
$collectionSql = @"
SELECT (SELECT MIN(intrst_duedate_0) FROM dbo.Units) AS summer_due,
       (SELECT MIN(intrst_duedate_1) FROM dbo.Units) AS winter_due,
       SUM(CASE WHEN tax_billed_0 > 0 THEN 1 ELSE 0 END) AS parcels_billed_summer,
       SUM(tax_billed_0) AS billed_summer, SUM(CASE WHEN tax_billed_0 > 0 THEN base_tax_left_0 ELSE 0 END) AS owed_summer,
       SUM(CASE WHEN tax_billed_0 > 0 AND base_tax_left_0 > 0 THEN 1 ELSE 0 END) AS parcels_unpaid_summer,
       SUM(CASE WHEN tax_billed_1 > 0 AND base_tax_left_1 < tax_billed_1 THEN 1 ELSE 0 END) AS parcels_paid_winter,
       SUM(tax_billed_1) AS billed_winter, SUM(CASE WHEN tax_billed_1 > 0 THEN base_tax_left_1 ELSE 0 END) AS owed_winter
FROM dbo.Parcels
"@
$weeklySql = @"
SELECT MIN(CAST(posting_date AS date)) AS week_start, SUM(amt) AS amount, COUNT(*) AS receipts
FROM dbo.ReceiptHeaders
WHERE billing_type = 0 AND transdesccode = 1
GROUP BY DATEPART(year, posting_date), DATEPART(week, posting_date)
ORDER BY week_start
"@
$sourceSql = @"
SELECT payment_src AS src, SUM(amt) AS amount, COUNT(*) AS receipts
FROM dbo.ReceiptHeaders WHERE billing_type = 0 AND transdesccode = 1 GROUP BY payment_src
"@

$levy = @(Invoke-BsaQuery -Database $TaxDatabase -Sql $levySql)
$homestead = Invoke-BsaQuery -Database $TaxDatabase -Sql $homesteadSql
$collection = Invoke-BsaQuery -Database $TaxDatabase -Sql $collectionSql
$weekly = @(Invoke-BsaQuery -Database $TaxDatabase -Sql $weeklySql)
$sources = @(Invoke-BsaQuery -Database $TaxDatabase -Sql $sourceSql)
if (-not $collection -or [int]$collection.parcels_billed_summer -lt 1000) { throw 'Collection query returned an implausible parcel count; refusing to write.' }
if ($levy.Count -lt 5) { throw "Levy query returned only $($levy.Count) rows; refusing to write." }
if (-not $homestead -or [int]$homestead.parcels -lt 1000) { throw 'Homestead query returned an implausible parcel count; refusing to write.' }

$cityLines = @($levy | Where-Object { [int]$_.classification -eq 7 -and $_.code -ne 'DDA' })
if ($cityLines.Count -lt 2) { throw 'Fewer than two City millage lines found; check tax_unit_classification.' }
$cityMills = [math]::Round((($cityLines | Measure-Object mills -Sum).Sum), 4)

# --- Assessing module -------------------------------------------------------------
$classSql = @"
SELECT propclass, COUNT(*) AS parcels, SUM(MborTaxableFullCpi) AS taxable, SUM(mborsev) AS sev
FROM dbo.Parcels WHERE mborsev > 0 GROUP BY propclass ORDER BY propclass
"@
$historySql = @"
SELECT year, SUM(mbortax) AS taxable, SUM(mborsev) AS sev
FROM dbo.ParcelPreviousYearTotals WHERE year >= $HistoryFrom AND year < $TaxYear
GROUP BY year ORDER BY year
"@
$classes = @(Invoke-BsaQuery -Database $AssessingDatabase -Sql $classSql)
$history = @(Invoke-BsaQuery -Database $AssessingDatabase -Sql $historySql)
if ($classes.Count -lt 3) { throw 'Class query returned too few rows; refusing to write.' }

# Michigan property class codes: first digit 2 commercial, 3 industrial, 4 residential,
# 5 utility; x51 codes are personal property. Group for the public chart.
function Get-ClassGroup([string]$code) {
    if ($code -match '^[2345]5\d$') { return 'Personal property (business and utility)' }
    switch ($code.Substring(0, 1)) {
        '2' { return 'Commercial' }
        '3' { return 'Industrial' }
        '4' { return 'Residential' }
        '5' { return 'Utility' }
        default { return 'Other' }
    }
}
$groups = @{}
foreach ($c in $classes) {
    $g = Get-ClassGroup ([string]$c.propclass)
    if (-not $groups.ContainsKey($g)) { $groups[$g] = [ordered]@{ group = $g; parcels = 0; taxable = [long]0; sev = [long]0 } }
    $groups[$g].parcels += [int]$c.parcels
    $groups[$g].taxable += ConvertTo-WholeNumber $c.taxable
    $groups[$g].sev += ConvertTo-WholeNumber $c.sev
}
$totalTaxable = ConvertTo-WholeNumber (($classes | Measure-Object taxable -Sum).Sum)
$totalSev = ConvertTo-WholeNumber (($classes | Measure-Object sev -Sum).Sum)

$out = [ordered]@{
    _source        = "City of Burton BS&A Tax module ($TaxDatabase) and Assessing module ($AssessingDatabase), read-only aggregate export. Levy = sum of billed tax lines by taxing unit; City millage = tax unit classification 7 excluding the DDA district levy; homestead median = class 401 parcels with a 100 percent principal residence exemption. Taxable value = March Board of Review taxable value on the roll; history from ParcelPreviousYearTotals."
    extracted      = (Get-Date).ToString('yyyy-MM-dd')
    tax_year       = $TaxYear
    city_mills     = $cityMills
    city_lines     = @($cityLines | ForEach-Object {
        [ordered]@{ code = [string]$_.code; mills = [double]$_.mills; levy = ConvertTo-WholeNumber $_.levy; parcels = [int]$_.parcels }
    })
    levy_by_unit   = @($levy | ForEach-Object {
        [ordered]@{ code = [string]$_.code; classification = [int]$_.classification; season = [int]$_.season; mills = [double]$_.mills; levy = ConvertTo-WholeNumber $_.levy; parcels = [int]$_.parcels }
    })
    homestead      = [ordered]@{ parcels = [int]$homestead.parcels; median_city_tax = [math]::Round([double]$homestead.median_city_tax, 2) }
    collection     = [ordered]@{
        as_of                 = (Get-Date).ToString('yyyy-MM-dd')
        summer_due            = ([datetime]$collection.summer_due).ToString('yyyy-MM-dd')
        winter_due            = ([datetime]$collection.winter_due).ToString('yyyy-MM-dd')
        summer                = [ordered]@{
            parcels_billed = [int]$collection.parcels_billed_summer
            billed         = ConvertTo-WholeNumber $collection.billed_summer
            owed           = ConvertTo-WholeNumber $collection.owed_summer
            parcels_unpaid = [int]$collection.parcels_unpaid_summer
        }
        winter                = [ordered]@{
            billed       = ConvertTo-WholeNumber $collection.billed_winter
            owed         = ConvertTo-WholeNumber $collection.owed_winter
            parcels_paid = [int]$collection.parcels_paid_winter
        }
        weekly_receipts_summer = @($weekly | ForEach-Object { [ordered]@{ week_start = ([datetime]$_.week_start).ToString('yyyy-MM-dd'); amount = ConvertTo-WholeNumber $_.amount; receipts = [int]$_.receipts } })
        payment_sources_summer = @($sources | ForEach-Object { [ordered]@{ source = [string]$_.src; amount = ConvertTo-WholeNumber $_.amount; receipts = [int]$_.receipts } })
    }
    taxable_value  = [ordered]@{
        year     = $TaxYear
        total    = $totalTaxable
        sev      = $totalSev
        by_group = @($groups.Values | Sort-Object taxable -Descending)
        history  = @($history | ForEach-Object { [ordered]@{ year = [int]$_.year; taxable = ConvertTo-WholeNumber $_.taxable; sev = ConvertTo-WholeNumber $_.sev } }) + @([ordered]@{ year = $TaxYear; taxable = $totalTaxable; sev = $totalSev })
    }
}

$json = $out | ConvertTo-Json -Depth 6
$tmp = Join-Path $env:TEMP 'bsa-taxroll.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  {0} roll: City {1} mills ({2}); homestead median City tax {3:N2} over {4:N0} parcels" -f $TaxYear, $cityMills, (($cityLines | ForEach-Object { "$($_.code) $($_.mills)" }) -join ', '), $out.homestead.median_city_tax, $out.homestead.parcels)
Write-Host ("  taxable value {0:N0} (SEV {1:N0}); history {2}-{3}" -f $totalTaxable, $totalSev, $HistoryFrom, $TaxYear)
