# Transcription Engine Notes

## Listing Available Azure AI Speech Models

When you need to discover which Azure AI Speech models (for example Whisper variants) are
available in your region, you can call the models catalog endpoint. The snippet below fetches
the catalog, formats the JSON with `jq`, and saves it locally so you can inspect it or grep for
specific deployments later:

Whisper models are only exposed in certain Azure regions, so you must query the endpoint that
matches the speech resource you provisioned (for example `https://eastus.api.cognitive.microsoft.com`).
The catalog is paginated—returning at most 100 entries per call—so the script below increments the
`skip` parameter in batches of 100 to scan the full list until the page containing Whisper appears.

```bash
API=""
KEY=""

for skip in $(seq 1 100 1000); do
  echo "==> skip=$skip"
  curl -s "${API}&skip=${skip}&top=100" \
    -H "Ocp-Apim-Subscription-Key: ${KEY}" \
  | jq '.values[] | select(.displayName | test("Whisper"; "i"))'
done
```

## Using a Discovered Whisper Model

Once you've identified an available Whisper model from the catalog above, you can use it in your transcription requests. Replace the `model` field in your payload with the discovered model's endpoint:

```json
{
    "model": {
        "self": "https://eastus.api.cognitive.microsoft.com/speechtotext/v3.2/models/{model-id}"
    },
    "properties": {
        "diarizationEnabled": false,
        "wordLevelTimestampsEnabled": true,
        "punctuationMode": "DictatedAndAutomatic"
    }
}
```

**Important considerations:**

 - Whisper batch support is only enabled in select Azure regions; confirm availability in the
   Speech regional matrix before deploying:
   https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=stt.
