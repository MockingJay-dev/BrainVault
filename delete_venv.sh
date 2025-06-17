#!/bin/bash
# Remove the Python virtual environment if it exists
if [ -d .venv ]; then
  rm -rf .venv
  echo "Virtual environment removed."
else
  echo "No virtual environment found."
fi
