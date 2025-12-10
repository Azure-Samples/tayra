#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $projectRoot

$envScript = Join-Path $projectRoot "..\..\infra\scripts\set-env.ps1"
if (Test-Path $envScript) {
    Write-Host "Loading environment variables from infra/scripts/set-env.ps1"
    . $envScript
}

uvicorn classification_engine.app.main:app --host 0.0.0.0 --port 8000 --reload
