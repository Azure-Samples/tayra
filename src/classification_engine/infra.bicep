// Deploys the Tayra classification engine container on Azure Container Apps.

@description('Name prefix applied to all generated resources.')
param namePrefix string = 'tayra-classification'

@description('Azure region for the deployment.')
param location string = resourceGroup().location

@description('Fully qualified container image reference, e.g. myregistry.azurecr.io/classification:latest.')
param containerImage string

@description('Target port exposed by the FastAPI service.')
param containerPort int = 8000

@description('Minimum number of container replicas.')
@minValue(0)
param minReplicas int = 1

@description('Maximum number of container replicas.')
@minValue(1)
param maxReplicas int = 2

@description('vCPU requested per replica (stringified number, e.g. 0.5, 1.0).')
param cpu string = '0.5'

@description('Memory requested per replica (Gi).')
param memory string = '1Gi'

@description('Container registry login server, e.g. myregistry.azurecr.io.')
param registryServer string

@description('Container registry username with pull permissions.')
param registryUsername string

@secure()
@description('Container registry password or access token.')
param registryPassword string

@description('Cosmos DB endpoint used by the API layer.')
param cosmosEndpoint string

@description('Cosmos DB database name that stores transcription documents.')
param cosmosDatabase string = 'tayradb'

@description('Cosmos DB container holding transcription documents.')
param transcriptionsContainer string = 'transcriptions'

@description('Cosmos DB container holding classification documents.')
param classificationsContainer string = 'classifications'

@description('Whether the container should use managed identity based Cosmos authentication.')
param useAadAuth bool = true

var analyticsWorkspaceName = '${namePrefix}-law'
var managedEnvironmentName = '${namePrefix}-env'
var containerAppName = '${namePrefix}-app'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: analyticsWorkspaceName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

var logAnalyticsKeys = logAnalytics.listKeys()

resource managedEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: managedEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalyticsKeys.primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'auto'
      }
      secrets: [
        {
          name: 'registry-password'
          value: registryPassword
        }
      ]
      registries: [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'classification-engine'
          image: containerImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmosEndpoint
            }
            {
              name: 'COSMOS_DB_TRANSCRIPTION'
              value: cosmosDatabase
            }
            {
              name: 'CONTAINER_NAME'
              value: transcriptionsContainer
            }
            {
              name: 'COSMOS_CLASSIFICATION_CONTAINER'
              value: classificationsContainer
            }
            {
              name: 'COSMOS_USE_AAD'
              value: string(useAadAuth)
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output logAnalyticsResourceId string = logAnalytics.id
output containerAppPrincipalId string = containerApp.identity.principalId
