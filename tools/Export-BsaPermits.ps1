<#
.SYNOPSIS
    Export building-permit aggregates from the City's BS&A Assessing database
    for the Building Permits dashboard. Aggregates only; never parcel numbers,
    addresses, contractor names, permit numbers or work descriptions.

.DESCRIPTION
    Runs on a workstation with the read-only BS&A helper and credential
    (C:\utils\BsaSql; db_datareader). Writes tools/data/bsa-permits.json, read
    by tools/build_permits.py.

    Source: dbo.Permits in the Assessing database. Both D001City Of Burton 2026
    and D001CITY OF BURTON 2027 are probed and the one with the later
    MAX(issdate) is used (both maxima are recorded in the output).

    Row filters: issdate is not NULL and the issue year is 1999 through the
    current year (earlier rows are sparse, and a few rows carry garbage years
    such as 1904 and 5780).

    recstatus finding (checked against the data, not assumed): recstatus is a
    PROGRESS code, not a deleted flag. recstatus 1 (about 9,700 rows) is almost
    all rows with a final-inspection date (findate), recstatus 5 is about half,
    recstatus 0 is mostly open permits with no findate, and in 2024 the count
    with recstatus <> 0 (679) equals the count with a findate (679). Statuses 2,
    3 and 4 (about 1,150 rows, nearly all with an expiry date and no findate)
    look like expired or closed-out permits, but nothing marks them as removed
    in error. Every row is a permit the City issued, so ALL recstatus values are
    counted and none is excluded.

    Category groups (case-insensitive, trimmed): new_homes, home_improvements,
    commercial, demolitions, other. Categories that land in "other" are printed
    to the console. The category-to-group map is written to the output so the
    builder can check it against its own copy.

    Declared value is what the applicant states and is often 0; value is
    exported with the count of permits that stated a value, so the builder can
    decide where it is reliable.

.EXAMPLE
    .\tools\Export-BsaPermits.ps1
