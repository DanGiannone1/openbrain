param(
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",

    [string]$Location = "eastus2",
    [string]$SubscriptionId,
    [string]$ResourceGroup,
    [string]$ContainerAppEnv,
    [string]$AppName,
    [string]$AcrName,
    [string]$ImagePrefix = "openbrain",
    [string]$CosmosAccountName,
    [string]$CosmosDatabase = "openbrain",
    [string]$CosmosContainer = "openbrain-data",

    [ValidateSet("free", "serverless", "provisioned")]
    [string]$CosmosMode,

    [switch]$CreateFoundryProject,
    [switch]$CreateFoundryHub,
    [string]$FoundryBaseName,
    [string]$FoundryFriendlyName,
    [string]$FoundryProjectName,
    [string]$FoundryDescription = "Open Brain Foundry project"
)

. (Join-Path $PSScriptRoot "common.ps1")

$subscription = Ensure-AzLogin -SubscriptionId $SubscriptionId
Ensure-Provider -Namespace "Microsoft.App"
Ensure-Provider -Namespace "Microsoft.DocumentDB"
Ensure-Provider -Namespace "Microsoft.OperationalInsights"
Ensure-Provider -Namespace "Microsoft.ContainerRegistry"
Ensure-Provider -Namespace "Microsoft.CognitiveServices"

$ResourceGroup = if ($ResourceGroup) { $ResourceGroup } else { "rg-openbrain-$Environment" }
$ContainerAppEnv = if ($ContainerAppEnv) { $ContainerAppEnv } else { "openbrain-env-$Environment" }
$AppName = if ($AppName) { $AppName } else { "openbrain-mcp-$Environment" }

$nameSeed = "$subscription/$ResourceGroup/$Environment"
$suffix = Get-StableSuffix -InputText $nameSeed
$AcrName = if ($AcrName) { $AcrName.ToLowerInvariant() } else { "openbrain${Environment}${suffix}" }
$CosmosAccountName = if ($CosmosAccountName) { $CosmosAccountName.ToLowerInvariant() } else { "openbrain-cosmos-$Environment-$suffix" }
$CosmosMode = if ($CosmosMode) { $CosmosMode } else { "serverless" }
$FoundryBaseName = if ($FoundryBaseName) { $FoundryBaseName.ToLowerInvariant() } else { "ob${Environment}${suffix}" }
$FoundryFriendlyName = if ($FoundryFriendlyName) { $FoundryFriendlyName } else { "Open Brain $Environment" }
$FoundryProjectName = if ($FoundryProjectName) { $FoundryProjectName.ToLowerInvariant() } else { "openbrain-$Environment" }
$logAnalyticsName = "log-openbrain-$Environment"

$state = Load-DeploymentState -Environment $Environment
Set-StateValues -State $state -Updates @{
    environment = $Environment
    subscriptionId = $subscription
    location = $Location
    resourceGroup = $ResourceGroup
    containerAppEnvironment = $ContainerAppEnv
    containerAppName = $AppName
    acrName = $AcrName
    imagePrefix = $ImagePrefix
    cosmosAccountName = $CosmosAccountName
    cosmosDatabase = $CosmosDatabase
    cosmosContainer = $CosmosContainer
    cosmosMode = $CosmosMode
}

Ensure-ResourceGroup -Name $ResourceGroup -Location $Location

Write-Step "Ensuring Log Analytics workspace $logAnalyticsName"
$workspaceId = Try-Get-AzTsv -Arguments @(
    "monitor", "log-analytics", "workspace", "show",
    "--resource-group", $ResourceGroup,
    "--workspace-name", $logAnalyticsName,
    "--query", "id"
)
if (-not $workspaceId) {
    & az monitor log-analytics workspace create `
        --resource-group $ResourceGroup `
        --workspace-name $logAnalyticsName `
        --location $Location `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Log Analytics workspace $logAnalyticsName."
    }
    $workspaceId = Invoke-AzTsv -Arguments @(
        "monitor", "log-analytics", "workspace", "show",
        "--resource-group", $ResourceGroup,
        "--workspace-name", $logAnalyticsName,
        "--query", "id"
    )
}

$workspaceCustomerId = Invoke-AzTsv -Arguments @(
    "monitor", "log-analytics", "workspace", "show",
    "--resource-group", $ResourceGroup,
    "--workspace-name", $logAnalyticsName,
    "--query", "customerId"
)
$workspaceSharedKey = Invoke-AzTsv -Arguments @(
    "monitor", "log-analytics", "workspace", "get-shared-keys",
    "--resource-group", $ResourceGroup,
    "--workspace-name", $logAnalyticsName,
    "--query", "primarySharedKey"
)

