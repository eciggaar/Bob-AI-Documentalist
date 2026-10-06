# Python Virtual Environment Execution Rule

## Policy
All Python commands and scripts executed in Agent mode MUST run within a Python virtual environment.

## Requirements
- Always use the Python interpreter located inside the project virtual environment at `.venv/bin/python`, or activate it prior to execution: `source .venv/bin/activate && python ...`.
- If no virtual environment exists in the workspace, create one using `python3 -m venv .venv` and install required dependencies (e.g., `pip install -r requirements.txt`) before running scripts.
- Never execute Python scripts using global or system Python directly without an active virtual environment.
