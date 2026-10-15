<#
.SYNOPSIS
    Export arms-length residential sales from the City's BS&A Assessing database
    for the Home Sale Prices dashboard (ADR-0003 Part B). Local input only; the
    public site shows block-group aggregates built by tools/build_sales_tiles.py.

.DESCRIPTION
    Runs on a workstation with the read-only BS&A helper and credential
    (C:\utils\BsaSql; db_datareader on the Assessing database). Writes
    pipeline/data/sales-source.csv, which is gitignored and never published.

    Columns: parcel, street, city, zip, saledate, price, propclass, terms, instr,
    sqft, vacant, liberpage. No grantor or grantee names are exported.

    Selection follows ADR-0003: property class 4xx, terms 03 or 19 (the Assessor's
    arms-length coding), not confidential, within the trailing MonthsBack months.
    The Python builder applies the improved-only and price-above-zero rules and
    collapses multi-parcel sales on liberpage, so this export stays a plain pull.

.EXAMPLE
    .\tools\Export-BsaSales.ps1 -AssessmentYear 2026
#>
[CmdletBinding()]
param(
    [ValidateRange(2010, 2100)]
    [int]$AssessmentYear = 2026,

    [string]$AssessingDatabase,

    [ValidateRange(12, 120)]
    [int]$MonthsBack = 48,

    [string]$OutCsv = (Join-Path $PSScriptRoot '..\pipeline\data\sales-source.csv')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

if (-not $AssessingDatabase) { $AssessingDatabase = 'D001City Of Burton {0}' -f $AssessmentYear }
if ($AssessingDatabase -notmatch '^D001City Of Burton \d{4}$') { throw "Unexpected Assessing database name: $AssessingDatabase" }

$sql = @"
SELECT s.pnum                                            AS parcel,
       LTRIM(RTRIM(ISNULL(s.addresscombined, '')))       AS street,
       LTRIM(RTRIM(ISNULL(p.propcity, '')))              AS city,
       LTRIM(RTRIM(ISNULL(p.propzip, '')))               AS zip,
       CONVERT(varchar(10), s.saledate, 23)              AS saledate,
       CAST(ROUND(ISNULL(s.saleprice, 0), 0) AS bigint)  AS price,
       LTRIM(RTRIM(ISNULL(s.propclass, '')))             AS propclass,
       LTRIM(RTRIM(ISNULL(s.terms, '')))                 AS terms,
       LTRIM(RTRIM(ISNULL(s.instr, '')))                 AS instr,
       ISNULL(s.resb_floorarea, 0)                       AS sqft,
       ISNULL(s.isVacantLandSale, 0)                     AS vacant,
       LTRIM(RTRIM(ISNULL(s.liberpage, '')))             AS liberpage
FROM dbo.Sales s
LEFT JOIN dbo.ParcelMaster p ON p.pnum = s.pnum
WHERE s.saledate >= DATEADD(month, -$MonthsBack, GETDATE())
  AND LEFT(s.propclass, 1) = '4'
  AND s.terms IN ('03-ARM''S LENGTH', '19-MULTI PARCEL ARM''S LENGTH')
  AND ISNULL(s.confidential, 0) = 0
ORDER BY s.saledate, s.pnum;
"@

$rows = Invoke-BsaQuery -Database $AssessingDatabase -Sql $sql
if (-not $rows -or @($rows).Count -lt 50) {
    throw ("Sales export returned {0} rows; expected hundreds. Source schema or filter changed?" -f @($rows).Count)
}
$dir = Split-Path $OutCsv -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$rows | Export-Csv -Path $OutCsv -NoTypeInformation -Encoding UTF8
Write-Output ("Wrote {0} arms-length residential sales ({1} months) -> {2}" -f @($rows).Count, $MonthsBack, $OutCsv)
