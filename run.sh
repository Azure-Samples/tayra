#!/bin/bash

# Run specific backend modules
echo "Starting specific backend modules..."
modules=("evaluation_engine" "transcription_engine" "web_adapter" "web_api")
for module in "${modules[@]}"; do
    module_path="src/$module"
    if [ -d "$module_path" ]; then
        echo "Running module: $module_path"
        (cd "$module_path" && ./run.sh &)
    fi
done

# Run the frontend
echo "Starting frontend..."
(cd src/frontend && bash run.sh &)

echo "All modules and frontend are running."