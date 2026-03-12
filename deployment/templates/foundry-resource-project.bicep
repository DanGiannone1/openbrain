@description('Azure region used for the deployment of all resources.')
param location string = resourceGroup().location

@minLength(2)
@maxLength(64)
@description('Globally unique name for the Microsoft Foundry resource.')
param aiFoundryName string

@minLength(2)
@maxLength(64)
@description('Name of the child project created under the Foundry resource.')
param aiProjectName string

@description('Display name for the Foundry project.')
param aiProjectDisplayName string = aiProjectName

@description('Description shown for the Foundry project.')
param aiProjectDescription string = 'Open Brain Foundry project'

@description('Tags to apply to all created resources.')
param tags object = {}

// Use the current stable Foundry resource model instead of the legacy hub/project pattern.
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-09-01' = {
  name: aiFoundryName
  location: location
  tags: tags
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiFoundryName
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
    restrictOutboundNetworkAccess: false
  }
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-09-01' = {
  parent: aiFoundry
  name: aiProjectName
  location: location
  tags: tags
  properties: {
    displayName: aiProjectDisplayName
    description: aiProjectDescription
  }
}

output aiFoundryName string = aiFoundry.name
output aiFoundryId string = aiFoundry.id
output aiFoundryEndpoint string = 'https://${aiFoundry.name}.services.ai.azure.com'
output aiProjectName string = aiProject.name
output aiProjectId string = aiProject.id
