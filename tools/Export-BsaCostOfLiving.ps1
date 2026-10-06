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

    # Live Utility Billing database (D010BURTON). Pass '' to skip the utility section.
    [ValidatePattern('^(D010[A-Za-z0-9 ]+)?$')]
    [string]$UtilityDatabase = 'D010BURTON',

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

# Typical residential utility bill: active residential accounts on quarterly
# cycles with exactly four bills in the last 12 months. Accounts are split by
# whether any water item was billed (many Burton homes are on private wells and
# pay sewer only). Medians of the annual total per account; aggregates only.
$utilitySql = @"
WITH bills AS (
    SELECT h.id, h.idAccount, h.amount
    FROM dbo.HistoryHeader h
    JOIN dbo.Account a ON a.id = h.idAccount
    WHERE h.actionTrxType = 0 AND h.amount > 0
      AND h.dateTimePosted >= DATEADD(year, -1, GETDATE())
      AND a.class = 'RES' AND a.status = 'Active' AND a.cycle LIKE 'Q%'
),
water AS (
    SELECT DISTINCT b.idAccount
    FROM bills b
    JOIN dbo.HistoryItem i ON i.idHistoryHeader = b.id
    JOIN dbo.BillItemAmt ba ON ba.id = i.idBillItemAmt
    WHERE ba.billItemName LIKE 'WTR%' OR ba.billItemName IN ('LAWNWTR', 'W-PDWV')
),
peracct AS (
    SELECT b.idAccount, SUM(b.amount) AS annual, COUNT(*) AS bills,
           CASE WHEN w.idAccount IS NULL THEN 0 ELSE 1 END AS hasWater
    FROM bills b LEFT JOIN water w ON w.idAccount = b.idAccount
    GROUP BY b.idAccount, w.idAccount
    HAVING COUNT(*) = 4
),
ranked AS (
    SELECT hasWater, annual,
           ROW_NUMBER() OVER (PARTITION BY hasWater ORDER BY annual) AS rn,
           COUNT(*) OVER (PARTITION BY hasWater) AS n
    FROM peracct
)
SELECT hasWater, MAX(n) AS accounts,
       MAX(CASE WHEN rn = (n + 1) / 2 THEN annual END) AS median_annual
FROM ranked GROUP BY hasWater ORDER BY hasWater
"@

$parcel = Invoke-BsaQuery -Database $Database -Sql $parcelSql
$sales = @(Invoke-BsaQuery -Database $Database -Sql $salesSql)
$utility = $null
if ($UtilityDatabase) {
    $rows = @(Invoke-BsaQuery -Database $UtilityDatabase -Sql $utilitySql)
    $sewerOnly = $rows | Where-Object { [int]$_.hasWater -eq 0 } | Select-Object -First 1
    $waterSewer = $rows | Where-Object { [int]$_.hasWater -eq 1 } | Select-Object -First 1
    if (-not $sewerOnly -or -not $waterSewer -or [int]$sewerOnly.accounts -lt 100 -or [int]$waterSewer.accounts -lt 100) {
        throw 'Utility query returned too few accounts in one of the groups; refusing to write.'
    }
    # Usage-based share of a quarterly bill (WTR-USAGE + SWR-USAGE items), so the
    # dashboard can say how much of the bill depends on how much water a home uses.
    $usageSql = @"
WITH u AS (
    SELECT h.id AS bill, SUM(i.amount) AS usage_amt
    FROM dbo.HistoryHeader h
    JOIN dbo.Account a ON a.id = h.idAccount
    JOIN dbo.HistoryItem i ON i.idHistoryHeader = h.id
    JOIN dbo.BillItemAmt ba ON ba.id = i.idBillItemAmt
    WHERE h.actionTrxType = 0 AND h.amount > 0
      AND h.dateTimePosted >= DATEADD(year, -1, GETDATE())
      AND ba.billItemName IN ('WTR-USAGE', 'SWR-USAGE')
      AND a.class = 'RES' AND a.status = 'Active' AND a.cycle LIKE 'Q%'
    GROUP BY h.id HAVING SUM(i.amount) > 0
),
r AS (SELECT usage_amt, ROW_NUMBER() OVER (ORDER BY usage_amt) AS rn, COUNT(*) OVER () AS n FROM u)
SELECT (SELECT COUNT(*) FROM u) AS bills,
       (SELECT TOP 1 usage_amt FROM r WHERE rn = (n + 1) / 2) AS median_q,
       (SELECT TOP 1 usage_amt FROM r WHERE rn = (n + 9) / 10) AS p10_q,
       (SELECT TOP 1 usage_amt FROM r WHERE rn = (n * 9) / 10) AS p90_q
"@
    $usage = Invoke-BsaQuery -Database $UtilityDatabase -Sql $usageSql
    if (-not $usage -or [int]$usage.bills -lt 1000) { throw 'Usage-charge query returned too few bills; refusing to write.' }
    $customers = @(Invoke-BsaQuery -Database $UtilityDatabase -Sql "SELECT class, COUNT(*) AS n FROM dbo.Account WHERE status LIKE 'Active%' OR status = 'First Bill' GROUP BY class")
    $custRes = ($customers | Where-Object { $_.class -eq 'RES' } | Select-Object -First 1).n
    $custComm = ($customers | Where-Object { $_.class -eq 'COMM' } | Select-Object -First 1).n
    if (-not $custRes -or [int]$custRes -lt 1000) { throw 'Residential customer count implausible; refusing to write.' }
    $utility = [ordered]@{
        window                    = 'four quarterly bills posted in the 12 months before extraction'
        accounts_sewer_only       = [int]$sewerOnly.accounts
        median_annual_sewer_only  = [int][math]::Round([double]$sewerOnly.median_annual)
        accounts_water_and_sewer  = [int]$waterSewer.accounts
        median_annual_water_sewer = [int][math]::Round([double]$waterSewer.median_annual)
        customers_residential     = [int]$custRes
        customers_commercial      = [int]$custComm
        usage_charge_quarterly    = [ordered]@{
            bills  = [int]$usage.bills
            median = [int][math]::Round([double]$usage.median_q)
            p10    = [int][math]::Round([double]$usage.p10_q)
            p90    = [int][math]::Round([double]$usage.p90_q)
        }
    }
}

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
if ($utility) {
    $out['_utility_source'] = "City of Burton BS&A Utility Billing database ($UtilityDatabase), read-only aggregate export. Residential active accounts on quarterly cycles with four bills in the window; split by whether any water item was billed."
    $out['utility'] = $utility
}

$json = $out | ConvertTo-Json -Depth 5
$tmp = Join-Path $env:TEMP 'bsa-residential.json'
[System.IO.File]::WriteAllText($tmp, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Copy-Item -Path $tmp -Destination $OutPath -Force
Write-Host "Wrote $OutPath"
Write-Host ("  parcels={0} median_sev={1} pre_share={2:P1}" -f $out.residential.parcels, $out.residential.median_sev, ($out.residential.pre_parcels / $out.residential.parcels))
foreach ($s in $out.sales) { Write-Host ("  {0}: {1} sales, median {2:N0}" -f $s.year, $s.sales, $s.median_price) }
