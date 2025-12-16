@description('Location for the Azure AI Speech resource')
param location string = resourceGroup().location

@description('Name of the Azure AI Speech (Cognitive Services) resource.')
param speechAccountName string


resource speechAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: speechAccountName
  location: location
  kind: 'SpeechServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    customSubDomainName: speechAccountName
    disableLocalAuth: false
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
  }
}

output speechEndpoint string = speechAccount.properties.endpoint
@secure()
output speechKey string = speechAccount.listKeys().key1