Set-StateValues -State $state -Updates @{
    logAnalyticsName = $logAnalyticsName
    logAnalyticsWorkspaceId = $workspaceId
}

Write-Step "Ensuring Azure Container Registry $AcrName"
$acrId = Try-Get-AzTsv -Arguments @(
    "acr", "show",
    "--resource-group", $ResourceGroup,
    "--name", $AcrName,
    "--query", "id"
)
if (-not $acrId) {
    & az acr create `
        --resource-group $ResourceGroup `
        --name $AcrName `
        --sku Basic `
        --admin-enabled true `
        --location $Location `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Azure Container Registry $AcrName."
    }
    $acrId = Invoke-AzTsv -Arguments @(
        "acr", "show",
        "--resource-group", $ResourceGroup,
        "--name", $AcrName,
        "--query", "id"
    )
}

$acrLoginServer = Invoke-AzTsv -Arguments @(
    "acr", "show",
    "--resource-group", $ResourceGroup,
    "--name", $AcrName,
    "--query", "loginServer"
)
Set-StateValues -State $state -Updates @{
    acrId = $acrId
    acrLoginServer = $acrLoginServer
}

Write-Step "Ensuring Container Apps environment $ContainerAppEnv"
$containerEnvId = Try-Get-AzTsv -Arguments @(
    "containerapp", "env", "show",
    "--resource-group", $ResourceGroup,
    "--name", $ContainerAppEnv,
    "--query", "id"
)
if (-not $containerEnvId) {
    & az containerapp env create `
        --resource-group $ResourceGroup `
        --name $ContainerAppEnv `
        --location $Location `
        --logs-workspace-id $workspaceCustomerId `
        --logs-workspace-key $workspaceSharedKey `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Container Apps environment $ContainerAppEnv."
    }
    $containerEnvId = Invoke-AzTsv -Arguments @(
        "containerapp", "env", "show",
        "--resource-group", $ResourceGroup,
        "--name", $ContainerAppEnv,
        "--query", "id"
    )
}

Set-StateValues -State $state -Updates @{
    containerAppEnvironmentId = $containerEnvId
}

Write-Step "Ensuring Cosmos DB account $CosmosAccountName"
$cosmosId = Try-Get-AzTsv -Arguments @(
    "cosmosdb", "show",
    "--resource-group", $ResourceGroup,
    "--name", $CosmosAccountName,
    "--query", "id"
)
if (-not $cosmosId) {
    $createArgs = @(
        "cosmosdb", "create",
        "--resource-group", $ResourceGroup,
        "--name", $CosmosAccountName,
        "--locations", "regionName=$Location", "failoverPriority=0", "isZoneRedundant=False",
        "--default-consistency-level", "Session",
        "--kind", "GlobalDocumentDB",
        "--output", "none"
    )

    switch ($CosmosMode) {
        "free" {
            $createArgs += @("--enable-free-tier", "true")
        }
        "serverless" {
            $createArgs += @("--capabilities", "EnableServerless")
        }
    }

    & az @createArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Cosmos DB account $CosmosAccountName."
    }
}

$capabilities = @(Invoke-AzJson -Arguments @(
    "cosmosdb", "show",
    "--resource-group", $ResourceGroup,
    "--name", $CosmosAccountName,
    "--query", "capabilities[].name"
))
if (-not $capabilities) {
    $capabilities = @()
}

if ($CosmosMode -eq "serverless" -and -not ($capabilities -contains "EnableServerless")) {
    throw "Cosmos DB account $CosmosAccountName is not serverless. This deployment expects a serverless account."
}

if (($CosmosMode -eq "free" -or $CosmosMode -eq "provisioned") -and ($capabilities -contains "EnableServerless")) {
    throw "Cosmos DB account $CosmosAccountName is already serverless and can't be reused with CosmosMode '$CosmosMode'."
}

if (-not ($capabilities -contains "EnableNoSQLVectorSearch")) {
    Write-Step "Enabling Cosmos DB vector search capability"
    & az cosmosdb update `
        --resource-group $ResourceGroup `
        --name $CosmosAccountName `
        --capabilities EnableNoSQLVectorSearch `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to enable vector search on Cosmos DB account $CosmosAccountName."
    }
}

