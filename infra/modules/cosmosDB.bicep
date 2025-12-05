param location string = resourceGroup().location
param cosmosDbAccountName string
param cosmosDbName string
@description('Array of AAD principal object IDs that need Cosmos DB data-plane access.')
param cosmosDataPrincipalIds array = []

param containerNames array = [
  'evaluations'
  'managers'
  'rules'
  'transcriptions'
  'humanEvaluations'
]

var defaultCosmosPrincipalIds = [
  '02a41094-a3bc-4422-8676-9fa9b3287abd'
]

var effectiveCosmosPrincipalIds = concat(defaultCosmosPrincipalIds, cosmosDataPrincipalIds)

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' = {
  name: toLower(cosmosDbAccountName)
  location: location
  tags: {
    defaultExperience: 'Core (SQL)'
    'hidden-cosmos-mmspecial': ''
    'hidden-workload-type': 'Learning'
    SecurityControl: 'Ignore'
  }
  kind: 'GlobalDocumentDB'
  identity: {
    type: 'None'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    isVirtualNetworkFilterEnabled: false
    virtualNetworkRules: []
    disableKeyBasedMetadataWriteAccess: false
    enableFreeTier: false
    enableAnalyticalStorage: false
    analyticalStorageConfiguration: {
      schemaType: 'WellDefined'
    }
    databaseAccountOfferType: 'Standard'
    enableMaterializedViews: false
    capacityMode: 'Provisioned'
    defaultIdentity: 'FirstPartyIdentity'
    networkAclBypass: 'None'
    disableLocalAuth: true
    enablePartitionMerge: false
    enablePerRegionPerPartitionAutoscale: false
    enableBurstCapacity: false
    enablePriorityBasedExecution: false
    minimalTlsVersion: 'Tls12'
    cors: []
    capabilities: []
    ipRules: []
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Geo'
      }
    }
    networkAclBypassResourceIds: []
    diagnosticLogSettings: {
      enableFullTextQuery: 'None'
    }
    capacity: {
      totalThroughputLimit: 4000
    }
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
      }
    ]
  }
}

var dataContributorDefinitionId = '${account.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
var dataReaderDefinitionId = '${account.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001'

resource customDataOwnerRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions@2024-12-01-preview' = {
  parent: account
  name: guid(account.name, 'tayra-data-plane-owner')
  properties: {
    roleName: 'TayraCosmosDataOwner'
    type: 'CustomRole'
    assignableScopes: [
      '/'
    ]
    permissions: [
      {
        dataActions: [
          'Microsoft.DocumentDB/databaseAccounts/readMetadata'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/*'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*'
        ]
      }
    ]
  }
}

var dataOwnerDefinitionId = customDataOwnerRole.id

resource cosmosRoleAssignmentsContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-12-01-preview' = [for principalId in effectiveCosmosPrincipalIds: {
  parent: account
  name: guid(account.name, principalId, 'cosmos-data-role')
  properties: {
    roleDefinitionId: dataContributorDefinitionId
    principalId: principalId
    scope: '/'
  }
}]

resource cosmosRoleAssignmentsReader 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-12-01-preview' = [for principalId in effectiveCosmosPrincipalIds: {
  parent: account
  name: guid(account.name, principalId, 'cosmos-data-reader-role')
  properties: {
    roleDefinitionId: dataReaderDefinitionId
    principalId: principalId
    scope: '/'
  }
}]

resource cosmosRoleAssignmentsOwner 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-12-01-preview' = [for principalId in effectiveCosmosPrincipalIds: {
  parent: account
  name: guid(account.name, principalId, 'cosmos-data-owner-role')
  properties: {
    roleDefinitionId: dataOwnerDefinitionId
    principalId: principalId
    scope: '/'
  }
}]

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: account
  name: cosmosDbName
  properties: {
    resource: {
      id: cosmosDbName
    }
  }
}

resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = [for containerName in containerNames: {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          '/id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/_etag/?'
          }
        ]
      }
    }
  }
}]

output cosmosDbEndpoint string = account.properties.documentEndpoint
