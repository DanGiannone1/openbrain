param(
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",

    [string]$SubscriptionId,
    [string]$ImageTag,
    [double]$Cpu = 0.5,
    [string]$Memory = "1.0Gi",
    [int]$MinReplicas = 0,
    [int]$MaxReplicas = 1
)

. (Join-Path $PSScriptRoot "common.ps1")

$subscription = Ensure-AzLogin -SubscriptionId $SubscriptionId
$state = Load-DeploymentState -Environment $Environment
if (-not $state.Count) {
    throw "No deployment state found for '$Environment'. Run deployment/setup-infrastructure.ps1 first."
}

$resourceGroup = $state.resourceGroup
$acrName = $state.acrName
$acrResourceGroup = $state.acrResourceGroup
$containerAppEnv = $state.containerAppEnvironment
$appName = $state.containerAppName
$imagePrefix = $state.imagePrefix
$repoRoot = Get-RepoRoot

if (-not $acrName -or -not $acrResourceGroup) {
    throw "Shared ACR details are missing from deployment state."
}

$ImageTag = if ($ImageTag) { $ImageTag } else { Get-Date -Format "yyyyMMddHHmmss" }

Write-Step "Building and pushing image ${imagePrefix}:$ImageTag to shared ACR $acrName"
& az acr build `
    --registry $acrName `
    --image "${imagePrefix}:$ImageTag" `
    --image "${imagePrefix}:latest" `
    $repoRoot `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Failed to build and push image to '$acrName'."
}

$acrLoginServer = Invoke-AzTsv -Arguments @(
    "acr", "show",
    "--resource-group", $acrResourceGroup,
    "--name", $acrName,
    "--query", "loginServer"
)
$acrUser = Invoke-AzTsv -Arguments @(
    "acr", "credential", "show",
    "--resource-group", $acrResourceGroup,
    "--name", $acrName,
    "--query", "username"
)
$acrPassword = Invoke-AzTsv -Arguments @(
    "acr", "credential", "show",
    "--resource-group", $acrResourceGroup,
    "--name", $acrName,
    "--query", "passwords[0].value"
)
$image = "${acrLoginServer}/${imagePrefix}:$ImageTag"

Write-Step "Deploying image $image to Container App $appName"
$appId = Try-Get-AzTsv -Arguments @(
    "containerapp", "show",
    "--resource-group", $resourceGroup,
    "--name", $appName,
    "--query", "id"
)

if ($appId) {
    & az containerapp registry set `
        --resource-group $resourceGroup `
        --name $appName `
        --server $acrLoginServer `
        --username $acrUser `
        --password $acrPassword `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update Container App registry credentials."
    }

    & az containerapp update `
        --resource-group $resourceGroup `
        --name $appName `
        --image $image `
        --cpu $Cpu `
        --memory $Memory `
        --min-replicas $MinReplicas `
        --max-replicas $MaxReplicas `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update Container App '$appName'."
    }
}
else {
    & az containerapp create `
        --resource-group $resourceGroup `
        --name $appName `
        --environment $containerAppEnv `
        --image $image `
        --ingress external `
        --target-port 8000 `
        --transport http `
        --cpu $Cpu `
        --memory $Memory `
        --min-replicas $MinReplicas `
        --max-replicas $MaxReplicas `
        --registry-server $acrLoginServer `
        --registry-username $acrUser `
        --registry-password $acrPassword `
        --env-vars "PORT=8000" `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Container App '$appName'."
    }
}

$fqdn = Invoke-AzTsv -Arguments @(
    "containerapp", "show",
    "--resource-group", $resourceGroup,
    "--name", $appName,
    "--query", "properties.configuration.ingress.fqdn"
)

Set-StateValues -State $state -Updates @{
    lastImageTag = $ImageTag
    lastImage = $image
    containerAppFqdn = $fqdn
}
Save-DeploymentState -Environment $Environment -State $state

Write-Host ""
Write-Host "Container App deployed: https://$fqdn/mcp" -ForegroundColor Green
