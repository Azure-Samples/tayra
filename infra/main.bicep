targetScope = 'subscription'

@description('The location where the resources will be created')
@allowed([
  'eastus'
  'eastus2'
  'westus'
  'westus2'
  'centralus']
)
param location string = 'eastus2'

param deploymentTimestamp string = utcNow('yyyyMMddHHmmss')

param uniquePrefix string = substring(uniqueString(subscription().id, deploymentTimestamp), 0, 4)

@description('The name of the resource group to create')
param resourceGroupName string = 'rg-tayra-callcenter'

@description('cosmosdb account name. It has to be unique.Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param cosmosDbAccountName string = 'tayracosmosdb-${uniquePrefix}'

@description('cosmosdb database name. It has to be unique.Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param cosmosDbName string = 'tayradb'

@description('That name is the name of our application. It has to be unique.Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param storageAccountName string = 'tayrastg${uniquePrefix}'

@description('Azure AI Foundry project name. It has to be unique within the selected hub.')
param aiProjectName string = 'tayra-project-${uniquePrefix}'

@description('Azure AI Foundry hub (Cognitive Services account) name. It has to be globally unique.')
param aiHubName string = 'tayra-hub-${uniquePrefix}'

@description('Name for the GPT-4 deployment inside Azure AI.')
param gptDeploymentName string = 'tayra-gpt4-${uniquePrefix}'
@description('Azure AI Speech resource name (Cognitive Services Speech).')
param speechAccountName string = 'tayra-speech-${uniquePrefix}'


@description('Model identifier to deploy (e.g., gpt-4o).')
param gptModelName string = 'gpt-4o'

@description('Model version to deploy.')
param gptModelVersion string = '2024-08-06'

@description('Manual capacity for the GPT-4 deployment.')
@minValue(1)
param gptCapacity int = 1


@description('The name of the cosmosdb container')
param containerNames array = [
  'evaluations'
  'managers'
  'rules'
  'transcriptions'
  'humanEvaluations'
]

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: resourceGroupName
  location: location
}

module cosmosdb 'modules/cosmosDB.bicep' = {
  name: 'cosmosdb-module'
  scope: rg
  params: {
    location: location
    cosmosDbAccountName: cosmosDbAccountName
    cosmosDbName: cosmosDbName
    containerNames: containerNames
  }
}

module storageAccount 'modules/storageAccount.bicep' = {
  name: 'storageaccount-module'
  scope: rg
  params: {
    location: location
    storageAccountName: storageAccountName
  }
}

module speechAccount 'modules/azureAISpeech.bicep' = {
  name: 'speechaccount-module'
  scope: rg
  params: {
    location: location
    speechAccountName: speechAccountName
  }
}

module aiProject 'modules/azureAIServices.bicep' = {
  name: 'ai-project-module'
  scope: rg
  params: {
    location: location
    aiHubName: aiHubName
    aiProjectName: aiProjectName
    gptDeploymentName: gptDeploymentName
    gptModelName: gptModelName
    gptModelVersion: gptModelVersion
    gptCapacity: gptCapacity
  }
}

output aiProjectEndpoint string = aiProject.outputs.projectEndpoint
output aiProjectId string = aiProject.outputs.projectId
output aiProjectPrincipalId string = aiProject.outputs.projectPrincipalId
output aiHubEndpoint string = aiProject.outputs.aiHubEndpoint
@secure()
output aiHubKey string = aiProject.outputs.aiHubPrimaryKey
output gpt4DeploymentName string = aiProject.outputs.gptDeploymentName
output cosmosDbEndpoint string = cosmosdb.outputs.cosmosDbEndpoint
@secure()
output storageAccountConnectionString string = storageAccount.outputs.storageAccountConnectionString
output aiSpeechEndpoint string = speechAccount.outputs.speechEndpoint
@secure()
output aiSpeechKey string = speechAccount.outputs.speechKey
