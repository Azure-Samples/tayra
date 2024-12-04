#!/usr/bin/env pwsh

# Run specific backend modules
Write-Output "Starting specific backend modules..."
$modules = @("evaluation_engine", "transcription_engine", "web_adapter", "web_api")
foreach ($module in $modules) {
    $module_path = "src/$module"
    if (Test-Path $module_path) {
        Write-Output "Running module: $module_path"
        Start-Process pwsh -ArgumentList "-NoProfile", "-Command", "cd $module_path; ./run.ps1" -NoNewWindow
    }
}

# Run the frontend
Write-Output "Starting frontend..."
Start-Process pwsh -ArgumentList "-NoProfile", "-Command", "cd src/frontend; ./run.ps1" -NoNewWindow

Write-Output "All modules and frontend are running."