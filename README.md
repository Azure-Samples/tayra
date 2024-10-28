# Tayra - CallCenter Analytics GenAI App

Tayra is a sophisticated call center analytics platform designed to systematically evaluate and score call center audio interactions. By processing audio files into transcriptions and applying various evaluation models, Tayra helps organizations measure performance, compliance, and customer satisfaction in a streamlined, automated manner. The implementation uses Python-based engines, enhancing flexibility and integration with machine learning frameworks, and providing easier adaptability for custom evaluations.

## Business Scenarios Exploitable by Tayra

The Tayra platform can be adapted to a variety of business scenarios, offering significant value in several key areas:

1. Customer Experience & Sentiment Analysis
Tayra can evaluate customer sentiment during calls by analyzing the tone, choice of words, and language used by both agents and customers. This can help businesses understand customer satisfaction levels and identify common pain points. For example:
A telecom company could use Tayra to monitor customer complaints and address dissatisfaction before it escalates.
A retail call center could analyze how agents handle customer objections and suggest training areas based on sentiment analysis.

2. Agent Performance Evaluation
By comparing transcriptions against business-defined rules and training guidelines, Tayra can assess how well agents are performing in their roles. This includes measuring how effectively agents resolve customer issues, adherence to scripts, and the quality of service delivered. For example:
In a banking call center, Tayra can ensure that agents adhere to regulatory requirements for verifying customer identity during interactions.
In technical support, it can assess how efficiently agents troubleshoot and resolve issues by measuring call resolution time and satisfaction levels.

3. Compliance & Regulatory Audits
In industries with strict regulations, such as finance, healthcare, or insurance, call centers must adhere to legal requirements during customer interactions. Tayra can automatically evaluate calls for compliance with these standards, flagging any violations for further review. For example:
Financial services can use Tayra to check whether agents follow proper disclosure procedures during sales calls, ensuring they meet legal obligations.
Healthcare providers can ensure that agents correctly handle sensitive patient information and adhere to privacy laws (e.g., HIPAA).

4. Custom Use-Cases and Adaptations
The flexibility of Tayra's architecture enables businesses to adapt the system to their specific needs. For instance:
A travel agency could implement custom evaluation metrics to assess how well agents upsell vacation packages during customer calls.
Insurance companies might focus on identifying fraudulent claims by evaluating the language used by customers during initial claims discussions.

5. Multi-Language Support and Cross-Cultural Analysis
With the integration of AI-based transcription and evaluation engines, Tayra can support multiple languages, enabling global organizations to monitor call centers across different regions. It can also help businesses understand cultural differences in customer interactions and adjust their communication strategies accordingly.


## Features

This project framework provides the following features:

1. **Audio Response Units**: These software systems capture live calls from customers. The audio files are stored in Audio Data Storage (Azure Data Lake) for later processing.
2. **Web Adapter**: This service (a Python-based API) retrieves the stored audio files and forwards them to the Transcription Engine for conversion to text.
3. **Transcription Engine**: Leveraging Azure Cognitive Services, this engine transcribes the audio files into text, which are then stored in Transcription Storage (Azure Cosmos DB). Transcriptions are the foundation for all subsequent evaluations.

### Evaluation Engine

4. **Controller Engine (Python)**: This engine now runs Python scripts for evaluating transcriptions according to business rules. These scripts might incorporate logic-based scoring systems (e.g., keyword matching, rule-based classifiers) or machine learning models to assess agent performance, customer satisfaction, or specific compliance metrics.
5. **AI-driven Evaluation Engine** (OpenAI & PromptFlow)**: Leveraging state-of-the-art natural language models, these engines provide deep evaluation capabilities. They analyze the sentiment, detect compliance violations, and identify areas for improvement based on business rules.

### Context and Memory Storage

6. **Context Storage (Azure Cosmos DB)**: Holds the configuration settings, business rules, and other contextual data required for the evaluation process.
7. **Memory Storage (Azure Search)**: Stores vectorized representations of the transcriptions for fast retrieval and matching across different evaluation scenarios.
8. **Management Interface**: Built as an Azure Static Web App using NestJS and React, this interface allows business users (e.g., call center managers) to configure evaluation rules, monitor ongoing processes, and review evaluation results. The user-friendly UI facilitates rapid adjustments to evaluation parameters.
9. **Balance and Load Management**: The system leverages API Management and load balancers to handle large workloads by deploying evaluation models and managing resource usage effectively during high-traffic periods.

## Getting Started

### Prerequisites

- Windows, Linux and MacOS
- Python 3.12
- Typescript 14

### Installation

Both frontend and services are easily implemented.

- npm install [package name]
- poetry install

### Quickstart
(Add steps to get up and running quickly)

1. git clone [repository clone url]
2. cd [repository name]
3. ...


## Demo

A demo app is included to show how to use the project.

To run the demo, follow these steps:

(Add steps to start up the demo)

1.
2.
3.

## Resources

(Any additional resources or related projects)

- Link to supporting information
- Link to similar sample
- ...
