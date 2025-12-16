# PowerShell script to set environment variables for local development based on Bicep outputs
# Usage: .\scripts\set-env.ps1

Write-Host "Getting environment variables from azd..."

# Get outputs from azd env get-values
$azdEnvValues = azd env get-values

# Parse function to extract value from azd output
function Get-AzdValue($envValues, $key) {
    $line = $envValues | Where-Object { $_ -match "^$key=" }
    if ($line) {
        return $line.Split('=', 2)[1].Trim('"')
    }
    return ""
}

# Create .env file content
$envContent = @"
# Environment variables for graphrag-indexer
# Generated from Bicep deployment outputs

# Storage
AZURE_STORAGE_CONNECTION_STRING=$(Get-AzdValue $azdEnvValues "AZURE_STORAGE_CONNECTION_STRING")

# GPT-4
GPT4_KEY=$(Get-AzdValue $azdEnvValues "GPT4_KEY")
GPT4_URL=$(Get-AzdValue $azdEnvValues "GPT4_URL")
GPT4_NAME=$(Get-AzdValue $azdEnvValues "GPT4_NAME")

# Cosmos DB
COSMOS_ENDPOINT=$(Get-AzdValue $azdEnvValues "COSMOS_ENDPOINT")
COSMOS_KEY=$(Get-AzdValue $azdEnvValues "COSMOS_KEY")
COSMOS_DB_TRANSCRIPTION=$(Get-AzdValue $azdEnvValues "COSMOS_DB_TRANSCRIPTION")
COSMOS_DB_MANAGER_RULES=$(Get-AzdValue $azdEnvValues "COSMOS_DB_MANAGER_RULES")
COSMOS_DB_EVALUATION=$(Get-AzdValue $azdEnvValues "COSMOS_DB_EVALUATION")

# Azure AI Speech
AI_SPEECH_URL=$(Get-AzdValue $azdEnvValues "AI_SPEECH_URL")
AI_SPEECH_KEY=$(Get-AzdValue $azdEnvValues "AI_SPEECH_KEY")
"@

# Write .env file
$envContent | Out-File -FilePath ".env" -Encoding UTF8

Write-Host ".env file created successfully with deployment outputs!"
Write-Host "You can now use 'docker-compose up' to test your container locally."
