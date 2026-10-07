<#
.SYNOPSIS
    Export inspection and completion aggregates from the City's BS&A Building
    Department module for the Building Permits dashboard. Aggregates only;
    never permit numbers, parcel numbers, addresses, applicant, owner,
    contractor or inspector names.

.DESCRIPTION
    Runs on a workstation with the read-only BS&A helper and credential
    (C:\utils\BsaSql; db_datareader on D007BURFINAL). Writes
    tools/data/bsa-permit-workflow.json, read by tools/build_permits.py.

    Source: dbo.Permit and dbo.Inspection in the Building Department database.
    Permit.Status and Inspection.Result are integers. They were decoded from
    the vendor object model (BSA.Cd.Shared.Objects in BSASoftware.Cd.Shared.Objects.dll,
    enums PermitStatus and InspectionResult, read with dnSpyEx on 2026-10-07):

      PermitStatus: 0 Unknown, 1 Issued, 2 IssuedExtended, 3 IssuedInactive,
        4 Denied, 5 Canceled, 6 Finaled, 7 Expired, 8 HoldFee, 9 HoldBond,
        10 HoldPrereq, 11 HoldC404, 12 HoldDodge, 13 Hold, 14 Closed,
        15 HoldIccInf, 16 HoldBuildingInf, 17 HoldDeficiency, 18 HoldContractor,
        19 SuspendedFee, 20 ReadyToIssue, 21 HoldForReview, 22 HoldForInvoice,
        23 HoldForIso, 24 HoldForProjectRequirement, 25 SuspendedReview,
        26 HoldBondPayment.
      InspectionResult (permit inspections, LinkFromType 2): 0 None, 1 Approved,
        2 Disapproved, 3 PartiallyApproved, 4 NotReady, 5 LockedOut, 6 Canceled.
        Code-enforcement inspections (LinkFromType 6) use a different result
        list (Violation(s), Complied, ...) and are excluded here.

    The decode is checked against the data on every run: Inspection.ResultString
    (the label the module stored with each row) must agree with the enum for
    at least 99 percent of permit inspections, or the script refuses to write.

    Time from application to issue is NOT exported: the applied date is stamped
    at issue (median 0 days every year), so it measures nothing. Completion is
    measured as the share of building permits finaled within a year of issue,
    only for issue years old enough that every permit has had a full year.

.EXAMPLE
    .\tools\Export-BsaPermitWorkflow.ps1
#>
[CmdletBinding()]
param(
    [string]$Database = 'D007BURFINAL',

    [ValidateRange(2000, 2100)]
    [int]$From = 2019,

    [string]$OutPath = (Join-Path $PSScriptRoot 'data\bsa-permit-workflow.json')
)

$ErrorActionPreference = 'Stop'
Import-Module 'C:\utils\BsaSql\BsaSql.psm1'

if ($Database -notmatch '^D007[A-Za-z0-9]+$') { throw "Unexpected Building Department database name: $Database" }

# Keys are strings on purpose: an integer index on an ordered dictionary is positional, not a key lookup.
$StatusNames = [ordered]@{
    '0' = 'Unknown'; '1' = 'Issued'; '2' = 'IssuedExtended'; '3' = 'IssuedInactive'; '4' = 'Denied'; '5' = 'Canceled'
    '6' = 'Finaled'; '7' = 'Expired'; '8' = 'HoldFee'; '9' = 'HoldBond'; '10' = 'HoldPrereq'; '11' = 'HoldC404'; '12' = 'HoldDodge'
    '13' = 'Hold'; '14' = 'Closed'; '15' = 'HoldIccInf'; '16' = 'HoldBuildingInf'; '17' = 'HoldDeficiency'; '18' = 'HoldContractor'
    '19' = 'SuspendedFee'; '20' = 'ReadyToIssue'; '21' = 'HoldForReview'; '22' = 'HoldForInvoice'; '23' = 'HoldForIso'
    '24' = 'HoldForProjectRequirement'; '25' = 'SuspendedReview'; '26' = 'HoldBondPayment'
}
$ResultNames = [ordered]@{ '0' = 'None'; '1' = 'Approved'; '2' = 'Disapproved'; '3' = 'Partially Approved'; '4' = 'Not Ready'; '5' = 'Locked Out'; '6' = 'Canceled' }
$ResultKeys = [ordered]@{ '1' = 'approved'; '2' = 'disapproved'; '3' = 'partially_approved'; '4' = 'not_ready'; '5' = 'locked_out'; '6' = 'canceled' }
$PermitLink = 2

