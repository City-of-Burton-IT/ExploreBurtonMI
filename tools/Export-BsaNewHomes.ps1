<#
.SYNOPSIS
    Export new-home building permits (address and issue year only) from the City's
    BS&A Assessing database for the "New homes permitted" map overlay (ADR-0003 Part D).

.DESCRIPTION
    Runs on a workstation with the read-only BS&A helper and credential
    (C:\utils\BsaSql; db_datareader). Writes the gitignored
    pipeline/data/new-homes.csv read by tools/build_new_homes.py:

      parcel, street, city, zip, year, units

    Only the three new-home categories used by Export-BsaPermits.ps1 are selected.
    No permit number, owner, contractor, value or description is exported. The two
    Assessing databases are probed and the one with the later MAX(issdate) is used,
    exactly as the permits aggregate export does.

.EXAMPLE
    .\tools\Export-BsaNewHomes.ps1 -FromYear 2015
#>
[CmdletBinding()]
param(
    [ValidateRange(1999, 2100)]
    [int]$FromYear = 2015,

    [string[]]$Databases = @('D001City Of Burton 2026', 'D001City Of Burton 2027'),

    [string]$OutCsv = (Join-Path $PSScriptRoot '..\pipeline\data\new-homes.csv')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

foreach ($d in $Databases) {
    if ($d -notmatch '^D001City Of Burton \d{4}$') { throw "Unexpected Assessing database name: $d" }
}

$maxima = @{}
foreach ($d in $Databases) {
    try {
        $m = Invoke-BsaQuery -Database $d -Sql "SELECT MAX(issdate) AS mx FROM dbo.Permits WHERE issdate < '2100-01-01'"
        $maxima[$d] = $m.mx
    } catch {
        Write-Host ("  {0}: not readable ({1})" -f $d, $_.Exception.Message)
    }
}
if ($maxima.Count -eq 0) { throw 'No Assessing database was readable.' }
$Database = ($maxima.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1).Key
Write-Host ("Using {0} (MAX issdate {1})" -f $Database, $maxima[$Database])

$currentYear = (Get-Date).Year
$sql = @"
SELECT p.pnum                                        AS parcel,
       LTRIM(RTRIM(ISNULL(p.addresscombined, '')))   AS street,
       LTRIM(RTRIM(ISNULL(m.propcity, '')))           AS city,
       LTRIM(RTRIM(ISNULL(m.propzip, '')))            AS zip,
       YEAR(p.issdate)                                AS year,
       ISNULL(p.units, 0)                             AS units
FROM dbo.Permits p
LEFT JOIN dbo.ParcelMaster m ON m.pnum = p.pnum
WHERE p.issdate >= '$FromYear-01-01' AND p.issdate < '$($currentYear + 1)-01-01'
  AND UPPER(LTRIM(RTRIM(p.category))) IN ('RES, NEW CONSTRUCTION', 'NEW HOUSE', 'RES, MODULAR HOME')
ORDER BY p.issdate;
"@

$rows = Invoke-BsaQuery -Database $Database -Sql $sql
if (-not $rows -or @($rows).Count -lt 20) {
    throw ("New-home export returned {0} rows; expected dozens per year. Category list or filter changed?" -f @($rows).Count)
}
$dir = Split-Path $OutCsv -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$rows | Export-Csv -Path $OutCsv -NoTypeInformation -Encoding UTF8
Write-Output ("Wrote {0} new-home permits since {1} -> {2}" -f @($rows).Count, $FromYear, $OutCsv)
