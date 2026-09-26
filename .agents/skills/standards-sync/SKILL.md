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
3. read only the selected core `SKILL.md` files;
4. install each selected skill package locally, including its colocated `references/` files when present;
5. when tooling supports copying/materializing reference files without rendering their contents, use that path; otherwise fetch each reference once for installation but do not analyze/reread it unless the current project adaptation requires that topic;
6. record the exact upstream commit SHA in the lock file;
7. record the installed profile and skill names.

Do not scan unrelated upstream skills or eagerly load every reference.

## Single-fetch rule

Within one standards synchronization run, fetch each required upstream file at most once, including core `SKILL.md` and changed reference files.

After a successful fetch:

- reuse the returned content for analysis and local installation/update;
- keep using that same content if a local patch/write must be retried;
- do not fetch the same upstream file again merely to verify the write.

A second fetch is justified only when:

- the first fetch failed and no content was obtained; or
- the selected upstream ref/commit changed during the synchronization.

Do not spend network/tool calls proving that a successfully fetched skill still contains the same text later in the same run.

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
   - changed files inside installed skill packages, including changed `references/`;
   - newly applicable skill packages introduced by the updated profile;
7. install changed reference files locally with the least-context transfer supported by the available tooling; do not analyze/reread their contents unless their topic is required for project adaptation;
8. do not fetch unchanged installed skill files;
9. do not fetch unrelated skills;
10. preserve compatible project-specific adaptations;
11. update the lock file only after the project-local standards and required project changes are complete.

A repository compare operation or changed-file list is preferred over opening every upstream file.

If the locked commit equals the resolved upstream commit, stop the standards synchronization immediately. Do not fetch catalog/profile/skills only to reconfirm an unchanged revision.

## Profile changes

If the active profile changed:

1. read the new profile;
2. compare its required/optional skill list with the lock file;
3. fetch/install newly required skill packages, including their references;
4. update only changed files inside already installed required skill packages;
5. do not automatically enable optional skills unless they apply to the project;
6. remove a local skill only when upstream/profile changes clearly make it obsolete and project-specific rules do not still require it.

## Do not verify byte-for-byte equality

Do not require local project skills to be byte-for-byte identical to upstream.

Forbidden verification patterns include:

- refetching every skill to compare Git blob SHA values;
- `git hash-object` checks performed only to prove upstream equality;
- changing files solely to match upstream trailing newlines or insignificant whitespace;
- treating local/upstream blob mismatch as an error by itself.

The lock file records the upstream revision that was used. Project-local skills may contain compatible project-specific adaptations, so identical blob hashes are not a correctness requirement.

Validate semantic/project compatibility instead of byte identity.

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

## One authoritative upstream channel

Use one authoritative mechanism to inspect the upstream standards repository during a synchronization.

When an authenticated GitHub connector/integration is available, prefer it for:

- resolving branches/commits;
- comparing revisions;
- fetching catalog/profile/skill files.

Do not verify the same upstream state independently through web search, `git ls-remote`, and the GitHub connector unless the primary mechanism failed or produced ambiguous results.

## Efficient upstream access

Preferred:

```text
local lock
-> upstream latest commit
-> compare commits / changed paths
-> fetch changed profile/skill-package files only
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

- applicable changed/new skill packages are installed, including their reference files;
- project-specific adaptations are preserved;
- affected project implementation/configuration is aligned when required;
- the lock file points to the exact upstream commit used;
- no unrelated skills were loaded or changed.
