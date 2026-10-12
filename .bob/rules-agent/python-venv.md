# Python Virtual Environment Execution Rule

## Policy
All Python commands and scripts executed in Agent mode MUST run within a Python virtual environment across all supported platforms (macOS, Linux, and Windows).

## Requirements
- Always use the Python interpreter located inside the project virtual environment:
  - **macOS / Linux:** `.venv/bin/python` (or activate via `source .venv/bin/activate && python ...`)
  - **Windows:** `.venv\Scripts\python.exe` (or activate via `.venv\Scripts\activate && python ...`)
- If no virtual environment exists in the workspace, create one and install dependencies:
  - **macOS / Linux:** `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (or `.venv/bin/pip install requests`)
  - **Windows:** `python -m venv .venv && .venv\Scripts\pip.exe install -r requirements.txt` (or `.venv\Scripts\pip.exe install requests`)
- If using `uv`: `uv venv && uv pip install -r requirements.txt`
- Never execute Python scripts using global or system Python directly without an active virtual environment.
