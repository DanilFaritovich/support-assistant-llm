---
name: standards-sync
description: Efficiently synchronize project-local Codex development standards with this upstream repository without rereading every installed skill. Use when installing, updating, or auditing standards in an existing project.
---

# Standards Sync

Use the standards repository as an installation/update source, not as context that must be fully reread on every task.

## Lock file

Projects using these standards should keep:

`.codex-standards.lock.yaml`

This file records the upstream state used for the current local standards installation.

Recommended shape:

```yaml
version: 1

source:
  repository: https://github.com/DanilFaritovich/codex-development-standards
  ref: <upstream-commit-sha>

profile:
  name: fastapi-vue-clean
  version: 5

skills:
  - task-development-workflow
  - standards-sync
  - code-quality
  - ...

optional_skills:
  - continuous-delivery
```

The lock file contains no secrets.

Commit it to the target repository.

## Initial installation

For the first installation:

1. read `catalog.yaml`;
2. select the applicable profile or individual skills;
3. read only those selected skills;
4. install/adapt them locally;
5. record the exact upstream commit SHA in the lock file;
6. record the installed profile and skill names.

Do not scan every upstream skill.

## Update workflow

When a lock file already exists:

1. read the local lock file first;
2. resolve the current upstream target ref/commit;
3. if the upstream commit equals the locked `source.ref`, stop: standards are already current;
4. compare the locked upstream commit with the new upstream commit;
5. inspect the changed-file list before fetching skill contents;
6. fetch only:
   - `catalog.yaml` when it changed;
   - the active profile when it changed;
   - installed skill files that changed;
   - newly applicable skill files introduced by the updated profile;
7. do not fetch unchanged installed skills;
8. do not fetch unrelated skills;
9. preserve compatible project-specific adaptations;
10. update the lock file only after the project-local standards and required project changes are complete.

A repository compare operation or changed-file list is preferred over opening every upstream file.

## Profile changes

If the active profile changed:

1. read the new profile;
2. compare its required/optional skill list with the lock file;
3. fetch newly required skills;
4. update changed required skills;
5. do not automatically enable optional skills unless they apply to the project;
6. remove a local skill only when upstream/profile changes clearly make it obsolete and project-specific rules do not still require it.

## Local adaptations

Project-local standards may differ from upstream where the project requires it.

Do not blindly overwrite local changes.

For each changed upstream skill:

- identify meaningful upstream changes;
- merge them into the local project version;
- preserve compatible project-specific rules;
- report conflicts that require a project decision.

Avoid reproducing unchanged upstream text merely to prove that it was checked.

## Project implementation changes

After synchronizing changed standards, inspect only the project areas affected by those changed rules.

Do not perform a full repository audit merely because the upstream standards commit changed.

Example:

```text
upstream change: code-quality only
-> inspect Makefiles / lint / format / typecheck workflow
-> do not reread persistence, Docker, Vue architecture, etc.
```

If several changed skills affect architecture/infrastructure, widen the audit only to those affected areas.

## Efficient upstream access

Preferred:

```text
local lock
-> upstream latest commit
-> compare commits / changed paths
-> fetch changed profile/skills only
```

Avoid:

```text
catalog
-> profile
-> fetch every skill
-> discover most files were unchanged
```

## Completion

A standards sync is complete when:

- applicable changed/new skills are installed;
- project-specific adaptations are preserved;
- affected project implementation/configuration is aligned when required;
- the lock file points to the exact upstream commit used;
- no unrelated skills were loaded or changed.
