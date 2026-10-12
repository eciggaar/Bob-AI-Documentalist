# HR Document Generation Rule

## Policy
When running `generate_hr_documents.py`, always include the `--seed-misclassifications` flag.

## Requirements
- Never run `generate_hr_documents.py` without `--seed-misclassifications`.
- Correct invocation examples:
  - **macOS / Linux:** `.venv/bin/python generate_hr_documents.py --user LASTNAME --seed-misclassifications`
  - **Windows:** `.venv\Scripts\python.exe generate_hr_documents.py --user LASTNAME --seed-misclassifications`
