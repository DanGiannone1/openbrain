param(
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",

    [string]$Location = "eastus2",
    [string]$SubscriptionId,
    [string]$ResourceGroup,
    [string]$ContainerAppEnv,
    [string]$AppName,
    [string]$SharedAcrName,
    [string]$SharedAcrResourceGroup,
    [string]$SharedAcrLoginServer,
    [string]$ImagePrefix = "openbrain",
    [string]$CosmosAccountName,
    [string]$CosmosDatabase = "openbrain",
    [string]$CosmosContainer = "openbrain-data",
    [ValidateSet("serverless", "provisioned")]
    [string]$CosmosMode = "serverless",
    [switch]$CreateFoundryProject,
    [switch]$CreateFoundryHub,
    [string]$FoundryBaseName,
    [string]$FoundryFriendlyName,
    [string]$FoundryProjectName,
    [string]$FoundryDescription = "Open Brain Foundry project",
    [bool]$RunWhatIf = $true,
    [string]$EmbeddingDeploymentName = "text-embedding-3-large",
    [string]$EmbeddingModelName = "text-embedding-3-large"
)

. (Join-Path $PSScriptRoot "common.ps1")

function Resolve-SharedAcrValue {
    param(
        [string]$ExplicitValue,
        [hashtable]$State,
        [string]$StateKey,
        [string[]]$EnvKeys
    )

    if ($ExplicitValue) {
        return $ExplicitValue
    }
    if ($State.ContainsKey($StateKey) -and $State[$StateKey]) {
        return [string]$State[$StateKey]
    }
    foreach ($envKey in $EnvKeys) {
        $envValue = [Environment]::GetEnvironmentVariable($envKey)
        if ($envValue) {
            return [string]$envValue
        }
    }
    return ""
}

function Get-PreferredModelSpec {
    param(
        [string]$ResourceGroupName,
        [string]$AccountName,
        [string]$ModelName
    )

    $models = @(Invoke-AzJson -Arguments @(
        "cognitiveservices", "account", "list-models",
        "--resource-group", $ResourceGroupName,
        "--name", $AccountName
    ))
    if (-not $models.Count) {
        throw "No models were returned for AI resource '$AccountName'."
    }

    $matching = @($models | Where-Object { $_.name -eq $ModelName })
    if (-not $matching.Count) {
        throw "Model '$ModelName' is not available on AI resource '$AccountName'."
    }

    $preferred = @($matching | Where-Object { $_.format -eq "OpenAI" })
    if (-not $preferred.Count) {
        $preferred = $matching
    }

    $selected = $preferred |
        Sort-Object -Property @{ Expression = { [string]$_.version } ; Descending = $true } |
        Select-Object -First 1

    $skus = @($selected.skus)
    if (-not $skus.Count) {
        throw "Model '$ModelName' on '$AccountName' does not advertise any deployable SKUs."
    }

    $sku = $skus |
        Sort-Object -Property @{ Expression = {
            switch ($_.name) {
                "GlobalStandard" { 3 }
                "Standard" { 2 }
                default { 1 }
            }
        } ; Descending = $true } |
        Select-Object -First 1

    return @{
        name = [string]$selected.name
        format = [string]$selected.format
        version = [string]$selected.version
        skuName = [string]$sku.name
        skuCapacity = if ($sku.capacity -and $sku.capacity.default) { [int]$sku.capacity.default } else { 1 }
    }
}