function Get-StatusGroup([int]$Status) {
    switch ($Status) {
        6 { return 'finaled' }
        14 { return 'closed' }
        7 { return 'expired' }
        5 { return 'canceled' }
        4 { return 'canceled' }
        default { if ($Status -in 1, 2, 3) { return 'open' }; return 'other' }
    }
}
function Get-TypeGroup([string]$PermitType) {
    $t = ([string]$PermitType).Trim().ToUpperInvariant()
    if ($t -eq 'BUILDING') { return 'building' }
    if ($t -eq 'SITE PERMIT') { return 'site' }
    return 'other'
}
function ConvertTo-WholeNumber([object]$v) { if ($null -eq $v) { return [long]0 }; return [long][math]::Round([double]$v) }

$today = (Get-Date).Date
$currentYear = $today.Year
$latestComplete = $currentYear - 1
$untilLit = '{0}-01-01' -f ($currentYear + 1)

# --- Decode guards ------------------------------------------------------------------
$statusRows = @(Invoke-BsaQuery -Database $Database -Sql 'SELECT Status, COUNT(*) AS n FROM dbo.Permit GROUP BY Status')
foreach ($r in $statusRows) {
    if (-not $StatusNames.Contains([string][int]$r.Status)) { throw "Permit.Status $($r.Status) is outside the decoded PermitStatus enum; refusing to write." }
}
$resultRows = @(Invoke-BsaQuery -Database $Database -Sql "SELECT Result, ISNULL(ResultString, '') AS label, COUNT(*) AS n FROM dbo.Inspection WHERE LinkFromType = $PermitLink GROUP BY Result, ISNULL(ResultString, '')")
$agree = 0; $disagree = 0
foreach ($r in $resultRows) {
    $code = [string][int]$r.Result
    if (-not $ResultNames.Contains($code)) { throw "Inspection.Result $code is outside the decoded InspectionResult enum; refusing to write." }
    $label = ([string]$r.label).Trim()
    if ($label -eq '') { continue }
    if ($label -eq $ResultNames[$code]) { $agree += [int]$r.n } else { $disagree += [int]$r.n; Write-Host ("  decode mismatch: Result {0} labelled '{1}' on {2} rows" -f $code, $label, $r.n) }
}
if ($agree -lt 1000 -or $disagree -gt 0.01 * ($agree + $disagree)) { throw "ResultString disagrees with the InspectionResult decode on $disagree of $($agree + $disagree) labelled rows; refusing to write." }

# --- Inspections completed per year, by result --------------------------------------
$inspSql = @"
SELECT YEAR(DateTimeCompleted) AS yr, Result, COUNT(*) AS n
FROM dbo.Inspection
WHERE LinkFromType = $PermitLink AND DateTimeCompleted >= '$From-01-01' AND DateTimeCompleted < '$untilLit'
GROUP BY YEAR(DateTimeCompleted), Result
"@
$inspRows = @(Invoke-BsaQuery -Database $Database -Sql $inspSql)
$inspByYear = @{}
foreach ($r in $inspRows) {
    $y = [int]$r.yr
    if (-not $inspByYear.ContainsKey($y)) {
        $e = [ordered]@{ year = $y; completed = [int]0 }
        foreach ($k in $ResultKeys.Values) { $e[$k] = [int]0 }
        $e['none'] = [int]0
        $inspByYear[$y] = $e
    }
    $e = $inspByYear[$y]
    $e.completed += [int]$r.n
    $code = [string][int]$r.Result
    if ($ResultKeys.Contains($code)) { $e[$ResultKeys[$code]] += [int]$r.n } else { $e['none'] += [int]$r.n }
}
$inspections = @($inspByYear.Keys | Sort-Object | ForEach-Object { $inspByYear[$_] })
foreach ($e in $inspections) {
    if ($e.year -le $latestComplete) {
        if ($e.completed -lt 500 -or $e.completed -gt 20000) { throw "Year $($e.year) has $($e.completed) permit inspections (expected 500 to 20,000); refusing to write." }
        $judged = $e.approved + $e.disapproved + $e.partially_approved
        if ($judged -lt 1 -or ($e.approved / $judged) -lt 0.5 -or ($e.approved / $judged) -gt 0.98) { throw "Year $($e.year) approval share is implausible; refusing to write." }
    }
}
if (@($inspections | Where-Object { $_.year -le $latestComplete }).Count -lt 5) { throw 'Fewer than five complete inspection years; refusing to write.' }

