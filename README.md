# Tayra - Call Center Analytics GenAI App

<img src="images/tayra-logo.jpg" alt="Tayra Logo" width="30%">

Tayra is an advanced call center analytics platform that evaluates and scores call center audio interactions. By converting audio files into transcriptions and applying various evaluation models, Tayra helps organizations measure performance, compliance, and customer satisfaction efficiently. It uses Python-based engines for flexibility and integration with machine learning frameworks, making it adaptable for custom evaluations.

## Business Scenarios for Tayra

Tayra can be tailored to various business scenarios, providing value in key areas:

1. **Customer Experience & Sentiment Analysis**
    - Tayra analyzes customer sentiment during calls by examining tone, word choice, and language. This helps businesses gauge customer satisfaction and identify pain points.
      - *Example 1*: A telecom company can monitor customer complaints and address issues before they escalate.
      - *Example 2*: A retail call center can analyze agent handling of objections and suggest training based on sentiment analysis.

2. **Agent Performance Evaluation**
    - Tayra compares transcriptions against business rules and training guidelines to assess agent performance, including issue resolution, script adherence, and service quality.
      - *Example 1*: In a banking call center, Tayra ensures agents follow regulatory requirements for customer identity verification.
      - *Example 2*: In technical support, it measures call resolution time and satisfaction levels to evaluate troubleshooting efficiency.

3. **Compliance & Regulatory Audits**
    - Tayra evaluates calls for compliance with industry regulations, flagging violations for review.
      - *Example 1*: Financial services can check if agents follow proper disclosure procedures during sales calls.
      - *Example 2*: Healthcare providers can ensure agents handle patient information correctly and comply with privacy laws (e.g., HIPAA).

4. **Custom Use-Cases and Adaptations**
    - Tayra's flexible architecture allows businesses to customize the system for specific needs.
      - *Example 1*: A travel agency can assess how well agents upsell vacation packages.
      - *Example 2*: Insurance companies can identify fraudulent claims by evaluating customer language during claims discussions.

5. **Multi-Language Support and Cross-Cultural Analysis**
    - Tayra supports multiple languages, enabling global organizations to monitor call centers across regions. It helps businesses understand cultural differences in customer interactions and adjust communication strategies.

## Architecture

<img src="images/Tayra-CallCenterAnalytics-C4.png" alt="Tayra Architecture" width="100%">

## Features

Tayra offers the following features:

1. **Call Center Software Integration**: Capture live calls and store audio files in Azure Data Lake for processing.
2. **Web Adapter**: A Python-based API that retrieves audio files and forwards them to the Transcription Engine.
3. **Transcription Engine**: Uses Azure Cognitive Services to transcribe audio files into text, stored in Azure Cosmos DB.

### Evaluation Engine

4. **Orchestrator**: Runs Python scripts to evaluate transcriptions based on business rules, using logic-based scoring or machine learning models.
5. **AI-driven Evaluation Engine** (Azure OpenAI & PromptFlow): Uses large language models to analyze sentiment, detect compliance violations, and identify improvement areas.

### Context and Memory Storage

6. **Context Storage (Azure Cosmos DB)**: Stores configuration settings, business rules, and contextual data for evaluations.
7. **Memory Storage (Azure AI Search)**: Stores vectorized represenations of transcriptions for fast retrieval and matching.
8. **Management Interface**: An Azure Static Web App using NestJS and React, allowing users to configure rules, monitor processes, and review results.
9. **Balancer and API Management**: Uses Azure API Management and load balancers to handle large workloads and manage resources during high-traffic periods.

## Getting Started

### Prerequisites

- Windows, Linux and MacOS
- Python 3.12
- Typescript 14
- [Az CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux?pivots=apt)
- [npm 8.5.1](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
- [Poetry 1.8.4 or greater](https://python-poetry.org/docs/#installing-with-the-official-installer)
- [Yarn 1.22 or greater](https://classic.yarnpkg.com/lang/en/docs/install/#windows-stable)
- [NVM 0.40.1 or greater](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating)


### Installation

Install dependencies for backend and frontend

- `npm install frontend`
- `poetry install`
- `yarn install`

* In some case you may need to use the NodeJS version 18:

- `nvm install 18` and `nvm use 18`

### Quickstart

1. `git clone https://github.com/Azure-Samples/tayra.git`
2. `bash run.sh` (for Linux users) or `run.ps1` (for Windows users)

The run script with run four microservices (Evaluation, Transcription, Web Adapter and Web APIs) as well as the frontend application.



## Demo

A demo app is included to show how to use the project.

To run the demo, follow these steps:

1.
2.
3.

## CosmosDB EntraID permissions
We use the [CosmosDB native RBAC](https://aka.ms/cosmos-native-rbac) to authenticate with the application. Follow the instructions below to give the permission to the user/service-principal:

1. `az login`
2. Add the CosmosDB SQL Data Contributor assigment:

```bash
resourceGroupName='<myResourceGroup>'
accountName='<myCosmosAccount>'
readOnlyRoleDefinitionId='00000000-0000-0000-0000-000000000001' 

# For Service Principals make sure to use the Object ID as found in the Enterprise applications section of the Azure Active Directory portal blade.
principalId='<aadPrincipalId>'

az cosmosdb sql role assignment create --account-name $accountName --resource-group $resourceGroupName --scope "/" --principal-id $principalId --role-definition-id $readOnlyRoleDefinitionId 
```

## Resources

- [Azure OpenAI Service](https://azure.microsoft.com/en-us/services/openai-service/)
- [Azure Speech Services](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/overview)
- [Azure Cosmos DB](https://azure.microsoft.com/en-us/services/cosmos-db/)
- [Azure Storage Account](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview)

## TO-DO
- Prepare sample audio data
- Prepare the demo step-by-step guidance
- Add PowerBI dashboard template with analytics
- Add language selection option
- Add transcription service options (currently only Fast Transcription API is used)