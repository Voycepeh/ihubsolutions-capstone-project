# AGENTS.md

AI agents are helpers, not owners of this repository.

## Read first

1. Read `README.md`.
2. Read `CONTRIBUTING.md` before changing the project structure or collaboration workflow.
3. Review relevant files in `docs/` before making project-scope or deliverable decisions.

## Keep the project structure

Use these top-level folders:

- `data/` for local datasets
- `notebooks/` for EDA, modelling and experiments
- `src/` for reusable Python code
- `deployment/` for dashboard, application and deployment assets
- `docs/` for reports, slides, references and project documentation

Do not create new top-level folders unless a human teammate explicitly asks for one.

## Repository safety

- Do normal work on a separate branch and open a pull request.
- Do not overwrite or delete unrelated teammate work.
- Do not delete or rename the established top-level folders without approval.
- Do not rewrite Git history or force-push unless explicitly approved.
- Do not merge into `main` unless explicitly asked.
- Never commit passwords, tokens, API keys, private keys, personal data, confidential data or other secrets.
- Keep changes focused and place files in the correct existing folder.

## Data and analysis

- Treat project datasets as local-only by default.
- Keep original source data unchanged where practical.
- Do not fabricate data, results, metrics, experiments, citations or execution evidence.
- Prevent target leakage in predictive modelling.
- Do not claim code, notebooks, models or deployments were tested unless they were actually run or checked.
- Update `requirements.txt` when new Python packages are required.

## Human review

Human teammates must review and understand AI-assisted work before merge or submission. Important analytical choices and conclusions must be checked by the team.
