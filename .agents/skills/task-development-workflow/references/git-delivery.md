# Git, Documentation, and Delivery Reference

Read this reference when starting/continuing a task branch, preparing documentation, committing, pushing, or creating a Pull Request.

## Branch setup

Use the repository's configured development branch, normally `develop`.

Before editing:

1. check current branch;
2. check working tree;
3. preserve unrelated user changes and untracked files;
4. create or continue a dedicated task branch.

Typical prefixes:

- `feature/`;
- `fix/`;
- `refactor/`;
- `chore/`;
- `docs/`.

Do not perform normal task development directly in `develop` or `main`.

## Documentation timing

Update affected documentation only after implementation and required validation are stable.

Potential files include:

- `AGENTS.md`;
- `ARCHITECTURE.md`;
- root/component READMEs;
- API docs;
- code docstrings.

Do not continuously rewrite documentation while implementation is changing.

## Commit and push

Stage only files belonging to the task.

Never include:

- secrets;
- local environment files;
- unrelated untracked files;
- accidental generated artifacts.

Create a clear commit and push only the task branch.

## Pull Request and CI

Normal flow:

```text
task branch -> develop
```

GitHub Actions performs the full independent CI validation.

If CI fails:

1. inspect only the relevant failure;
2. reproduce it locally with the smallest practical command when possible;
3. make a targeted fix;
4. run targeted validation;
5. run the affected fast aggregate check if necessary;
6. push and let CI rerun.

Do not ingest unrelated successful CI logs.

## Merge boundary

Codex must not automatically merge the Pull Request.

Responsibility:

```text
Codex:
analyze -> implement -> validate -> document -> commit -> push -> PR -> CI

Developer:
review -> merge
```

Merge only when the user explicitly requests that separate action.

## Completion report

Keep the final report concise.

Include:

- what changed;
- tests/checks performed;
- whether extended verification was needed;
- documentation changes;
- branch/commit;
- push/PR/CI status;
- remaining limitations.

Do not include long successful logs or a chronological list of tool calls.
