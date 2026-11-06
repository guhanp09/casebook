# Casebook methodology

The corpus preserves source URL, tag, kind, document ID and available date per chunk. An issue body is dated by its last update, not its creation, because edited text cannot safely be treated as originally available. Comments are excluded from historical searches because their edit history is not reconstructed. Documentation dates use release dates. Exact-version retrieval is deliberately conservative; unspecified issue versions do not enter a version-specific search.

Keyword ranking uses sublinear TF-IDF with unigrams and bigrams. Dense ranking uses normalized all-MiniLM-L6-v2 embeddings and dot products. Hybrid ranking sums 1/(60 + rank) across both lists after eligibility filtering. Long chunks can be truncated by the embedding model; keywords still index their full text.

Evidence requires keyword cosine at least 0.045 and at least two overlapping non-generic terms. This is an explicit heuristic, not a semantic entailment guarantee. Extractive drafts reproduce contiguous source text. Optional generated diagnostic questions are unverified and separated from quoted evidence. Source content is treated as untrusted input, never executable instructions.

The author-developed benchmark contains 24 themes with three phrasings each plus six unrelated questions. One phrasing per theme is development; two are test. Themes overlap across splits. Expected answers are source pages, not independently verified resolutions. Recall@5 and MRR measure page retrieval. Quote integrity checks provenance, not semantic correctness. Timing excludes model cold-start unless included in total pipeline runtime. Local hardware/electricity/hosting are unpriced.

Issue analytics describe a most-recently-updated sample. Label totals overlap, closure is not resolution, and the first observed comment is not a verified agent response. Do not interpret these as service SLAs.

## Data flow

Public tagged docs / GitHub issue snapshots → normalized SQL tables → keyword + embedding indexes → version/date eligibility → fused ranking → evidence gate → cited investigation → human review.
