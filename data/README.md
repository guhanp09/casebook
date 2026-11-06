# Data dictionary and provenance

Public encode/httpx documentation at tags 0.27.2 and 0.28.1, 300 most-recently-updated issue API entries with pull requests removed, and comments from a bounded twelve-issue sample. The first snapshot has 1,365 chunks, 98 issues and 36 comments. Refreshes may change those counts. Public text remains attributed through original URLs. Documentation/source is BSD-3-Clause; models have their own upstream licenses.

| Table/file | Grain | Key fields |
| --- | --- | --- |
| sources | One chunk | id, document, title, kind, version, published, url, text |
| issues | One public issue | number, state, created, updated, closed, url |
| comments | One sampled comment | id, issue, created, url |
| issue_labels | One issue/label | number, label |
| benchmark.json | One authored query | question, version, expected_document, split, expected_status |

`published` is a conservative available date for the current body, not proof of a
historical original. Unspecified versions are excluded from exact-version search. Local
SQLite and PostgreSQL carry the same normalized schema. The JSON snapshot supplies the
retrieval index with a checked stable source ordering. Raw snapshots remain locally
regenerable and are not bundled into Git. Downstream excerpts retain source URLs.
