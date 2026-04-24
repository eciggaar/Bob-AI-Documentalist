# AI Documentalist

An AI-powered document management and classification system for HR documents using IBM FileNet Content Manager.

## Project Overview

This project demonstrates how to use AI (Bob) to manage, classify, and organize HR documents in a content repository. It includes automated document generation, classification, and repository management capabilities.

## Features

- **Automated HR Document Generation**: Generate sample HR documents for testing
- **Document Classification**: Automatically classify documents using the HRDocument class
- **Repository Management**: Organize documents in a structured folder hierarchy
- **Metadata Management**: Properly tag documents with employee information, department, job role, etc.

## Project Structure

```
AIDocumentalist/
├── Lab1_Bob_as_Documentalist.md    # Introduction to Bob as a documentalist
├── Lab2_Generate_Sample_Content.md # Guide for generating sample HR documents
├── Lab3_Review_and_Reclassify.md   # Document review and reclassification guide
├── generate_hr_documents.py         # Python script to generate HR documents
├── Reference/                       # Reference documentation and images
│   ├── Classification_and_Cleaning_Plan.md
│   ├── Document_Class_Architecture.md
│   └── Document_Property_Specifications.md
└── Completed Lab/                   # Completed lab exercises

```

## HR Document Categories

The system manages documents across 8 categories:
1. **Recruitment** - Job applications, interview notes
2. **Employment Contract** - Employment agreements
3. **Personal Administration** - Personal info, ID documents
4. **Payroll** - Salary information, payslips
5. **Performance** - Performance reviews
6. **Training** - Training records and certifications
7. **Disciplinary** - Disciplinary records
8. **Exit** - Exit interviews and offboarding notes

## Getting Started

### Prerequisites

- IBM FileNet Content Manager access
- Python 3.x (for document generation)
- Bob AI assistant with MCP server configuration

### Setup

1. Clone this repository
2. Configure your MCP server settings in `.bob/mcp.json`
3. Follow the lab guides in sequence (Lab1 → Lab2 → Lab3)

## Usage

### Generating Sample HR Documents

```bash
python generate_hr_documents.py
```

### Repository Structure

Documents are organized in the repository under:
```
/BOB_LAB/DUPONT/[EmployeeID_Name]/[Category]/[Documents]
```

Example:
```
/BOB_LAB/DUPONT/JAB001_Jade Robin/
├── 01_Recruitment/
├── 02_Employment_Contract/
├── 03_Personal_Administration/
├── 04_Payroll/
├── 05_Performance/
├── 06_Training/
├── 07_Disciplinary/
└── 08_Exit/
```

## Document Metadata

Each HR document includes standardized metadata:
- Employee ID
- First Name / Last Name
- Document Type
- Department
- Job Role
- Company / Company Code
- Cost Center
- Location
- Start Date

## Labs

- **Lab 1**: Introduction to Bob as a Documentalist
- **Lab 2**: Generate Sample HR Content
- **Lab 3**: Review and Reclassify Documents

## Contributing

This is a demonstration project for learning purposes.

## License

[Specify your license here]

## Contact

[Your contact information]