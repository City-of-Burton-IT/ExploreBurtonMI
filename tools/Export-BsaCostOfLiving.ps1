<#
.SYNOPSIS
    Export residential aggregates from the City's BS&A Assessing database for the
    "What It Costs to Live Here" dashboard. Aggregates only; never parcel rows.

.DESCRIPTION
    Runs only on a workstation that has the read-only BS&A helper and credential
    (C:\utils\BsaSql, db_datareader on the Assessing database). Writes
    tools/data/bsa-residential.json, which tools/fetch_costofliving.py reads with
    --city-file. The JSON holds counts and medians, the extraction date, and the
    filters used, so the public site can cite them.

    Residential = property class 401. Sale medians use the assessor's own
    "arm's length" terms code and ignore prices of 10,000 dollars or less.

.PARAMETER Database
    Assessing database name (one database per assessment year).

.PARAMETER FirstSaleYear
    Earliest calendar year of sales to include in the trend.

.EXAMPLE
    .\tools\Export-BsaCostOfLiving.ps1 -Database 'D001City Of Burton 2026'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^D001City Of Burton \d{4}$')]
    [string]$Database,

    [ValidateRange(2010, 2100)]
    [int]$FirstSaleYear = 2019,

    [string]$OutPath = (Join-Path $PSScriptRoot 'data\bsa-residential.json')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

$assessmentYear = [int]($Database -replace '^.*?(\d{4})$', '$1')
$lastSaleYear = $assessmentYear - 1

$parcelSql = @"
WITH r AS (
    SELECT mborsev, MborTaxableFullCpi, homestead
    FROM dbo.Parcels
    WHERE propclass = '401' AND mborsev > 0
)
SELECT COUNT(*) AS parcels,
    (SELECT TOP 1 mborsev FROM (
        SELECT mborsev, ROW_NUMBER() OVER (ORDER BY mborsev) rn, COUNT(*) OVER () n FROM r) x
        WHERE rn = (n + 1) / 2) AS median_sev,
    (SELECT TOP 1 MborTaxableFullCpi FROM (
        SELECT MborTaxableFullCpi, ROW_NUMBER() OVER (ORDER BY MborTaxableFullCpi) rn, COUNT(*) OVER () n FROM r) x
        WHERE rn = (n + 1) / 2) AS median_taxable,
    SUM(CASE WHEN homestead >= 100 THEN 1 ELSE 0 END) AS pre_parcels
FROM r
"@

$salesSql = @"
WITH s AS (
    SELECT YEAR(saledate) AS yr, saleprice
    FROM dbo.Sales
    WHERE propclass = '401' AND saleprice > 10000 AND terms LIKE '03-ARM%'
      AND saledate >= '$FirstSaleYear-01-01' AND saledate < '$($lastSaleYear + 1)-01-01'
),
ranked AS (
    SELECT yr, saleprice,
        ROW_NUMBER() OVER (PARTITION BY yr ORDER BY saleprice) AS rn,
        COUNT(*) OVER (PARTITION BY yr) AS n
    FROM s
)
SELECT yr, MAX(n) AS sales, MAX(CASE WHEN rn = (n + 1) / 2 THEN saleprice END) AS median_price
FROM ranked
GROUP BY yr
ORDER BY yr
"@

$parcel = Invoke-BsaQuery -Database $Database -Sql $parcelSql
$sales = @(Invoke-BsaQuery -Database $Database -Sql $salesSql)

if (-not $parcel -or [int]$parcel.parcels -lt 1000) {
    throw "Parcel query returned an implausible count ($($parcel.parcels)); refusing to write."
}
if ($sales.Count -lt 1) {
    throw 'Sales query returned no years; refusing to write.'
}

$out = [ordered]@{
    _source          = "City of Burton BS&A Assessing database ($Database), read-only aggregate export. Residential = property class 401. Sales = assessor terms code 03 (arm's length), price over 10,000 dollars, by calendar year of sale."
    extracted        = (Get-Date).ToString('yyyy-MM-dd')
    assessment_year  = $assessmentYear
    residential      = [ordered]@{
        parcels        = [int]$parcel.parcels
        median_sev     = [int]$parcel.median_sev
        median_taxable = [int]$parcel.median_taxable
        pre_parcels    = [int]$parcel.pre_parcels
    }
    sales            = @($sales | ForEach-Object {
        [ordered]@{ year = [int]$_.yr; sales = [int]$_.sales; median_price = [int]$_.median_price }
    })
}

$json = $out | ConvertTo-Json -Depth 5
$tmp = Join-Path $env:TEMP 'bsa-residential.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  parcels={0} median_sev={1} pre_share={2:P1}" -f $out.residential.parcels, $out.residential.median_sev, ($out.residential.pre_parcels / $out.residential.parcels))
foreach ($s in $out.sales) { Write-Host ("  {0}: {1} sales, median {2:N0}" -f $s.year, $s.sales, $s.median_price) }
