"""Developer-authored retrieval benchmark; not independent customer evaluation."""

import time

import numpy as np
import pandas as pd

from .io import ROOT, dump
from .retrieval import investigate

# Three independently worded queries per theme. Shared themes across development/test
# make this a transparent in-domain benchmark, not an unseen-domain generalization test.
TOPICS = [
    (
        "docs/advanced/ssl.md",
        [
            "How can I configure a custom SSL certificate authority bundle?",
            "TLS certificate verification fails with my company's CA certificate.",
            "Where do I supply a custom SSLContext for certificate verification?",
        ],
    ),
    (
        "docs/advanced/ssl.md",
        [
            "How does HTTPX send a client certificate for mutual TLS?",
            "The server requires a client certificate and private key for SSL authentication.",
            "Can I configure load_cert_chain for HTTPS client certificates?",
        ],
    ),
    (
        "docs/advanced/proxies.md",
        [
            "How do I route HTTP traffic through a proxy?",
            "Configure an HTTP proxy URL for outbound requests.",
            "How do proxy mounts route traffic by scheme?",
        ],
    ),
    (
        "docs/advanced/proxies.md",
        [
            "How do I configure SOCKS proxy support?",
            "My client needs a SOCKS5 proxy dependency and URL.",
            "Which optional dependency supports socks proxies?",
        ],
    ),
    (
        "docs/advanced/timeouts.md",
        [
            "What is the difference between connect and read timeouts?",
            "Configure timeout settings for connecting and reading the response.",
            "How can I assign separate read, write and pool timeouts?",
        ],
    ),
    (
        "docs/advanced/timeouts.md",
        [
            "How do I disable request timeouts?",
            "Set timeout to None for long running operations.",
            "Can a client default timeout be disabled?",
        ],
    ),
    (
        "docs/advanced/resource-limits.md",
        [
            "How can I limit the number of connections in the pool?",
            "Configure max_connections and max_keepalive_connections.",
            "Where do I set keepalive_expiry for pooled connections?",
        ],
    ),
    (
        "docs/advanced/clients.md",
        [
            "Why should I reuse a Client for connection pooling?",
            "Repeated top-level requests do not reuse pooled connections.",
            "How does the Client context manager close connection pools?",
        ],
    ),
    (
        "docs/advanced/authentication.md",
        [
            "How can I implement a custom authentication flow?",
            "I need to subclass Auth and define auth_flow.",
            "Can a custom authentication flow yield several requests?",
        ],
    ),
    (
        "docs/advanced/authentication.md",
        [
            "How do I configure BasicAuth or DigestAuth?",
            "Send username and password with HTTP Basic authentication.",
            "Where are digest authentication credentials configured?",
        ],
    ),
    (
        "docs/advanced/event-hooks.md",
        [
            "How do event hooks inspect requests and responses?",
            "Configure response hooks for logging and raise_for_status.",
            "Can I attach an asynchronous response event hook?",
        ],
    ),
    (
        "docs/advanced/transports.md",
        [
            "How can I test an ASGI application without a network server?",
            "Use ASGITransport to make requests directly to the application.",
            "How do I connect AsyncClient to an ASGI app for tests?",
        ],
    ),
    (
        "docs/advanced/transports.md",
        [
            "How do I provide a mock transport for testing?",
            "MockTransport should return a predefined response from a handler.",
            "Can a custom transport intercept requests without sockets?",
        ],
    ),
    (
        "docs/advanced/text-encodings.md",
        [
            "How is the response text encoding selected?",
            "Configure default_encoding when the server omits charset.",
            "Can I use automatic character encoding detection for response text?",
        ],
    ),
    (
        "docs/async.md",
        [
            "How do I reuse an AsyncClient in asynchronous code?",
            "I need async with and await for AsyncClient requests.",
            "What is the supported way to stream responses asynchronously?",
        ],
    ),
    (
        "docs/environment_variables.md",
        [
            "How do I prevent environment variables from changing proxy configuration?",
            "Does trust_env=False disable HTTP_PROXY environment variables?",
            "What do NO_PROXY and HTTPS_PROXY change?",
        ],
    ),
    (
        "docs/http2.md",
        [
            "How do I enable HTTP/2 support?",
            "What optional dependencies are needed for http2=True?",
            "How can I check the negotiated HTTP protocol version?",
        ],
    ),
    (
        "docs/logging.md",
        [
            "How do I enable HTTPX debug logging?",
            "I need connection-level diagnostic logs from httpcore.",
            "Which Python logging settings show HTTPX debug output?",
        ],
    ),
    (
        "docs/compatibility.md",
        [
            "Does HTTPX automatically follow redirects like requests?",
            "What are the main requests compatibility differences?",
            "How do I migrate a requests client with redirect behavior?",
        ],
    ),
    (
        "docs/quickstart.md",
        [
            "How can I upload a file with multipart form data?",
            "Send multipart files and a custom upload filename.",
            "How do file uploads use the files parameter?",
        ],
    ),
    (
        "docs/quickstart.md",
        [
            "How do I send JSON request bodies?",
            "Submit a dictionary as a JSON body rather than form encoded data.",
            "What is the json parameter used for when posting data?",
        ],
    ),
    (
        "docs/exceptions.md",
        [
            "Which exception represents a pool acquisition timeout?",
            "What exception hierarchy includes PoolTimeout and ConnectTimeout?",
            "How can I distinguish HTTPStatusError from RequestError?",
        ],
    ),
    (
        "docs/advanced/clients.md",
        [
            "How are client-level headers merged with request headers?",
            "Combine client defaults with per-request configuration.",
            "How does Client.build_request apply shared client settings?",
        ],
    ),
    (
        "CHANGELOG.md",
        [
            "Was the deprecated proxies argument removed in version 0.28?",
            "My upgrade to 0.28 fails because the app argument was removed.",
            "What changed in SSL configuration deprecations in 0.28.0?",
        ],
    ),
]


