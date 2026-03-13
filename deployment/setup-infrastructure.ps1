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
    [string]$EmbeddingModelName = "text-embedding-3-large",
    [string]$EmbeddingResourceName,
    [string]$EmbeddingResourceLocation = "eastus2"
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
$EmbeddingResourceName = if ($EmbeddingResourceName) { $EmbeddingResourceName.ToLowerInvariant() } else { "openbrain-openai-$Environment-$suffix" }
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

$cosmosReady = $false
for ($attempt = 1; $attempt -le 20 -and -not $cosmosReady; $attempt++) {
    $cosmosId = Try-Get-AzTsv -Arguments @(
        "cosmosdb", "show",
        "--resource-group", $ResourceGroup,
        "--name", $CosmosAccountName,
        "--query", "id"
    )
    if ($cosmosId) {
        $cosmosReady = $true
        break
    }

    if ($attempt -eq 20) {
        throw "Cosmos DB account '$CosmosAccountName' was created but never became readable."
    }

    Start-Sleep -Seconds 15
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
$containerId = Try-Get-AzTsv -Arguments @(
    "cosmosdb", "sql", "container", "show",
    "--resource-group", $ResourceGroup,
    "--account-name", $CosmosAccountName,
    "--database-name", $CosmosDatabase,
    "--name", $CosmosContainer,
    "--query", "id"
)

if (-not $containerId) {
    $indexingPolicy = @{
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
    $vectorEmbeddingPolicy = @{
        vectorEmbeddings = @(
            @{
                path = "/embedding"
                dataType = "float32"
                distanceFunction = "cosine"
                dimensions = 3072
            }
        )
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "openbrain"
    if (-not (Test-Path $tempRoot)) {
        New-Item -ItemType Directory -Path $tempRoot | Out-Null
    }
    $indexingPolicyPath = Join-Path $tempRoot "cosmos-indexing-policy-$Environment.json"
    $vectorPolicyPath = Join-Path $tempRoot "cosmos-vector-policy-$Environment.json"
    ($indexingPolicy | ConvertTo-Json -Depth 10) | Set-Content -Path $indexingPolicyPath
    ($vectorEmbeddingPolicy | ConvertTo-Json -Depth 10) | Set-Content -Path $vectorPolicyPath

    try {
        $createArgs = @(
            "cosmosdb", "sql", "container", "create",
            "--resource-group", $ResourceGroup,
            "--account-name", $CosmosAccountName,
            "--database-name", $CosmosDatabase,
            "--name", $CosmosContainer,
            "--partition-key-path", "/userId",
            "--partition-key-version", "2",
            "--idx", "@$indexingPolicyPath",
            "--vector-embeddings", "@$vectorPolicyPath",
            "--output", "none"
        )
        if ($CosmosMode -eq "provisioned") {
            $createArgs += @("--throughput", "400")
        }

        $containerCreated = $false
        for ($attempt = 1; $attempt -le 20 -and -not $containerCreated; $attempt++) {
            try {
                & az @createArgs
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to create Cosmos container '$CosmosContainer'."
                }
                $containerCreated = $true
            }
            catch {
                if ($attempt -eq 20) {
                    throw
                }
                Write-Host "Cosmos container create attempt $attempt failed, retrying in 45s..." -ForegroundColor Yellow
                Start-Sleep -Seconds 45
            }
        }
    }
    finally {
        Remove-Item -Path $indexingPolicyPath -ErrorAction SilentlyContinue
        Remove-Item -Path $vectorPolicyPath -ErrorAction SilentlyContinue
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
        foundryProjectName = $outputs.aiProjectName.value
        foundryProjectId = $outputs.aiProjectId.value
        foundryMode = "resource-project"
    }
}

$embeddingAccountName = ""
$embeddingAccountResourceGroup = $ResourceGroup
$foundryAccountName = if ($state.ContainsKey("aiFoundryName") -and $state.aiFoundryName) {
    [string]$state.aiFoundryName
}
else {
    ""
}

if ($foundryAccountName) {
    try {
        Get-PreferredModelSpec `
            -ResourceGroupName $ResourceGroup `
            -AccountName $foundryAccountName `
            -ModelName $EmbeddingModelName | Out-Null

        $embeddingAccountName = $foundryAccountName
        $foundryAccount = Invoke-AzJson -Arguments @(
            "cognitiveservices", "account", "show",
            "--resource-group", $ResourceGroup,
            "--name", $foundryAccountName
        )
        Set-StateValues -State $state -Updates @{
            aiServicesName = $foundryAccountName
            aiServicesId = [string]$foundryAccount.id
            aiServicesEndpoint = [string]$foundryAccount.properties.endpoint
            aiServicesKind = [string]$foundryAccount.kind
        }
    }
    catch {
        Write-Host "Embedding model '$EmbeddingModelName' is unavailable on Foundry account '$foundryAccountName'. Falling back to a dedicated Azure OpenAI resource." -ForegroundColor Yellow
    }
}

if (-not $embeddingAccountName) {
    Write-Step "Ensuring Azure OpenAI embedding resource $EmbeddingResourceName"
    $embeddingAccountId = Try-Get-AzTsv -Arguments @(
        "cognitiveservices", "account", "show",
        "--resource-group", $ResourceGroup,
        "--name", $EmbeddingResourceName,
        "--query", "id"
    )
    if (-not $embeddingAccountId) {
        & az cognitiveservices account create `
            --name $EmbeddingResourceName `
            --resource-group $ResourceGroup `
            --kind OpenAI `
            --sku S0 `
            --location $EmbeddingResourceLocation `
            --assign-identity `
            --custom-domain $EmbeddingResourceName `
            --yes `
            --output none
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create Azure OpenAI embedding resource '$EmbeddingResourceName'."
        }
    }

    $embeddingAccount = Invoke-AzJson -Arguments @(
        "cognitiveservices", "account", "show",
        "--resource-group", $ResourceGroup,
        "--name", $EmbeddingResourceName
    )
    $embeddingAccountName = [string]$embeddingAccount.name
    Set-StateValues -State $state -Updates @{
        aiServicesName = $embeddingAccountName
        aiServicesId = [string]$embeddingAccount.id
        aiServicesEndpoint = [string]$embeddingAccount.properties.endpoint
        aiServicesKind = [string]$embeddingAccount.kind
        aiServicesLocation = [string]$embeddingAccount.location
    }
}

if ($embeddingAccountName) {
    Ensure-EmbeddingDeployment `
        -ResourceGroupName $embeddingAccountResourceGroup `
        -AccountName $embeddingAccountName `
        -DeploymentName $EmbeddingDeploymentName `
        -ModelName $EmbeddingModelName
}

Save-DeploymentState -Environment $Environment -State $state

Write-Host ""
Write-Host "Infrastructure ready. State saved to $(Get-DeploymentStatePath -Environment $Environment)" -ForegroundColor Green
