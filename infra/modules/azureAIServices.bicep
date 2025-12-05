@description('Location for all resources.')
param location string = resourceGroup().location

@description('Azure AI Foundry hub (Cognitive Services account) name to either create or update.')
param aiHubName string

@description('Azure AI Foundry project name to create inside the hub.')
param aiProjectName string

@description('Friendly display name for the project.')
param projectDisplayName string = aiProjectName

@description('Optional description for the project.')
param projectDescription string = ''

@description('Name of the GPT-4 deployment to create inside the Azure AI hub.')
param gptDeploymentName string = 'gpt4o'

@description('Model identifier to deploy (OpenAI catalog name).')
param gptModelName string = 'gpt-4o'

@description('Specific model version to deploy.')
param gptModelVersion string = '2024-08-06'

@description('Manual capacity for the GPT-4 deployment.')
@minValue(1)
param gptCapacity int = 1


resource aiHub 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiHubName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiHubName
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}


resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: aiProjectName
  parent: aiHub
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectDisplayName
    description: projectDescription
  }
}

resource gpt4Deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  name: gptDeploymentName
  parent: aiHub
  properties: {
    model: {
      format: 'OpenAI'
      name: gptModelName
      version: gptModelVersion
    }
    raiPolicyName: 'Microsoft.Default'
  }
  sku: {
    name: 'Standard'
    capacity: gptCapacity
  }
}

output projectName string = aiProjectName
output projectId string = aiProject.id
output projectPrincipalId string = aiProject.identity.principalId
output projectEndpoint string = 'https://${aiHubName}.services.ai.azure.com/api/projects/${aiProjectName}'
output gptDeploymentName string = gptDeploymentName
output aiHubEndpoint string = 'https://${aiHubName}.cognitiveservices.azure.com/'
@secure()
output aiHubPrimaryKey string = aiHub.listKeys().key1
