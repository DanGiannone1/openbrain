Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Assert-AzCli {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "Azure CLI ('az') is required."
    }
}

function Ensure-AzLogin {
    param([string]$SubscriptionId)

    Assert-AzCli

    $accountJson = & az account show --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $accountJson) {
        throw "Azure CLI is not logged in. Run 'az login' first."
    }

    $account = $accountJson | ConvertFrom-Json
    if ($SubscriptionId -and $account.id -ne $SubscriptionId) {
        Write-Step "Selecting Azure subscription $SubscriptionId"
        & az account set --subscription $SubscriptionId | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to select Azure subscription $SubscriptionId."
        }
    }

    return ((& az account show --query id --output tsv).Trim())
}

function Ensure-Provider {
    param([Parameter(Mandatory = $true)][string]$Namespace)

    $state = (& az provider show --namespace $Namespace --query registrationState --output tsv 2>$null).Trim()
    if (-not $state) {
        throw "Unable to read provider state for $Namespace."
    }

    if ($state -ne "Registered") {
        Write-Step "Registering provider $Namespace"
        & az provider register --namespace $Namespace | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to register provider $Namespace."
        }
    }
}

function Get-StableSuffix {
    param(
        [Parameter(Mandatory = $true)][string]$InputText,
        [int]$Length = 5
    )

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($InputText)
        $hash = $sha.ComputeHash($bytes)
    }
    finally {
        $sha.Dispose()
    }

    $hex = [System.BitConverter]::ToString($hash).Replace("-", "").ToLowerInvariant()
    return $hex.Substring(0, $Length)
}

function Get-DeploymentStatePath {
    param([Parameter(Mandatory = $true)][string]$Environment)

    $stateDir = Join-Path $PSScriptRoot ".state"
    if (-not (Test-Path $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir | Out-Null
    }

    return (Join-Path $stateDir "$Environment.json")
}

function ConvertTo-Hashtable {
    param([Parameter(Mandatory = $true)]$InputObject)

    if ($null -eq $InputObject) {
        return $null
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        $hash = @{}
        foreach ($key in $InputObject.Keys) {
            $hash[$key] = ConvertTo-Hashtable -InputObject $InputObject[$key]
        }
        return $hash
    }

    if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
        $items = @()
        foreach ($item in $InputObject) {
            $items += @(ConvertTo-Hashtable -InputObject $item)
        }
        return $items
    }

    if ($InputObject -is [psobject]) {
        $hash = @{}
        foreach ($property in $InputObject.PSObject.Properties) {
            $hash[$property.Name] = ConvertTo-Hashtable -InputObject $property.Value
        }
        return $hash
    }

    return $InputObject
}

function Load-DeploymentState {
    param([Parameter(Mandatory = $true)][string]$Environment)

    $path = Get-DeploymentStatePath -Environment $Environment
    if (-not (Test-Path $path)) {
        return @{}
    }

    $raw = Get-Content -Path $path -Raw
    if (-not $raw.Trim()) {
        return @{}
    }

    return (ConvertTo-Hashtable -InputObject ($raw | ConvertFrom-Json))
}

function Save-DeploymentState {
    param(
        [Parameter(Mandatory = $true)][string]$Environment,
        [Parameter(Mandatory = $true)][hashtable]$State
    )

    $path = Get-DeploymentStatePath -Environment $Environment
    ($State | ConvertTo-Json -Depth 20) | Set-Content -Path $path
}

function Set-StateValues {
    param(
        [Parameter(Mandatory = $true)][hashtable]$State,
        [Parameter(Mandatory = $true)][hashtable]$Updates
    )

    foreach ($key in $Updates.Keys) {
        $State[$key] = $Updates[$key]
    }
}

function Invoke-AzJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $raw = & az @Arguments --output json
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($Arguments -join ' ')"
    }

    if (-not $raw) {
        return $null
    }

    return ($raw | ConvertFrom-Json)
}

function Invoke-AzTsv {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $raw = & az @Arguments --output tsv
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($Arguments -join ' ')"
    }

    if ($null -eq $raw) {
        return ""
    }

    return ([string]$raw).Trim()
}

function Try-Get-AzTsv {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    try {
        return Invoke-AzTsv -Arguments $Arguments
    }
    catch {
        return ""
    }
}

function Invoke-AzRestJson {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("GET", "PUT", "PATCH", "POST", "DELETE")][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [AllowNull()][string]$Body
    )

    $args = @("rest", "--method", $Method, "--uri", $Uri, "--output", "json")
    if ($Body) {
        $args += @("--body", $Body)
        $args += @("--headers", "Content-Type=application/json")
    }

    $raw = & az @args
    if ($LASTEXITCODE -ne 0) {
        throw "Azure REST call failed: az $($args -join ' ')"
    }

    if (-not $raw) {
        return $null
    }

    return ($raw | ConvertFrom-Json)
}

function Ensure-ResourceGroup {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Location
    )

    $exists = (& az group exists --name $Name).Trim()
    if ($exists -eq "true") {
        return
    }

    Write-Step "Creating resource group $Name"
    & az group create --name $Name --location $Location --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create resource group $Name."
    }
}

function Ensure-RoleAssignment {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalObjectId,
        [Parameter(Mandatory = $true)][string]$RoleName,
        [Parameter(Mandatory = $true)][string]$Scope,
        [string]$PrincipalType = "ServicePrincipal"
    )

    $assignmentId = Try-Get-AzTsv -Arguments @(
        "role", "assignment", "list",
        "--assignee-object-id", $PrincipalObjectId,
        "--scope", $Scope,
        "--role", $RoleName,
        "--query", "[0].id"
    )
    if ($assignmentId) {
        return
    }

    & az role assignment create `
        --assignee-object-id $PrincipalObjectId `
        --assignee-principal-type $PrincipalType `
        --role $RoleName `
        --scope $Scope `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to assign role '$RoleName' to principal '$PrincipalObjectId' at scope '$Scope'."
    }
}
