# iHub Solutions Capstone Project

Repository for the iHub Solutions capstone project.

## Project overview

This repository keeps the team's analysis, modelling, reusable code, documentation and deployment work in one consistent structure. It follows the same simple project layout used in the team's IT5006 repository so contributors know where work belongs.

## Repository structure

```text
project-root/
├── data/
│   └── raw/
├── notebooks/
├── src/
├── deployment/
├── docs/
├── .github/
├── CONTRIBUTING.md
├── AGENTS.md
├── requirements.txt
└── README.md
```

- `data/` contains the local project data structure. Project datasets themselves are not committed to GitHub.
- `notebooks/` contains exploratory analysis, modelling and experiments.
- `src/` contains reusable Python code where needed.
- `deployment/` contains dashboard, application and deployment assets.
- `docs/` contains reports, presentation materials, references and project documentation.

## Data policy

Project data stays local unless the team explicitly agrees that a file is safe and appropriate to commit. The repository `.gitignore` excludes everything under `data/` except the README instruction files.

Never commit passwords, tokens, API keys, confidential information or other secrets.

## Environment

Project dependencies are recorded in [`requirements.txt`](requirements.txt) and should be updated as the project develops.

## Team contribution guide

Local setup and collaboration guidance are kept separately in [`CONTRIBUTING.md`](CONTRIBUTING.md).