def benchmark():
    rows = []
    for i, (path, questions) in enumerate(TOPICS):
        for j, query in enumerate(questions):
            rows.append(
                dict(
                    id=f"topic-{i:02}-{j}",
                    question=query,
                    version="0.28.1",
                    expected_document=f"0.28.1:{path}",
                    expected_status="evidence_found",
                    split="development" if j == 0 else "test",
                )
            )
    for i, question in enumerate(
        [
            "How should I fertilize a mango orchard?",
            "What are the tax deductions for a bakery?",
            "How do I price actuarial catastrophe insurance?",
            "Diagnose a bicycle hydraulic brake leak.",
            "What is the recipe for sourdough bread?",
            "How do I repair a cracked concrete foundation?",
        ]
    ):
        rows.append(
            dict(
                id=f"unsupported-{i}",
                question=question,
                version="0.28.1",
                expected_document=None,
                expected_status="insufficient_evidence",
                split="development" if i < 2 else "test",
            )
        )
    dump(
        ROOT / "data/benchmark.json",
        dict(
            provenance="Developer-authored in-domain questions and expected source pages; theme overlap across splits; not independent human validation",
            fixed_support_gate="keyword cosine >= 0.045 and >= 2 non-generic overlapping terms; not tuned using test results",
            rows=rows,
        ),
    )
    return rows


def evaluate(retriever):
    rows = benchmark()
    results = []
    for method in ["keyword", "embedding", "hybrid"]:
        for row in rows:
            started = time.perf_counter()
            hits = retriever.search(row["question"], row["version"], method=method, k=5)
            rank = next(
                (i + 1 for i, hit in enumerate(hits) if hit["document"] == row["expected_document"]), None
            )
            results.append(
                dict(
                    id=row["id"],
                    split=row["split"],
                    method=method,
                    answerable=row["expected_document"] is not None,
                    recall_at_5=int(rank is not None),
                    reciprocal_rank=1 / rank if rank else 0.0,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
            )
    workflow = []
    for row in rows:
        outcome = investigate(retriever, row["question"], row["version"])
        valid = all(
            any(e["quote"] in text for text in retriever.sources.loc[retriever.sources.id == e["id"], "text"])
            for e in outcome["evidence"]
        )
        workflow.append(
            dict(
                id=row["id"],
                split=row["split"],
                expected_status=row["expected_status"],
                actual_status=outcome["status"],
                status_correct=outcome["status"] == row["expected_status"],
                citation_excerpt_valid=valid,
                expected_document_retrieved=any(
                    e["document"] == row["expected_document"] for e in outcome["evidence"]
                ),
            )
        )
    results = pd.DataFrame(results)
    workflow = pd.DataFrame(workflow)
    results.to_csv(ROOT / "reports/retrieval_evaluation.csv", index=False)
    workflow.to_csv(ROOT / "reports/workflow_evaluation.csv", index=False)
    summaries = []
    for (method, split), group in results[results.answerable].groupby(["method", "split"]):
        summaries.append(
            dict(
                method=method,
                split=split,
                questions=len(group),
                recall_at_5=float(group.recall_at_5.mean()),
                mrr=float(group.reciprocal_rank.mean()),
                median_latency_ms=float(group.latency_ms.median()),
                p95_latency_ms=float(np.quantile(group.latency_ms, 0.95)),
            )
        )
    return dict(
        questions=len(rows),
        retrieval=summaries,
        citation_excerpt_integrity=float(workflow.citation_excerpt_valid.mean()),
        status_accuracy=float(workflow.status_correct.mean()),
        unsupported_abstention_rate=float(
            (
                workflow.loc[workflow.expected_status == "insufficient_evidence", "actual_status"]
                == "insufficient_evidence"
            ).mean()
        ),
        caveat="Quoted-source integrity is not semantic citation correctness; benchmark is author-developed and theme-overlapping",
    )
