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

@description('The name of the resource group to create')
param resourceGroupName string = 'rg-tayra-callcenter-poc'

@description('cosmosdb account name. It has to be unique.Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param cosmosDbAccountName string = 'tayracosmosdb-poc-${uniqueString(resourceGroupName)}'

@description('cosmosdb database name. It has to be unique.Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param cosmosDbName string = 'tayradbpoc'

@description('That name is the name of our application. It has to be unique.Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param storageAccountName string = 'tayrastgpoc${uniqueString(resourceGroupName)}'

@description('That name is the name of our application. It has to be unique.Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param aiServicesName string = 'aiservices-poc-${uniqueString(resourceGroupName)}'

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

module aiServices 'modules/azureAIServices.bicep' = {
  name: aiServicesName
  scope: rg
  params: {
    location: location
    sku: 'S0'
    aiServicesName: aiServicesName
  }
}

output aiServiceEndpoint string = aiServices.outputs.aiServiceEndpoint
output aiServiceVersion string = aiServices.outputs.aiServiceVersion
output cosmosDbEndpoint string = cosmosdb.outputs.cosmosDbEndpoint
output storageAccountConnectionString string = storageAccount.outputs.storageAccountConnectionString
