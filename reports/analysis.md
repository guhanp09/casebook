# Evidence-grounded support investigation

The snapshot contains 1,365 source chunks from two HTTPX documentation tags and public issue histories, with 98 sampled issues and 36 sampled comments. Source IDs, URLs, versions and available dates are preserved. Raw response checksums and source provenance are retained. Ingestion replaces the snapshot transactionally and is idempotent by stable source/issue keys; it supports SQLite locally and PostgreSQL through DATABASE_URL.

Retrieval compares keyword TF-IDF, MiniLM sentence embeddings and reciprocal-rank fusion. Version and date constraints are applied before ranking. Edited issue bodies are dated by last update, and comments are excluded from historical cutoff searches because current snapshots do not establish comment edit history. Documentation publication dates are release-tag dates.

The bounded workflow validates context, retrieves sources, applies a lexical support gate, and assembles exact source excerpts with citations. No extractive draft is presented as a confirmed diagnosis. Unsupported questions request more information. Optional local Flan-T5 drafting proposes an unverified diagnostic question and always requires human review; citations do not certify generated text.

The 78-question benchmark is developer-authored with expected source pages. Development/test wording differs but themes overlap, so this is an in-domain development benchmark, not independent human evaluation. Detailed per-query failures and timing remain in retrieval_evaluation.csv. Unsupported-question abstention rate: 100.0%. Quoted-source integrity: 100.0%. The latter checks exact provenance, not semantic entailment or troubleshooting correctness.

Operational metrics describe the most recently updated issue sample, not customer-support performance. Open issues in sample: 53; closed issues: 45. Closure is not verified resolution, labels overlap, and comment timing is not an SLA measure. Avoid projecting sample totals onto the whole repository.

Recommendation: use source-linked investigation briefs to support human troubleshooting, starting with the version-filtered TLS and upgrade examples. Review retrieval misses before widening scope. A historical query for version 0.28.1 before its release correctly returns insufficient evidence. Example transcripts are saved as structured workflow records.

The application, FastAPI endpoints, PostgreSQL Compose configuration, container definition and scheduled-ingestion workflow are included. These are local/deployable artifacts; no cloud hosting or live customer use is claimed. External inference API charge is zero because inference is local; hardware and hosting costs are unpriced.

Limitations: author-developed benchmark, two old documentation versions, partial issue/comment sampling, source editing, embedding truncation, no proven semantic entailment, no automatic external actions, and no independent user productivity study. A source may be relevant without being sufficient to diagnose the user's environment.
