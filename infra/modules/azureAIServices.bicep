

@description('Location for all resources.')
param location string = resourceGroup().location

@allowed([
  'S0'
])
param sku string = 'S0'

@description('Name of the AI Services account.')
param aiServicesName string

resource aisaccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aiServicesName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: sku
  }
  kind: 'AIServices'
  properties: {
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Deny'
    }
    disableLocalAuth: true
  }
}


resource aisaccountgpt4omodel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aisaccount
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-05-13'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    currentCapacity: 30
  }
}

output aiServiceEndpoint string = aisaccount.properties.endpoint
output aiServiceVersion string = aisaccountgpt4omodel.properties.model.version
