#!/bin/bash
# Generate a Tayra .env file from azd environment values
# Usage: ./infra/scripts/set-env.sh

set -euo pipefail

AZD_VALUES=$(azd env get-values)

get_value() {
	local key="$1"
	local line
	line=$(echo "$AZD_VALUES" | grep -E "^${key}=") || true
	if [ -z "$line" ]; then
		echo "";
		return
	fi
	echo "$line" | cut -d'=' -f2- | tr -d '"'
}

AZURE_STORAGE_CONNECTION_STRING=$(get_value AZURE_STORAGE_CONNECTION_STRING)
GPT4_KEY=$(get_value GPT4_KEY)
GPT4_URL=$(get_value GPT4_URL)
GPT4_NAME=$(get_value GPT4_NAME)
COSMOS_ENDPOINT=$(get_value COSMOS_ENDPOINT)
COSMOS_KEY=$(get_value COSMOS_KEY)
COSMOS_DB_TRANSCRIPTION=$(get_value COSMOS_DB_TRANSCRIPTION)
COSMOS_DB_MANAGER_RULES=$(get_value COSMOS_DB_MANAGER_RULES)
COSMOS_DB_EVALUATION=$(get_value COSMOS_DB_EVALUATION)
AI_SPEECH_URL=$(get_value AI_SPEECH_URL)
AI_SPEECH_KEY=$(get_value AI_SPEECH_KEY)

cat > .env <<EOF
# Tayra runtime environment
# Generated via infra/scripts/set-env.sh from azd environment values

AZURE_STORAGE_CONNECTION_STRING='${AZURE_STORAGE_CONNECTION_STRING}'

GPT4_KEY='${GPT4_KEY}'
GPT4_URL='${GPT4_URL}'
GPT4_NAME='${GPT4_NAME}'

COSMOS_ENDPOINT='${COSMOS_ENDPOINT}'
COSMOS_KEY='${COSMOS_KEY}'
COSMOS_DB_TRANSCRIPTION='${COSMOS_DB_TRANSCRIPTION}'
COSMOS_DB_MANAGER_RULES='${COSMOS_DB_MANAGER_RULES}'
COSMOS_DB_EVALUATION='${COSMOS_DB_EVALUATION}'

AI_SPEECH_URL='${AI_SPEECH_URL}'
AI_SPEECH_KEY='${AI_SPEECH_KEY}'
EOF

echo ".env file created successfully."