function Ensure-EmbeddingDeployment {
    param(
        [string]$ResourceGroupName,
        [string]$AccountName,
        [string]$DeploymentName,
        [string]$ModelName
    )

    $existingDeployment = Try-Get-AzTsv -Arguments @(
        "cognitiveservices", "account", "deployment", "show",
        "--resource-group", $ResourceGroupName,
        "--name", $AccountName,
        "--deployment-name", $DeploymentName,
        "--query", "id"
    )
    if ($existingDeployment) {
        return
    }

    $modelSpec = Get-PreferredModelSpec -ResourceGroupName $ResourceGroupName -AccountName $AccountName -ModelName $ModelName

    Write-Step "Creating embedding deployment $DeploymentName on $AccountName"
    & az cognitiveservices account deployment create `
        --resource-group $ResourceGroupName `
        --name $AccountName `
        --deployment-name $DeploymentName `
        --model-name $modelSpec.name `
        --model-version $modelSpec.version `
        --model-format $modelSpec.format `
        --sku-capacity $modelSpec.skuCapacity `
        --sku-name $modelSpec.skuName `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create embedding deployment '$DeploymentName' on '$AccountName'."
    }

    for ($attempt = 1; $attempt -le 40; $attempt++) {
        $provisioningState = Try-Get-AzTsv -Arguments @(
            "cognitiveservices", "account", "deployment", "show",
            "--resource-group", $ResourceGroupName,
            "--name", $AccountName,
            "--deployment-name", $DeploymentName,
            "--query", "properties.provisioningState"
        )
        if ($provisioningState -eq "Succeeded") {
            return
        }
        if ($provisioningState -eq "Failed") {
            throw "Embedding deployment '$DeploymentName' entered a failed state."
        }
        Start-Sleep -Seconds 15
    }

    throw "Embedding deployment '$DeploymentName' did not reach Succeeded within the expected time."
}

$subscription = Ensure-AzLogin -SubscriptionId $SubscriptionId
Ensure-Provider -Namespace "Microsoft.App"
Ensure-Provider -Namespace "Microsoft.DocumentDB"
Ensure-Provider -Namespace "Microsoft.OperationalInsights"
Ensure-Provider -Namespace "Microsoft.CognitiveServices"

$ResourceGroup = if ($ResourceGroup) { $ResourceGroup } else { "rg-openbrain-$Environment" }
$ContainerAppEnv = if ($ContainerAppEnv) { $ContainerAppEnv } else { "openbrain-env-$Environment" }
$AppName = if ($AppName) { $AppName } else { "openbrain-mcp-$Environment" }

$nameSeed = "$subscription/$ResourceGroup/$Environment"
$suffix = Get-StableSuffix -InputText $nameSeed
$CosmosAccountName = if ($CosmosAccountName) { $CosmosAccountName.ToLowerInvariant() } else { "openbrain-cosmos-$Environment-$suffix" }
$FoundryBaseName = if ($FoundryBaseName) { $FoundryBaseName.ToLowerInvariant() } else { "ob${Environment}${suffix}" }
$FoundryFriendlyName = if ($FoundryFriendlyName) { $FoundryFriendlyName } else { "Open Brain $Environment" }
$FoundryProjectName = if ($FoundryProjectName) { $FoundryProjectName.ToLowerInvariant() } else { "openbrain-$Environment" }
$logAnalyticsName = "log-openbrain-$Environment"

$state = Load-DeploymentState -Environment $Environment
$SharedAcrName = Resolve-SharedAcrValue -ExplicitValue $SharedAcrName -State $state -StateKey "acrName" -EnvKeys @("ACR_NAME", "OPENBRAIN_SHARED_ACR_NAME")
$SharedAcrResourceGroup = Resolve-SharedAcrValue -ExplicitValue $SharedAcrResourceGroup -State $state -StateKey "acrResourceGroup" -EnvKeys @("RESOURCE_GROUP_SHARED", "OPENBRAIN_SHARED_ACR_RESOURCE_GROUP")
$SharedAcrLoginServer = Resolve-SharedAcrValue -ExplicitValue $SharedAcrLoginServer -State $state -StateKey "acrLoginServer" -EnvKeys @("ACR_SERVER", "OPENBRAIN_SHARED_ACR_LOGIN_SERVER")

if (-not $SharedAcrName) {
    throw "A shared ACR name is required. Pass -SharedAcrName or set ACR_NAME / OPENBRAIN_SHARED_ACR_NAME."
}
if (-not $SharedAcrResourceGroup) {
    throw "A shared ACR resource group is required. Pass -SharedAcrResourceGroup or set RESOURCE_GROUP_SHARED / OPENBRAIN_SHARED_ACR_RESOURCE_GROUP."
}

Set-StateValues -State $state -Updates @{
    environment = $Environment
    subscriptionId = $subscription
    location = $Location
    resourceGroup = $ResourceGroup
    containerAppEnvironment = $ContainerAppEnv
    containerAppName = $AppName
    acrName = $SharedAcrName
    acrResourceGroup = $SharedAcrResourceGroup
    imagePrefix = $ImagePrefix
    cosmosAccountName = $CosmosAccountName
    cosmosDatabase = $CosmosDatabase
    cosmosContainer = $CosmosContainer
    cosmosMode = $CosmosMode
    embeddingDeployment = $EmbeddingDeploymentName
}

Ensure-ResourceGroup -Name $ResourceGroup -Location $Location

Write-Step "Resolving shared Azure Container Registry $SharedAcrName"
$acrId = Try-Get-AzTsv -Arguments @(
    "acr", "show",
    "--resource-group", $SharedAcrResourceGroup,
    "--name", $SharedAcrName,
    "--query", "id"
)
if (-not $acrId) {
    throw "Shared Azure Container Registry '$SharedAcrName' was not found in resource group '$SharedAcrResourceGroup'."
}
if (-not $SharedAcrLoginServer) {
    $SharedAcrLoginServer = Invoke-AzTsv -Arguments @(
        "acr", "show",
        "--resource-group", $SharedAcrResourceGroup,
        "--name", $SharedAcrName,
        "--query", "loginServer"
    )
}
Set-StateValues -State $state -Updates @{
    acrId = $acrId
    acrLoginServer = $SharedAcrLoginServer
}

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
        throw "Failed to create Log Analytics workspace '$logAnalyticsName'."
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
        throw "Failed to create Container Apps environment '$ContainerAppEnv'."
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
    if ($CosmosMode -eq "serverless") {
        $createArgs += @("--capabilities", "EnableServerless")
    }
    & az @createArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Cosmos DB account '$CosmosAccountName'."
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
    throw "Cosmos DB account '$CosmosAccountName' is not serverless."
}
if (-not ($capabilities -contains "EnableNoSQLVectorSearch")) {
    Write-Step "Enabling Cosmos DB vector search capability"
    & az cosmosdb update `
        --resource-group $ResourceGroup `
        --name $CosmosAccountName `
        --capabilities EnableNoSQLVectorSearch `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to enable vector search on Cosmos DB account '$CosmosAccountName'."
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
    throw "Failed to create Cosmos SQL database '$CosmosDatabase'."
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
            @{ path = "/embedding/*" }
            @{ path = "/rawText/?" }
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
$containerProperties = @{ resource = $containerResource }
if ($CosmosMode -eq "provisioned") {
    $containerProperties.options = @{ throughput = 400 }
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
        Write-Host "Cosmos container create/update attempt $attempt failed, retrying in 45s..." -ForegroundColor Yellow
        Start-Sleep -Seconds 45
    }
}

if ($CreateFoundryHub -and -not $CreateFoundryProject) {
    Write-Host "CreateFoundryHub is deprecated. Deploying the current Microsoft Foundry resource/project model instead." -ForegroundColor Yellow
    $CreateFoundryProject = $true
}

if ($CreateFoundryProject) {
    $templatePath = Join-Path $PSScriptRoot "templates\foundry-resource-project.bicep"
    if ($RunWhatIf) {
        Write-Step "Running what-if for Microsoft Foundry resource/project deployment"
        & az deployment group what-if `
            --resource-group $ResourceGroup `
            --name "openbrain-foundry-$Environment-preview" `
            --template-file $templatePath `
            --parameters `
            "location=$Location" `
            "aiFoundryName=$FoundryBaseName" `
            "aiProjectName=$FoundryProjectName" `
            "aiProjectDisplayName=$FoundryFriendlyName" `
            "aiProjectDescription=$FoundryDescription" `
            --output table
        if ($LASTEXITCODE -ne 0) {
            throw "Foundry what-if failed."
        }
    }

    Write-Step "Deploying Microsoft Foundry resource and project"
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

$aiResourceName = if ($state.ContainsKey("aiFoundryName") -and $state.aiFoundryName) {
    [string]$state.aiFoundryName
}
elseif ($state.ContainsKey("aiServicesName") -and $state.aiServicesName) {
    [string]$state.aiServicesName
}
else {
    ""
}

if ($aiResourceName) {
    Ensure-EmbeddingDeployment `
        -ResourceGroupName $ResourceGroup `
        -AccountName $aiResourceName `
        -DeploymentName $EmbeddingDeploymentName `
        -ModelName $EmbeddingModelName
}

Save-DeploymentState -Environment $Environment -State $state

Write-Host ""
Write-Host "Infrastructure ready. State saved to $(Get-DeploymentStatePath -Environment $Environment)" -ForegroundColor Green
