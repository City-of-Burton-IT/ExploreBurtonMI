<#
.SYNOPSIS
    One-command refresh of every Explore Burton feed that comes from the City's
    BS&A databases, followed by the Python panel builders that consume them.

.DESCRIPTION
    Runs on the IT workstation that holds the read-only BS&A credential
    (C:\utils\BsaSql). Steps:
      1. Export-BsaCostOfLiving.ps1  -> tools/data/bsa-residential.json
      2. Export-BsaBudget.ps1        -> tools/data/bsa-budget.json
      3. Export-BsaTaxRoll.ps1       -> tools/data/bsa-taxroll.json
      4. fetch_costofliving.py (needs CENSUS_API_KEY), fetch_finances.py
         (--offline unless -Online), build_propertytax.py
    Aggregates only leave the databases. Review the git diff, run the test
    suites, and open a PR as usual; nothing here commits or deploys.

.PARAMETER AssessmentYear
    Assessing roll year (database D001City Of Burton <year>). Also the tax year.

.PARAMETER FiscalYearEnd
    GL fiscal year end for the adopted budget (2027 = FY2026-27).

.PARAMETER Online
    Let fetch_finances.py call the State Community Financials API instead of
    reusing the committed audited figures.

.EXAMPLE
    .\tools\Refresh-CityRecords.ps1 -AssessmentYear 2026 -FiscalYearEnd 2027
#>
[CmdletBinding()]
param(
    [ValidateRange(2010, 2100)][int]$AssessmentYear = 2026,
    [ValidateRange(2010, 2100)][int]$FiscalYearEnd = 2027,
    [switch]$Online
)

$ErrorActionPreference = 'Stop'
$tools = $PSScriptRoot
$repo = (Resolve-Path (Join-Path $tools '..')).Path

Write-Output '[1/4] Cost of living (Assessing sales + Utility Billing) ...'
& (Join-Path $tools 'Export-BsaCostOfLiving.ps1') -Database ('D001City Of Burton {0}' -f $AssessmentYear)

Write-Output '[2/4] Budget and actuals (General Ledger) ...'
& (Join-Path $tools 'Export-BsaBudget.ps1') -FiscalYearEnd $FiscalYearEnd

Write-Output '[3/4] Tax roll and taxable value (Tax + Assessing) ...'
& (Join-Path $tools 'Export-BsaTaxRoll.ps1') -TaxYear $AssessmentYear

Write-Output '[4/4] Rebuilding panels ...'
Push-Location $tools
try {
    if (-not $env:CENSUS_API_KEY) { throw 'CENSUS_API_KEY is not set; fetch_costofliving.py needs it.' }
    & python fetch_costofliving.py --rpp-file data/bea-rpp.json
    if ($LASTEXITCODE -ne 0) { throw "fetch_costofliving.py exited $LASTEXITCODE" }
    $finArgs = @('fetch_finances.py')
    if (-not $Online) { $finArgs += '--offline' }
    & python @finArgs
    if ($LASTEXITCODE -ne 0) { throw "fetch_finances.py exited $LASTEXITCODE" }
    & python build_propertytax.py
    if ($LASTEXITCODE -ne 0) { throw "build_propertytax.py exited $LASTEXITCODE" }
} finally {
    Pop-Location
}

Write-Output ''
Write-Output 'Refresh complete. Next: review `git diff public/ tools/data/`, bump public/freshness.json if a'
Write-Output 'vintage changed, re-read the clarity copy for stale numbers, then run the test suites.'
& git -C $repo status --short -- public tools/data
