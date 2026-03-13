param(
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",

    [string]$SubscriptionId,
    [string]$AiResourceName,
    [string]$EmbeddingDeployment = "text-embedding-3-large",
    [bool]$DisableAuth = $false,
    [string]$DefaultUserId = "dev-user",
    [string]$OpenBrainApiToken,
    [string]$LogLevel = "INFO",
    [int]$Port = 8000
)

. (Join-Path $PSScriptRoot "common.ps1")

$subscription = Ensure-AzLogin -SubscriptionId $SubscriptionId
$state = Load-DeploymentState -Environment $Environment
if (-not $state.Count) {
    throw "No deployment state found for '$Environment'. Run deployment/setup-infrastructure.ps1 first."
}

$resourceGroup = $state.resourceGroup
$appName = $state.containerAppName
$cosmosAccountName = $state.cosmosAccountName
$cosmosDatabase = $state.cosmosDatabase
$cosmosContainer = $state.cosmosContainer

$appId = Try-Get-AzTsv -Arguments @(
    "containerapp", "show",
    "--resource-group", $resourceGroup,
    "--name", $appName,
    "--query", "id"
)
if (-not $appId) {
    throw "Container App '$appName' does not exist yet. Run deployment/deploy.ps1 first."
}

$cosmosHost = Invoke-AzTsv -Arguments @(
    "cosmosdb", "show",
    "--resource-group", $resourceGroup,
    "--name", $cosmosAccountName,
    "--query", "documentEndpoint"
)
$cosmosKey = Invoke-AzTsv -Arguments @(
    "cosmosdb", "keys", "list",
    "--resource-group", $resourceGroup,
    "--name", $cosmosAccountName,
    "--query", "primaryMasterKey"
)

if (-not $AiResourceName) {
    if ($state.ContainsKey("aiServicesName") -and $state.aiServicesName) {
        $AiResourceName = [string]$state.aiServicesName
    }
    elseif ($state.ContainsKey("aiFoundryName") -and $state.aiFoundryName) {
        $AiResourceName = [string]$state.aiFoundryName
    }
    else {
        throw "No AI resource name supplied and none is recorded in deployment state."
    }
}

$EmbeddingDeployment = if ($EmbeddingDeployment) {
    $EmbeddingDeployment
}
elseif ($state.ContainsKey("embeddingDeployment") -and $state.embeddingDeployment) {
    [string]$state.embeddingDeployment
}
else {
    "text-embedding-3-large"
}

$aiEndpoint = Try-Get-AzTsv -Arguments @(
    "cognitiveservices", "account", "show",
    "--resource-group", $resourceGroup,
    "--name", $AiResourceName,
    "--query", "properties.endpoint"
)
if (-not $aiEndpoint) {
    $aiEndpoint = Try-Get-AzTsv -Arguments @(
        "cognitiveservices", "account", "show",
        "--resource-group", $resourceGroup,
        "--name", $AiResourceName,
        "--query", "properties.endpoints['Azure AI Model Inference API']"
    )
}
if (-not $aiEndpoint) {
    throw "Unable to determine an inference endpoint for AI resource '$AiResourceName'."
}

$embeddingDeploymentId = Try-Get-AzTsv -Arguments @(
    "cognitiveservices", "account", "deployment", "show",
    "--resource-group", $resourceGroup,
    "--name", $AiResourceName,
    "--deployment-name", $EmbeddingDeployment,
    "--query", "id"
)
if (-not $embeddingDeploymentId) {
    throw "Embedding deployment '$EmbeddingDeployment' does not exist on '$AiResourceName'."
}

$aiKey = Invoke-AzTsv -Arguments @(
    "cognitiveservices", "account", "keys", "list",
    "--resource-group", $resourceGroup,
    "--name", $AiResourceName,
    "--query", "key1"
)

Write-Step "Ensuring system-assigned managed identity on Container App $appName"
& az containerapp identity assign `
    --resource-group $resourceGroup `
    --name $appName `
    --system-assigned `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Failed to assign a system-managed identity to Container App '$appName'."
}

$containerAppPrincipalId = Invoke-AzTsv -Arguments @(
    "containerapp", "show",
    "--resource-group", $resourceGroup,
    "--name", $appName,
    "--query", "identity.principalId"
)
if (-not $containerAppPrincipalId) {
    throw "Container App '$appName' does not expose a managed identity principal id."
}

$aiResourceId = Invoke-AzTsv -Arguments @(
    "cognitiveservices", "account", "show",
    "--resource-group", $resourceGroup,
    "--name", $AiResourceName,
    "--query", "id"
)
if (-not $aiResourceId) {
    throw "Unable to resolve Azure OpenAI resource id for '$AiResourceName'."
}

Write-Step "Ensuring Container App identity can access Azure OpenAI resource $AiResourceName"
Ensure-RoleAssignment `
    -PrincipalObjectId $containerAppPrincipalId `
    -RoleName "Cognitive Services OpenAI User" `
    -Scope $aiResourceId

$OpenBrainApiToken = if ($OpenBrainApiToken) {
    $OpenBrainApiToken
}
elseif ($env:OPENBRAIN_API_TOKEN) {
    [string]([Environment]::GetEnvironmentVariable("OPENBRAIN_API_TOKEN"))
}
elseif ($state.ContainsKey("openBrainApiToken") -and $state.openBrainApiToken) {
    [string]$state.openBrainApiToken
}
else {
    [Guid]::NewGuid().ToString("N")
}

Write-Step "Setting Container App secrets"
& az containerapp secret set `
    --resource-group $resourceGroup `
    --name $appName `
    --secrets `
    "cosmos-key=$cosmosKey" `
    "ai-foundry-api-key=$aiKey" `
    "openbrain-api-token=$OpenBrainApiToken" `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Failed to update Container App secrets."
}

Write-Step "Setting Container App environment variables"
& az containerapp update `
    --resource-group $resourceGroup `
    --name $appName `
    --set-env-vars `
    "COSMOS_HOST=$cosmosHost" `
    "COSMOS_KEY=secretref:cosmos-key" `
    "COSMOS_DATABASE=$cosmosDatabase" `
    "COSMOS_CONTAINER=$cosmosContainer" `
    "AI_FOUNDRY_ENDPOINT=$($aiEndpoint.TrimEnd('/'))" `
    "AI_FOUNDRY_API_KEY=secretref:ai-foundry-api-key" `
    "AI_FOUNDRY_EMBEDDING_DEPLOYMENT=$EmbeddingDeployment" `
    "DISABLE_AUTH=$($DisableAuth.ToString().ToLowerInvariant())" `
    "DEFAULT_USER_ID=$DefaultUserId" `
    "OPENBRAIN_API_TOKEN=secretref:openbrain-api-token" `
    "ENVIRONMENT=$Environment" `
    "LOG_LEVEL=$LogLevel" `
    "PORT=$Port" `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Failed to update Container App environment variables."
}

Set-StateValues -State $state -Updates @{
    aiServicesName = $AiResourceName
    aiServicesEndpoint = $aiEndpoint.TrimEnd("/")
    embeddingDeployment = $EmbeddingDeployment
    containerAppPrincipalId = $containerAppPrincipalId
    openBrainApiToken = $OpenBrainApiToken
    disableAuth = $DisableAuth
    defaultUserId = $DefaultUserId
}
Save-DeploymentState -Environment $Environment -State $state

Write-Host ""
Write-Host "Container App secrets and environment variables updated." -ForegroundColor Green
