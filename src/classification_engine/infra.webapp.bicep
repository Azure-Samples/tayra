targetScope = 'resourceGroup'

@description('Azure region for every resource in this deployment.')
param location string = resourceGroup().location

@description('Globally unique storage account name for audio data.')
param storageAccountName string = 'tayrastge2sm'

@description('App Service plan name that powers the API, adapter, and ingestion function.')
param appServicePlanName string = 'tayra-appserviceplan'

@description('Azure Functions app name for ingestion skillset.')
param ingestionFunctionName string = 'tayra-ingestion-func'

@description('Web App name for the API surface.')
param webApiName string = 'tayra-webapi'

@description('Web App name for the adapter surface.')
param webAdapterName string = 'tayra-webadapter'

@description('API Management instance name used to balance evaluation requests.')
param apiManagementName string = 'tayraapimanager'

@description('Service Bus namespace name for orchestrator messaging.')
param serviceBusNamespaceName string = 'tayraservicebus'

@description('Queue name inside Service Bus for orchestrator jobs.')
param orchestratorQueueName string = 'orchestratorQueue'

@description('SKU for the App Service plan.')
@allowed([ 'B1', 'P1v2', 'P2v2' ])
param appServiceSku string = 'P1v2'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

var storagePrimaryKey = storageAccount.listKeys().keys[0].value
var storageConnectionString = format('DefaultEndpointsProtocol=https;AccountName={0};AccountKey={1};EndpointSuffix=core.windows.net', storageAccount.name, storagePrimaryKey)

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: appServiceSku
    capacity: 1
  }
  properties: {
    reserved: false
    targetWorkerCount: 0
    targetWorkerSizeId: 0
  }
}

resource ingestionFunction 'Microsoft.Web/sites@2023-12-01' = {
  name: ingestionFunctionName
  location: location
  kind: 'functionapp'
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'node'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AzureWebJobsStorage'
          value: storageConnectionString
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '14.17.0'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: ''
        }
      ]
    }
  }
}

resource webApi 'Microsoft.Web/sites@2023-12-01' = {
  name: webApiName
  location: location
  kind: 'app'
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      appSettings: [
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '14.17.0'
        }
      ]
    }
  }
}

resource webAdapter 'Microsoft.Web/sites@2023-12-01' = {
  name: webAdapterName
  location: location
  kind: 'app'
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      appSettings: [
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '14.17.0'
        }
      ]
    }
  }
}

resource apiManagement 'Microsoft.ApiManagement/service@2022-08-01' = {
  name: apiManagementName
  location: location
  sku: {
    name: 'Developer'
    capacity: 1
  }
  properties: {
    publisherEmail: 'tayra-admin@example.com'
    publisherName: 'Tayra'
  }
}

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: serviceBusNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
}

resource orchestratorQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: orchestratorQueueName
  properties: {
    maxSizeInMegabytes: 5120
    defaultMessageTimeToLive: 'P14D'
    requiresDuplicateDetection: false
    requiresSession: false
  }
}

output storageEndpoint string = storageAccount.properties.primaryEndpoints.blob
output functionHostName string = ingestionFunction.properties.defaultHostName
output webApiEndpoint string = webApi.properties.defaultHostName
output webAdapterEndpoint string = webAdapter.properties.defaultHostName
output apiManagementHostname string = apiManagement.properties.hostnameConfigurations[0].hostName
output serviceBusNamespaceConnection string = format('Endpoint=sb://{0}.servicebus.windows.net/;', serviceBusNamespace.name)
