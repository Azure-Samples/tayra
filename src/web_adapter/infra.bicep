// Create the resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-tayra-app'
  location: 'EastUS'
}

// Create an Azure Storage Account for Audio Data Storage
resource storageAccount 'Microsoft.Storage/storageAccounts@2021-09-01' = {
  name: 'tayraaudiodatastore'
  location: rg.location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

// Create an Azure Function for Ingestion Skillset
resource ingestionFunction 'Microsoft.Web/sites@2021-02-01' = {
  name: 'tayra-ingestion-func'
  location: rg.location
  kind: 'functionapp'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'node'
        }
        {
          name: 'AzureWebJobsStorage'
          value: storageAccount.properties.primaryEndpoints.blob
        }
      ]
    }
  }
  dependsOn: [
    appServicePlan
    storageAccount
  ]
}

// Create an App Service Plan for Web API and Web Adapter
resource appServicePlan 'Microsoft.Web/serverfarms@2021-02-01' = {
  name: 'tayra-appserviceplan'
  location: rg.location
  sku: {
    name: 'P1v2'
    capacity: 1
  }
}

// Create a Web App for the Web API
resource webApi 'Microsoft.Web/sites@2021-02-01' = {
  name: 'tayra-webapi'
  location: rg.location
  kind: 'app'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '14.17.0'
        }
      ]
    }
  }
  dependsOn: [appServicePlan]
}

// Create a Web App for the Web Adapter
resource webAdapter 'Microsoft.Web/sites@2021-02-01' = {
  name: 'tayra-webadapter'
  location: rg.location
  kind: 'app'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '14.17.0'
        }
      ]
    }
  }
  dependsOn: [appServicePlan]
}

// Create Cosmos DB for both Context and Transcription Storage
resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2021-04-15' = {
  name: 'tayracosmosdb'
  location: rg.location
  kind: 'MongoDB'
  properties: {
    locations: [
      {
        locationName: rg.location
      }
    ]
  }
}

// Create Cosmos DB Databases and Containers
resource contextDatabase 'Microsoft.DocumentDB/databaseAccounts/databases@2021-04-15' = {
  name: '${cosmosDbAccount.name}/tayraContextDb'
  properties: {}
  dependsOn: [
    cosmosDbAccount
  ]
}

resource transcriptionDatabase 'Microsoft.DocumentDB/databaseAccounts/databases@2021-04-15' = {
  name: '${cosmosDbAccount.name}/tayraTranscriptionDb'
  properties: {}
  dependsOn: [
    cosmosDbAccount
  ]
}

// Create Azure Search for Memory Storage
resource searchService 'Microsoft.Search/searchServices@2020-08-01' = {
  name: 'tayrasearchservice'
  location: rg.location
  sku: {
    name: 'basic'
  }
}

// Create Azure Cognitive Services for Transcription Engine (Speech to Text)
resource cognitiveServices 'Microsoft.CognitiveServices/accounts@2017-04-18' = {
  name: 'tayracognitive'
  location: rg.location
  kind: 'CognitiveServices'
  sku: {
    name: 'S1'
    tier: 'Standard'
  }
  properties: {
    apiProperties: {
      cognitiveservices: 'Speech'
    }
  }
}

// Create Azure AI for Evaluation Engine (OpenAI + PromptFlow)
resource openAiService 'Microsoft.CognitiveServices/accounts@2017-04-18' = {
  name: 'tayraopenaiengine'
  location: rg.location
  kind: 'OpenAI'
  sku: {
    name: 'S1'
  }
  dependsOn: [
    cognitiveServices
  ]
}

// Create Azure API Management for Balancing Evaluation Requests
resource apiManagement 'Microsoft.ApiManagement/service@2021-08-01' = {
  name: 'tayraapimanager'
  location: rg.location
  sku: {
    name: 'Developer'
    capacity: 1
  }
}

// Create Azure Service Bus for Orchestrator
resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2021-01-01-preview' = {
  name: 'tayraservicebus'
  location: rg.location
  sku: {
    name: 'Standard'
  }
}

resource orchestratorQueue 'Microsoft.ServiceBus/namespaces/queues@2021-01-01-preview' = {
  name: '${serviceBusNamespace.name}/orchestratorQueue'
  properties: {
    maxSizeInMegabytes: 5120
    defaultMessageTimeToLive: 'P14D'
  }
  dependsOn: [
    serviceBusNamespace
  ]
}

output storageEndpoint string = storageAccount.properties.primaryEndpoints.blob
output webApiEndpoint string = webApi.properties.defaultHostName
output webAdapterEndpoint string = webAdapter.properties.defaultHostName
output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint
output cognitiveServicesEndpoint string = cognitiveServices.properties.endpoint
