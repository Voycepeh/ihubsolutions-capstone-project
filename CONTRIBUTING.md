# Contributing

This is a data and analytics capstone project, so keep the workflow simple.

## First-time setup

1. Open your IDE, for example VS Code.
2. Clone this repository:

```bash
git clone https://github.com/Voycepeh/ihubsolutions-capstone-project.git
```

3. Open the cloned repository in your IDE.
4. Place project datasets in the appropriate folder under:

```text
data/raw/
```

Project data is for local use and is ignored by Git.

## Where work goes

| Work | Folder |
| --- | --- |
| Raw and local datasets | `data/` |
| EDA, modelling and analysis notebooks | `notebooks/` |
| Reusable Python scripts | `src/` |
| Dashboard, app and deployment files | `deployment/` |
| Reports, slides, references and project documents | `docs/` |

For most analysis work, use `notebooks/` and read local files from `data/raw/`.

## What to upload

Upload project work such as notebooks, Python scripts, reports, documentation and deployment files.

**Do not upload or commit project data by default.**

Everything under `data/` stays on your computer unless the team explicitly agrees otherwise. Only README instruction files inside `data/` are tracked.

Before committing, check that no dataset, credential, token, API key, personal information or confidential material is included.

## Working with the team

Use your own branch where practical and submit changes through a pull request. Do not overwrite or delete another teammate's work without agreement.

Keep each change focused on the task you are working on.

## AI-assisted work

AI tools may assist the project, but team members remain responsible for reviewing, understanding and validating AI-assisted work before it is used or submitted.

AI agents must follow [`AGENTS.md`](AGENTS.md).