# --- Inspection types in the latest complete year -------------------------------------
$typeSql = @"
SELECT CASE WHEN UPPER(LTRIM(RTRIM(InspectionType))) = 'INITAL' THEN 'INITIAL' ELSE UPPER(LTRIM(RTRIM(InspectionType))) END AS t,
       SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS approved,
       SUM(CASE WHEN Result = 2 THEN 1 ELSE 0 END) AS disapproved,
       SUM(CASE WHEN Result = 3 THEN 1 ELSE 0 END) AS partially_approved,
       COUNT(*) AS completed
FROM dbo.Inspection
WHERE LinkFromType = $PermitLink AND DateTimeCompleted >= '$latestComplete-01-01' AND DateTimeCompleted < '$currentYear-01-01'
GROUP BY CASE WHEN UPPER(LTRIM(RTRIM(InspectionType))) = 'INITAL' THEN 'INITIAL' ELSE UPPER(LTRIM(RTRIM(InspectionType))) END
HAVING COUNT(*) >= 25
ORDER BY completed DESC
"@
$typeRows = @(Invoke-BsaQuery -Database $Database -Sql $typeSql)
foreach ($r in $typeRows) {
    if (([string]$r.t) -notmatch "^[A-Z0-9 &/\-]+$") { throw "Unexpected inspection type label '$($r.t)'; refusing to write." }
}
$types = @($typeRows | ForEach-Object {
    [ordered]@{ type = [string]$_.t; completed = [int]$_.completed; approved = [int]$_.approved; disapproved = [int]$_.disapproved; partially_approved = [int]$_.partially_approved }
})

# --- Permits by issue year, type group and status group ---------------------------------
$permitSql = @"
SELECT YEAR(DateIssued) AS yr, PermitType, Status, COUNT(*) AS n
FROM dbo.Permit
WHERE DateIssued >= '$From-01-01' AND DateIssued < '$untilLit'
GROUP BY YEAR(DateIssued), PermitType, Status
"@
$permitRows = @(Invoke-BsaQuery -Database $Database -Sql $permitSql)
$permitByYear = @{}
$statusGroups = @('finaled', 'closed', 'expired', 'open', 'canceled', 'other')
foreach ($r in $permitRows) {
    $y = [int]$r.yr
    if (-not $permitByYear.ContainsKey($y)) {
        $e = [ordered]@{ year = $y; permits = [int]0 }
        foreach ($tg in @('building', 'site', 'other')) {
            $cell = [ordered]@{ permits = [int]0 }
            foreach ($sg in $statusGroups) { $cell[$sg] = [int]0 }
            $e[$tg] = $cell
        }
        $permitByYear[$y] = $e
    }
    $e = $permitByYear[$y]
    $tg = Get-TypeGroup ([string]$r.PermitType)
    $sg = Get-StatusGroup ([int]$r.Status)
    $e.permits += [int]$r.n
    $e[$tg].permits += [int]$r.n
    $e[$tg][$sg] += [int]$r.n
}
$permits = @($permitByYear.Keys | Sort-Object | ForEach-Object { $permitByYear[$_] })
foreach ($e in $permits) {
    if ($e.year -le $latestComplete -and ($e.permits -lt 300 -or $e.permits -gt 3000)) { throw "Year $($e.year) has $($e.permits) permits (expected 300 to 3,000); refusing to write." }
}

