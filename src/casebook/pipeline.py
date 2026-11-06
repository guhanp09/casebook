import time

import pandas as pd
import plotly.express as px
from sqlalchemy import text

from .data import engine, ingest, load_sources
from .evaluation import evaluate
from .io import ROOT, chart, dump, report
from .retrieval import Retriever, build, investigate


def operational_metrics(issues, comments, labels):
    issues = issues.copy()
    issues["created_dt"] = pd.to_datetime(issues.created, utc=True)
    issues["closed_dt"] = pd.to_datetime(issues.closed, utc=True)
    issues["days_to_close"] = (issues.closed_dt - issues.created_dt).dt.total_seconds() / 86400
    closed = issues[issues.closed_dt.notna()]
    categories = (
        labels.merge(issues[["number", "state"]], on="number")
        .groupby(["label", "state"])
        .size()
        .rename("issues")
        .reset_index()
    )
    categories.to_csv(ROOT / "reports/issue_categories.csv", index=False)
    if not comments.empty:
        first = comments.groupby("issue").created.min()
        sample = issues[issues.number.isin(first.index)].copy()
        sample["first_observed_comment"] = pd.to_datetime(sample.number.map(first), utc=True)
        sample["hours_to_first_observed_comment"] = (
            sample.first_observed_comment - sample.created_dt
        ).dt.total_seconds() / 3600
        sample[["number", "hours_to_first_observed_comment"]].to_csv(
            ROOT / "reports/comment_timing_sample.csv", index=False
        )
    with engine().connect() as con:
        db_sources = int(con.execute(text("SELECT COUNT(*) FROM sources")).scalar())
        db_issues = int(con.execute(text("SELECT COUNT(*) FROM issues")).scalar())
    return dict(
        sampled_issues=len(issues),
        open_in_sample=int((issues.state == "open").sum()),
        closed_in_sample=len(closed),
        median_days_to_close=float(closed.days_to_close.median()) if len(closed) else None,
        comments_sampled=len(comments),
        database_sources=db_sources,
        database_issues=db_issues,
        sampling="Most recently updated API pages; not a representative service workload. Labels may overlap. Closed does not mean resolved. First observed comment may be by the reporter and is not a verified first-response SLA.",
    )


def run(refresh=False, skip_ingest=False, generative=False):
    start = time.perf_counter()
    if skip_ingest:
        sources = load_sources()
        issues = pd.read_csv(ROOT / "data/processed/issues.csv")
        comments = pd.read_csv(ROOT / "data/processed/comments.csv")
        labels = pd.read_csv(ROOT / "data/processed/issue_labels.csv")
    else:
        sources, issues, comments, labels = ingest(refresh)
    build(sources)
    retriever = Retriever(sources)
    evaluation = evaluate(retriever)
    examples = []
    for question, version, cutoff in [
        (
            "How do I configure a custom SSL certificate authority bundle for TLS verification?",
            "0.28.1",
            None,
        ),
        ("Was the deprecated proxies argument removed in version 0.28?", "0.28.1", None),
        ("How do I repair a cracked concrete foundation?", "0.28.1", None),
        ("How can I configure SSL certificate verification?", "0.28.1", "2024-12-01"),
    ]:
        examples.append(
            investigate(retriever, question, version, cutoff, "local" if generative else "extractive")
        )
    dump(ROOT / "reports/investigation_examples.json", examples)
    operation = operational_metrics(issues, comments, labels)
    metrics = dict(
        sources=len(sources),
        operational=operation,
        evaluation=evaluation,
        total_pipeline_seconds=time.perf_counter() - start,
        generation_exercised=generative,
        default_backend="extractive quoted evidence",
        model="sentence-transformers/all-MiniLM-L6-v2",
        local_drafter="google/flan-t5-small" if generative else None,
        external_inference_api_calls=0,
        external_inference_api_charge_usd=0,
        cost_caveat="Local CPU time, electricity and hosting are unpriced; zero API charge is not zero operating cost",
    )
    plot = pd.DataFrame(evaluation["retrieval"])
    chart(
        px.bar(
            plot,
            x="method",
            y="recall_at_5",
            color="split",
            barmode="group",
            title="Author-developed source-page retrieval benchmark",
        ),
        "retrieval_comparison",
    )
    report(
        "Casebook",
        f"""# Evidence-grounded support investigation

The snapshot contains {len(sources):,} source chunks from two HTTPX documentation tags and public issue histories, with {len(issues)} sampled issues and {len(comments)} sampled comments. Source IDs, URLs, versions and available dates are preserved. Raw response checksums and source provenance are retained. Ingestion replaces the snapshot transactionally and is idempotent by stable source/issue keys; it supports SQLite locally and PostgreSQL through DATABASE_URL.

Retrieval compares keyword TF-IDF, MiniLM sentence embeddings and reciprocal-rank fusion. Version and date constraints are applied before ranking. Edited issue bodies are dated by last update, and comments are excluded from historical cutoff searches because current snapshots do not establish comment edit history. Documentation publication dates are release-tag dates.

The bounded workflow validates context, retrieves sources, applies a lexical support gate, and assembles exact source excerpts with citations. No extractive draft is presented as a confirmed diagnosis. Unsupported questions request more information. Optional local Flan-T5 drafting proposes an unverified diagnostic question and always requires human review; citations do not certify generated text.

The {evaluation["questions"]}-question benchmark is developer-authored with expected source pages. Development/test wording differs but themes overlap, so this is an in-domain development benchmark, not independent human evaluation. Detailed per-query failures and timing remain in retrieval_evaluation.csv. Unsupported-question abstention rate: {evaluation["unsupported_abstention_rate"]:.1%}. Quoted-source integrity: {evaluation["citation_excerpt_integrity"]:.1%}. The latter checks exact provenance, not semantic entailment or troubleshooting correctness.

Operational metrics describe the most recently updated issue sample, not customer-support performance. Open issues in sample: {operation["open_in_sample"]}; closed issues: {operation["closed_in_sample"]}. Closure is not verified resolution, labels overlap, and comment timing is not an SLA measure. Avoid projecting sample totals onto the whole repository.

Recommendation: use source-linked investigation briefs to support human troubleshooting, starting with the version-filtered TLS and upgrade examples. Review retrieval misses before widening scope. A historical query for version 0.28.1 before its release correctly returns insufficient evidence. Example transcripts are saved as structured workflow records.

The application, FastAPI endpoints, PostgreSQL Compose configuration, container definition and scheduled-ingestion workflow are included. These are local/deployable artifacts; no cloud hosting or live customer use is claimed. External inference API charge is zero because inference is local; hardware and hosting costs are unpriced.

Limitations: author-developed benchmark, two old documentation versions, partial issue/comment sampling, source editing, embedding truncation, no proven semantic entailment, no automatic external actions, and no independent user productivity study. A source may be relevant without being sufficient to diagnose the user's environment.
""",
        metrics,
    )
    return metrics
