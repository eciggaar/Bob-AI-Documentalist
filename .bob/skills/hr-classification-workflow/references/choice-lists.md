# HRDocument choice lists

These `HRDocument` properties are bound to a choice list. The repository rejects any value
that is not listed (error `FNRJG1017` … "not within the range of permitted values").
Values are case- and space-sensitive; use them exactly as written.

Source: `graphql/01-choice-lists.graphql` (values) and `graphql/02-property-templates.graphql` (bindings).

| Property | Allowed values |
|---|---|
| DocType | JobApplication, InterviewNotes, EmploymentContract, IDDocument, PersonalInfo, Payslip, SalaryInfo, PerformanceReview, TrainingRecord, DisciplinaryRecord, ExitDocument |
| Department | IT, Marketing, Human Resources, Sales, Finance |
| JobRole | Senior Developer, Marketing Manager, HR Specialist, Sales Representative, Financial Analyst |
| Location | Paris, France · Lyon, France · Bordeaux, France · Marseille, France · Lille, France |
| JobStatus | Active, Inactive, On Leave, Terminated |
| EmploymentType | Full Time, Part Time, Contractor, Intern, Temporary |
| CurrentStatus | Active, Pending, Suspended, Exited |
| DocumentCategory | Recruitment, Employment, Compensation, Performance, Training, Compliance, Exit |
| ClassDocType | EmployeeMaster, Identity, Compensation, Performance, Training, Disciplinary, Exit |

All other HRDocument string properties (EmployeeID, FirstName, LastName, Company, CompanyCode,
CostCenter, …) are free text.

## Mapping examples

| Text in the document | Property | Best choice | Match |
|---|---|---|---|
| "Department: Finance" | Department | Finance | Exact |
| "Exit Interview and Offboarding Notes" | DocType | ExitDocument | Mapped |
| "Permanent (CDI — Contrat à Durée Indéterminée)", 35 h/week | EmploymentType | Full Time | Mapped |
| "Disciplinary Record" | DocType | DisciplinaryRecord | Exact (normalised) |
| "Position: Data Scientist" | JobRole | — | No match → leave unset, needs manual review |