# --- Building permits finaled within a year of issue ------------------------------------
# Only issue years where every permit has had a full year: year <= current year - 2.
$observable = $currentYear - 2
$finishSql = @"
SELECT YEAR(DateIssued) AS yr, COUNT(*) AS permits,
       SUM(CASE WHEN DateFinaled IS NOT NULL AND DateFinaled <= DATEADD(day, 365, DateIssued) THEN 1 ELSE 0 END) AS finaled_within_year,
       SUM(CASE WHEN DateFinaled IS NOT NULL THEN 1 ELSE 0 END) AS finaled_ever
FROM dbo.Permit
WHERE UPPER(LTRIM(RTRIM(PermitType))) = 'BUILDING' AND DateIssued >= '$From-01-01' AND DateIssued < '$($observable + 1)-01-01'
GROUP BY YEAR(DateIssued) ORDER BY yr
"@
$finishRows = @(Invoke-BsaQuery -Database $Database -Sql $finishSql)
if ($finishRows.Count -lt 4) { throw 'Fewer than four observable issue years for completion; refusing to write.' }
$finished = @($finishRows | ForEach-Object {
    if ([int]$_.permits -lt 100) { throw "Issue year $($_.yr) has only $($_.permits) building permits; refusing to write." }
    [ordered]@{ year = [int]$_.yr; permits = [int]$_.permits; finaled_within_year = [int]$_.finaled_within_year; finaled_ever = [int]$_.finaled_ever }
})

# Scheduling lag is NOT exported: DateTimeScheduled is filled when the inspection is
# entered (median 0 days from scheduled to completed, all within 3 days), so it does
# not measure waiting time.

# --- Inspections per building permit, latest complete issue year ---------------------------
$perPermitSql = @"
SELECT COUNT(*) AS permits, ISNULL(SUM(x.n), 0) AS inspections
FROM dbo.Permit p
LEFT JOIN (SELECT LinkFromGuid, COUNT(*) AS n FROM dbo.Inspection WHERE LinkFromType = $PermitLink AND DateTimeCompleted IS NOT NULL GROUP BY LinkFromGuid) x ON x.LinkFromGuid = p.Guid
WHERE UPPER(LTRIM(RTRIM(p.PermitType))) = 'BUILDING' AND p.DateIssued >= '$latestComplete-01-01' AND p.DateIssued < '$currentYear-01-01'
"@
$perPermit = Invoke-BsaQuery -Database $Database -Sql $perPermitSql
if (-not $perPermit -or [int]$perPermit.permits -lt 100) { throw 'Inspections-per-permit query returned too few permits; refusing to write.' }

$out = [ordered]@{
    _source                 = [ordered]@{
        server   = 'BURBSA01\BSA'
        database = $Database
        tables   = 'dbo.Permit, dbo.Inspection (LinkFromType 2 = permit inspections)'
        note     = 'aggregates only; status and result codes decoded from the vendor object model and checked against ResultString on every run'
    }
    extracted               = $today.ToString('yyyy-MM-dd')
    latest_complete_year    = $latestComplete
    status_codes            = $StatusNames
    result_codes            = $ResultNames
    inspections_by_year     = $inspections
    inspection_types_latest = [ordered]@{ year = $latestComplete; minimum_count = 25; types = $types }
    permits_by_issue_year   = $permits
    finished_within_year    = [ordered]@{ permit_type = 'Building'; through_year = $observable; years = $finished }
    inspections_per_permit  = [ordered]@{ year = $latestComplete; permit_type = 'Building'; permits = [int]$perPermit.permits; inspections = [int]$perPermit.inspections }
}

$json = $out | ConvertTo-Json -Depth 8
$tmp = Join-Path $env:TEMP 'bsa-permit-workflow.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
$last = $inspections | Where-Object { $_.year -eq $latestComplete }
$judged = $last.approved + $last.disapproved + $last.partially_approved
Write-Host ("  {0}: {1:N0} permit inspections completed, {2:P0} approved of those judged" -f $latestComplete, $last.completed, ($last.approved / $judged))
$lf = $finished | Select-Object -Last 1
Write-Host ("  building permits issued {0}: {1:P0} finaled within a year" -f $lf.year, ($lf.finaled_within_year / $lf.permits))
