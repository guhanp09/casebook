# Engineering notes

Source ingestion stores stable chunk IDs, source URLs, documentation tags and conservative
availability dates. SQLite is the local default; PostgreSQL uses the same normalized tables.
Repeated ingestion is checked for stable unique record counts.

The retrieval index checks source ordering before use. Version and date filters run before
ranking. TF-IDF, sentence embeddings and reciprocal-rank fusion are compared on the same
in-domain benchmark. Extractive investigation briefs quote source text; optional generated
diagnostic questions are separately marked for review.

Validation covers historical cutoffs, version filtering, unsupported questions, exact source
excerpts, HTTP request validation and PostgreSQL ingestion. Benchmark design and applicability
limits are documented in methodology.md; measured results are in reports/metrics.json.

Tested dependency versions are recorded in constraints.txt and environment.json.