$cosmosEndpoint = Invoke-AzTsv -Arguments @(
    "cosmosdb", "show",
    "--resource-group", $ResourceGroup,
    "--name", $CosmosAccountName,
    "--query", "documentEndpoint"
)
$cosmosId = Invoke-AzTsv -Arguments @(
    "cosmosdb", "show",
    "--resource-group", $ResourceGroup,
    "--name", $CosmosAccountName,
    "--query", "id"
)
Set-StateValues -State $state -Updates @{
    cosmosId = $cosmosId
    cosmosEndpoint = $cosmosEndpoint
}

Write-Step "Ensuring Cosmos SQL database $CosmosDatabase"
& az cosmosdb sql database create `
    --resource-group $ResourceGroup `
    --account-name $CosmosAccountName `
    --name $CosmosDatabase `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create Cosmos SQL database $CosmosDatabase."
}

Write-Step "Ensuring vector-enabled Cosmos container $CosmosContainer"
$containerUri = "https://management.azure.com/subscriptions/$subscription/resourceGroups/$ResourceGroup/providers/Microsoft.DocumentDB/databaseAccounts/$CosmosAccountName/sqlDatabases/$CosmosDatabase/containers/$CosmosContainer?api-version=2024-11-15"
$containerResource = @{
    id = $CosmosContainer
    partitionKey = @{
        paths = @("/userId")
        kind = "Hash"
        version = 2
    }
    indexingPolicy = @{
        indexingMode = "consistent"
        automatic = $true
        includedPaths = @(
            @{ path = "/*" }
        )
        excludedPaths = @(
            @{ path = "/`"_etag`"/?" }
        )
        vectorIndexes = @(
            @{
                path = "/embedding"
                type = "diskANN"
            }
        )
    }
    vectorEmbeddingPolicy = @{
        vectorEmbeddings = @(
            @{
                path = "/embedding"
                dataType = "float32"
                distanceFunction = "cosine"
                dimensions = 3072
            }
        )
    }
}
$containerProperties = @{
    resource = $containerResource
}
if ($CosmosMode -eq "provisioned" -or $CosmosMode -eq "free") {
    $containerProperties.options = @{
        throughput = 400
    }
}
$containerBody = @{
    location = $Location
    properties = $containerProperties
} | ConvertTo-Json -Depth 20 -Compress

$containerCreated = $false
for ($attempt = 1; $attempt -le 20 -and -not $containerCreated; $attempt++) {
    try {
        Invoke-AzRestJson -Method "PUT" -Uri $containerUri -Body $containerBody | Out-Null
        $containerCreated = $true
    }
    catch {
        if ($attempt -eq 20) {
            throw
        }
        Write-Host "Cosmos vector container create/update attempt $attempt failed, retrying in 45s..." -ForegroundColor Yellow
        Start-Sleep -Seconds 45
    }
}

if ($CreateFoundryHub -and -not $CreateFoundryProject) {
    Write-Host "CreateFoundryHub is deprecated. Deploying the current Microsoft Foundry resource/project model instead." -ForegroundColor Yellow
    $CreateFoundryProject = $true
}

if ($CreateFoundryProject) {
    Write-Step "Deploying Microsoft Foundry resource and project"
    $templatePath = Join-Path $PSScriptRoot "templates\foundry-resource-project.bicep"
    $deployment = Invoke-AzJson -Arguments @(
        "deployment", "group", "create",
        "--resource-group", $ResourceGroup,
        "--name", "openbrain-foundry-$Environment",
        "--template-file", $templatePath,
        "--parameters",
        "location=$Location",
        "aiFoundryName=$FoundryBaseName",
        "aiProjectName=$FoundryProjectName",
        "aiProjectDisplayName=$FoundryFriendlyName",
        "aiProjectDescription=$FoundryDescription"
    )

    $outputs = ConvertTo-Hashtable -InputObject $deployment.properties.outputs
    Set-StateValues -State $state -Updates @{
        aiFoundryName = $outputs.aiFoundryName.value
        aiFoundryId = $outputs.aiFoundryId.value
        aiFoundryEndpoint = $outputs.aiFoundryEndpoint.value
        aiServicesName = $outputs.aiFoundryName.value
        aiServicesId = $outputs.aiFoundryId.value
        aiServicesEndpoint = $outputs.aiFoundryEndpoint.value
        foundryProjectName = $outputs.aiProjectName.value
        foundryProjectId = $outputs.aiProjectId.value
        foundryMode = "resource-project"
    }
}

Save-DeploymentState -Environment $Environment -State $state

Write-Host ""
Write-Host "Infrastructure ready. State saved to $(Get-DeploymentStatePath -Environment $Environment)" -ForegroundColor Green
