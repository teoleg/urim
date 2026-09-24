# Architecture Decision Records

Required before editing any validated model (`engine/**/validated/`). The `protect_paths` hook
allows the edit only when an ADR here contains a line `Status: Accepted` and names the exact
path being edited.

Template (`NNNN-short-title.md`):

```
# NNNN: Title
Status: Proposed | Accepted | Superseded
Date: YYYY-MM-DD
Paths: engine/instruments/<instrument>/validated/<file>.py

## Context
## Decision
## Consequences (incl. golden tests affected)
```