#>
[CmdletBinding()]
param(
    [string[]]$Databases = @('D001City Of Burton 2026', 'D001CITY OF BURTON 2027'),

    [ValidateRange(2000, 2100)]
    [int]$RecentFrom = 2015,

    [ValidateRange(2000, 2100)]
    [int]$CompletionFrom = 2019,

    [string]$OutPath = (Join-Path $PSScriptRoot 'data\bsa-permits.json')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

$LongFrom = 1999
$Groups = @('new_homes', 'home_improvements', 'commercial', 'demolitions', 'other')
$NewHomeCategories = @('RES, NEW CONSTRUCTION', 'NEW HOUSE', 'RES, MODULAR HOME')
$ImprovementCategories = @(
    'RES, ALTER/REPAIR', 'RES, ADDITION', 'RES, RENEWAL', 'RES, FIRE REPAIR', 'RES, CAR PORT',
    'ROOFING AND SIDING', 'SIDING', 'DECK', 'POOL', 'SHED', 'FENCE', 'POLE BARN',
    'DETACHED ACCESSORY STRUCTURE'
)

foreach ($d in $Databases) {
    if ($d -notmatch '^D001City Of Burton \d{4}$') { throw "Unexpected Assessing database name: $d" }
}

function Get-PermitGroup([string]$Category) {
    $c = ([string]$Category).Trim().ToUpperInvariant()
    if ($NewHomeCategories -contains $c) { return 'new_homes' }
    if ($c -like 'DEMO*') { return 'demolitions' }
    if ($c -like '*COMMERC*' -or $c -eq 'CELL TOWER' -or $c -eq 'SIGN') { return 'commercial' }
    if ($ImprovementCategories -contains $c -or $c -like 'GARAGE*' -or $c -like 'ROOF*') { return 'home_improvements' }
    return 'other'
}

function Test-PermitPlausibility([object[]]$AllYears, [object[]]$RecentYears, [int]$LatestCompleteYear, [int]$CurrentYear) {
    if ($AllYears.Count -lt 20) { throw "Only $($AllYears.Count) issue years found from $LongFrom; need at least 20. Refusing to write." }
    foreach ($y in $RecentYears) {
        if ($y.year -gt $CurrentYear) { throw "Year $($y.year) is after the current year; refusing to write." }
        if ($y.total -gt 3000) { throw "Year $($y.year) has $($y.total) permits (limit 3,000); refusing to write." }
        if ($y.year -le $LatestCompleteYear -and $y.total -lt 200) { throw "Year $($y.year) has only $($y.total) permits (minimum 200 for a complete year); refusing to write." }
        if ($y.year -eq $LatestCompleteYear -and ($y.new_homes.count -lt 0 -or $y.new_homes.count -gt 300)) {
            throw "Latest complete year $($y.year) shows $($y.new_homes.count) new homes (expected 0 to 300); refusing to write."
        }
    }
}

function ConvertTo-WholeNumber([object]$v) { if ($null -eq $v) { return [long]0 }; return [long][math]::Round([double]$v) }

$today = Get-Date
$currentYear = $today.Year
$latestComplete = $currentYear - 1

# --- Pick the database with the later MAX(issdate) -------------------------------
$maxima = [ordered]@{}
$best = $null
$bestMax = [datetime]::MinValue
foreach ($d in $Databases) {
    $m = Invoke-BsaQuery -Database $d -Sql "SELECT MAX(issdate) AS mx FROM dbo.Permits WHERE issdate < '2100-01-01'"
    $mx = [datetime]$m.mx
    $maxima[$d] = $mx.ToString('yyyy-MM-dd')
    Write-Host ("  {0}: MAX(issdate) = {1}" -f $d, $maxima[$d])
    if ($mx -gt $bestMax) { $bestMax = $mx; $best = $d }
}
$Database = $best
Write-Host "Using $Database"

# --- Per year and category aggregates --------------------------------------------
$issued = "issdate >= '$LongFrom-01-01' AND issdate < '$($currentYear + 1)-01-01'"
$catSql = @"
SELECT YEAR(issdate) AS yr, ISNULL(UPPER(LTRIM(RTRIM(category))), 'UNKNOWN') AS cat,
       COUNT(*) AS permits,
       SUM(CASE WHEN permitvalue > 0 THEN permitvalue ELSE 0 END) AS declared_value,
       SUM(CASE WHEN permitvalue > 0 THEN 1 ELSE 0 END) AS with_value,
       SUM(ISNULL(units, 0)) AS units
FROM dbo.Permits
WHERE $issued
GROUP BY YEAR(issdate), ISNULL(UPPER(LTRIM(RTRIM(category))), 'UNKNOWN')
"@
$rows = @(Invoke-BsaQuery -Database $Database -Sql $catSql)
if ($rows.Count -lt 50) { throw "Category query returned only $($rows.Count) rows; refusing to write." }

$categoryMap = @{}
$allYears = @{}
$byYear = @{}
foreach ($r in $rows) {
    $y = [int]$r.yr
    $cat = [string]$r.cat
    $g = Get-PermitGroup $cat
    if (-not $allYears.ContainsKey($y)) { $allYears[$y] = [int]0 }
    $allYears[$y] += [int]$r.permits
    if ($y -ge $RecentFrom) {
        if (-not $byYear.ContainsKey($y)) {
            $e = [ordered]@{ year = $y; total = [int]0 }
            foreach ($gg in $Groups) { $e[$gg] = [ordered]@{ count = [int]0; value = [long]0; with_value = [int]0 } }
            $e['_units_new_homes'] = [long]0
            $byYear[$y] = $e
        }
        $e = $byYear[$y]
        $e.total += [int]$r.permits
        $e[$g].count += [int]$r.permits
        $e[$g].value += ConvertTo-WholeNumber $r.declared_value
        $e[$g].with_value += [int]$r.with_value
        if ($g -eq 'new_homes') { $e['_units_new_homes'] += [long]$r.units }
        if (-not $categoryMap.ContainsKey($cat)) { $categoryMap[$cat] = [ordered]@{ category = $cat; group = $g; permits = [int]0 } }
        $categoryMap[$cat].permits += [int]$r.permits
    }
}

$unmapped = @($categoryMap.Values | Where-Object { $_.group -eq 'other' } | Sort-Object { $_.permits } -Descending)
Write-Host ''
Write-Host ("Categories grouped as 'other' (issued {0} onward):" -f $RecentFrom)
foreach ($u in $unmapped) { Write-Host ("    {0,-34} {1,5}" -f $u.category, $u.permits) }
Write-Host ''
Write-Host 'recstatus finding: recstatus is a progress code, not a deleted flag; all values are counted (see script header).'

$permitsByYear = @($byYear.Keys | Sort-Object | ForEach-Object {
    $e = $byYear[$_]
    $o = [ordered]@{ year = $e.year; total = $e.total }
    foreach ($g in $Groups) { $o[$g] = $e[$g] }
    $o
})
$permitsAll = @($allYears.Keys | Sort-Object | ForEach-Object { [ordered]@{ year = [int]$_; total = [int]$allYears[$_] } })

Test-PermitPlausibility -AllYears $permitsAll -RecentYears $permitsByYear -LatestCompleteYear $latestComplete -CurrentYear $currentYear

# --- Latest complete year and year to date ---------------------------------------
$latestRow = $permitsByYear | Where-Object { $_.year -eq $latestComplete }
if (-not $latestRow) { throw "No permits found for the latest complete year $latestComplete; refusing to write." }
$ytdRow = $permitsByYear | Where-Object { $_.year -eq $currentYear }
$ytd = $null
if ($ytdRow) {
    $ytd = [ordered]@{ as_of = $today.ToString('yyyy-MM-dd'); last_permit_issued = $maxima[$Database] }
    foreach ($k in $ytdRow.Keys) { $ytd[$k] = $ytdRow[$k] }
}

# --- New-home units per year -----------------------------------------------------
$unitRows = @($byYear.Keys | Sort-Object | ForEach-Object {
    $e = $byYear[$_]
    if ($e['_units_new_homes'] -gt 0) {
        [ordered]@{ year = $e.year; units = [long]$e['_units_new_homes']; basis = 'units' }
    } else {
        [ordered]@{ year = $e.year; units = [long]$e.new_homes.count; basis = 'permit_count' }
    }
})

# --- Median days from issue to final inspection ----------------------------------
function Get-GroupCategoryList([string]$Group) {
    # Category strings come from the database, so validate before building an IN list.
    $names = @($categoryMap.Values | Where-Object { $_.group -eq $Group } | ForEach-Object { $_.category })
    foreach ($n in $names) {
        if ($n -notmatch "^[A-Z0-9 ,/&.\-']+$") { throw "Unexpected characters in category '$n'; refusing to build SQL." }
    }
    return ($names | ForEach-Object { "'" + ($_ -replace "'", "''") + "'" }) -join ', '
}
$completion = [ordered]@{ since_year = $CompletionFrom; note = 'Permits issued since since_year that have a final-inspection date after the issue date.' }
foreach ($g in @('new_homes', 'home_improvements')) {
    $list = Get-GroupCategoryList $g
    $medianSql = @"
WITH d AS (
    SELECT DATEDIFF(day, issdate, findate) AS days
    FROM dbo.Permits
    WHERE issdate >= '$CompletionFrom-01-01' AND issdate < '$($currentYear + 1)-01-01'
      AND findate > issdate AND findate < '2100-01-01'
      AND UPPER(LTRIM(RTRIM(category))) IN ($list)
),
ranked AS (SELECT days, ROW_NUMBER() OVER (ORDER BY days) AS rn, COUNT(*) OVER () AS n FROM d)
SELECT (SELECT COUNT(*) FROM d) AS permits,
       (SELECT TOP 1 days FROM ranked WHERE rn = (n + 1) / 2) AS median_days
"@
    $m = Invoke-BsaQuery -Database $Database -Sql $medianSql
    if (-not $m -or [int]$m.permits -lt 30) { throw "Completion-time query for $g returned too few permits; refusing to write." }
    $completion[$g] = [ordered]@{ permits = [int]$m.permits; median_days = [int]$m.median_days }
}

$out = [ordered]@{
    _source                = [ordered]@{
        server   = 'BURBSA01\BSA'
        database = $Database
        table    = 'dbo.Permits'
        note     = 'aggregates only'
    }
    extracted              = $today.ToString('yyyy-MM-dd')
    database_max_issdate   = $maxima
    recstatus_note         = 'recstatus is a progress code, not a deleted flag; every row is an issued permit and all values are counted.'
    groups                 = $Groups
    latest_complete_year   = $latestComplete
    latest_year            = $latestRow
    year_to_date           = $ytd
    permits_by_year        = $permitsByYear
    permits_by_year_all    = $permitsAll
    new_home_units_by_year = $unitRows
    time_to_complete       = $completion
    category_map           = @($categoryMap.Values | Sort-Object { $_.category })
}

$json = $out | ConvertTo-Json -Depth 8
$tmp = Join-Path $env:TEMP 'bsa-permits.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  {0} permits issued in {1} ({2} new homes, {3} home improvements, {4} demolitions)" -f $latestRow.total, $latestComplete, $latestRow.new_homes.count, $latestRow.home_improvements.count, $latestRow.demolitions.count)
Write-Host ("  median days to completion: new homes {0}, home improvements {1}" -f $completion.new_homes.median_days, $completion.home_improvements.median_days)
