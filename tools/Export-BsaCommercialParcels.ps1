<#
.SYNOPSIS
    Export commercial and industrial parcels from the City's BS&A Assessing roll for
    the Sites for Business overlays and dashboard (ADR-0003 Part C), plus one
    citywide count of commercial transfers.

.DESCRIPTION
    Runs on a workstation with the read-only BS&A helper and credential
    (C:\utils\BsaSql; db_datareader on the Assessing database). Writes two
    gitignored inputs read by tools/build_business_sites.py:

      pipeline/data/commercial-parcels.csv
        parcel, street, city, zip, propclass, acres, frontage, zoning
        for property classes 201, 202, 301 and 302. No owner, value or tax field.

      pipeline/data/commercial-sales-summary.json
        { "transfers24": N, "asOf": "YYYY-MM-DD" } -- arms-length sales of
        improved commercial and industrial parcels (201/301) in the trailing 24
        months. A count only; prices are never exported (ADR-0003 Part C).

.EXAMPLE
    .\tools\Export-BsaCommercialParcels.ps1 -AssessmentYear 2026
#>
[CmdletBinding()]
param(
    [ValidateRange(2010, 2100)]
    [int]$AssessmentYear = 2026,

    [string]$AssessingDatabase,

    [string]$OutCsv = (Join-Path $PSScriptRoot '..\pipeline\data\commercial-parcels.csv'),

    [string]$OutSummary = (Join-Path $PSScriptRoot '..\pipeline\data\commercial-sales-summary.json')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

if (-not $AssessingDatabase) { $AssessingDatabase = 'D001City Of Burton {0}' -f $AssessmentYear }
if ($AssessingDatabase -notmatch '^D001City Of Burton \d{4}$') { throw "Unexpected Assessing database name: $AssessingDatabase" }

$parcelSql = @"
SELECT p.pnum                                              AS parcel,
       LTRIM(RTRIM(ISNULL(m.propstreetcombined, '')))      AS street,
       LTRIM(RTRIM(ISNULL(m.propcity, '')))                AS city,
       LTRIM(RTRIM(ISNULL(m.propzip, '')))                 AS zip,
       LTRIM(RTRIM(p.propclass))                           AS propclass,
       ROUND(ISNULL(m.totalacres, 0), 2)                   AS acres,
       ROUND(ISNULL(m.frontage, 0), 0)                     AS frontage,
       LTRIM(RTRIM(ISNULL(m.zoning, '')))                  AS zoning
FROM dbo.Parcels p
JOIN dbo.ParcelMaster m ON m.pnum = p.pnum
WHERE LTRIM(RTRIM(p.propclass)) IN ('201', '202', '301', '302')
ORDER BY p.propclass, m.propstreetcombined;
"@

$summarySql = @"
SELECT COUNT(*) AS transfers24
FROM dbo.Sales
WHERE saledate >= DATEADD(month, -24, GETDATE())
  AND LTRIM(RTRIM(propclass)) IN ('201', '301')
  AND terms IN ('03-ARM''S LENGTH', '19-MULTI PARCEL ARM''S LENGTH')
  AND saleprice > 0 AND ISNULL(confidential, 0) = 0;
"@

$rows = Invoke-BsaQuery -Database $AssessingDatabase -Sql $parcelSql
if (-not $rows -or @($rows).Count -lt 100) {
    throw ("Commercial parcel export returned {0} rows; expected several hundred." -f @($rows).Count)
}
$dir = Split-Path $OutCsv -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$rows | Export-Csv -Path $OutCsv -NoTypeInformation -Encoding UTF8

$summary = Invoke-BsaQuery -Database $AssessingDatabase -Sql $summarySql
$json = '{{"transfers24": {0}, "asOf": "{1}"}}' -f [int]$summary.transfers24, (Get-Date -Format 'yyyy-MM-dd')
[System.IO.File]::WriteAllText($OutSummary, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))

Write-Output ("Wrote {0} commercial/industrial parcels -> {1}" -f @($rows).Count, $OutCsv)
Write-Output ("Wrote transfers24={0} -> {1}" -f [int]$summary.transfers24, $OutSummary)
