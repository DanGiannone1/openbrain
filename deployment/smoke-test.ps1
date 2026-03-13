param(
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",

    [string]$ExpectedStatusCodes = "200,400,404,405",
    [string]$Path = "/mcp"
)

. (Join-Path $PSScriptRoot "common.ps1")

$state = Load-DeploymentState -Environment $Environment
if (-not $state.Count) {
    throw "No deployment state found for '$Environment'."
}

$fqdn = if ($state.ContainsKey("containerAppFqdn")) { [string]$state.containerAppFqdn } else { "" }
if (-not $fqdn) {
    throw "Container App FQDN is missing from deployment state. Run deployment/deploy.ps1 first."
}

$apiToken = if ($state.ContainsKey("openBrainApiToken")) { [string]$state.openBrainApiToken } else { "" }
$uri = "https://$fqdn$Path"
$statusCode = & curl.exe -s -o NUL -w "%{http_code}" -H "Authorization: Bearer $apiToken" $uri

if (-not $statusCode -or $statusCode -eq "000") {
    throw "Smoke test failed: no HTTP response from $uri"
}

$allowed = $ExpectedStatusCodes.Split(",") | ForEach-Object { $_.Trim() }
if ($allowed -notcontains $statusCode) {
    throw "Smoke test failed: $uri returned HTTP $statusCode (allowed: $ExpectedStatusCodes)"
}

Write-Host ""
Write-Host "Smoke test passed: $uri returned HTTP $statusCode" -ForegroundColor Green
