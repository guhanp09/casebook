"""Keyword, sentence embedding, and reciprocal-rank-fusion retrieval."""

import hashlib
import re

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .io import ROOT, dump

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


def embedder():
    from sentence_transformers import SentenceTransformer

    path = ROOT / "models/embedder"
    model = SentenceTransformer(str(path) if path.exists() else MODEL_ID, device="cpu")
    if not path.exists():
        model.save(str(path))
    return model


def build(sources):
    folder = ROOT / "models"
    folder.mkdir(exist_ok=True)
    texts = (sources.title + "\n" + sources.text).tolist()
    keyword = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True, max_features=80000)
    sparse = keyword.fit_transform(texts)
    embeddings = embedder().encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=True)
    joblib.dump(dict(vectorizer=keyword, sparse=sparse, ids=sources.id.tolist()), folder / "keyword.joblib")
    np.save(folder / "embeddings.npy", embeddings)
    dump(
        folder / "index_manifest.json",
        dict(
            model=MODEL_ID,
            sources=len(sources),
            dimension=int(embeddings.shape[1]),
            source_order_sha256=hashlib.sha256("\n".join(sources.id).encode()).hexdigest(),
        ),
    )


class Retriever:
    def __init__(self, sources, use_dense=True):
        self.sources = sources.reset_index(drop=True)
        saved = joblib.load(ROOT / "models/keyword.joblib")
        if saved["ids"] != self.sources.id.tolist():
            raise ValueError("Source snapshot differs from retrieval index; rebuild the index")
        self.vectorizer = saved["vectorizer"]
        self.sparse = saved["sparse"]
        self.dense = np.load(ROOT / "models/embeddings.npy")
        self.model = embedder() if use_dense else None

    def search(self, question, version="0.28.1", as_of=None, method="hybrid", k=5):
        if method not in ["keyword", "embedding", "hybrid"]:
            raise ValueError("Unknown retrieval method")
        if not 1 <= k <= 20:
            raise ValueError("k must be between 1 and 20")
        eligible = np.ones(len(self.sources), dtype=bool)
        if version:
            eligible &= self.sources.version.to_numpy() == version
        if as_of:
            eligible &= self.sources.published.to_numpy().astype(str) <= str(as_of)
            eligible &= self.sources.kind.to_numpy() != "comment"
        indices = np.flatnonzero(eligible)
        if not len(indices):
            return []
        keyword = (self.sparse @ self.vectorizer.transform([question]).T).toarray().ravel()
        dense = np.zeros(len(self.sources))
        if method != "keyword":
            if self.model is None:
                self.model = embedder()
            dense = self.dense @ self.model.encode([question], normalize_embeddings=True)[0]
        if method == "keyword":
            scores = keyword
        elif method == "embedding":
            scores = dense
        else:
            scores = np.zeros(len(self.sources))
            for component in [keyword, dense]:
                ordered = indices[np.argsort(-component[indices], kind="stable")]
                scores[ordered] += 1 / (60 + np.arange(1, len(ordered) + 1))
        best = indices[np.argsort(-scores[indices], kind="stable")[:k]]
        found = []
        for idx in best:
            row = self.sources.iloc[idx].to_dict()
            row.update(
                score=float(scores[idx]), keyword_score=float(keyword[idx]), embedding_score=float(dense[idx])
            )
            found.append(row)
        return found


STOP = {
    "the",
    "and",
    "for",
    "with",
    "what",
    "when",
    "where",
    "how",
    "can",
    "does",
    "httpx",
    "request",
    "requests",
    "use",
    "using",
    "why",
    "from",
    "this",
    "that",
    "are",
    "into",
}


def terms(text):
    return {x for x in re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()) if x not in STOP}


def excerpt(question, source):
    """Select an exact contiguous paragraph; no claims are invented by the drafter."""
    paragraphs = [p.strip() for p in source["text"].split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    query = terms(question)
    ranked = sorted(paragraphs, key=lambda p: len(query & terms(p)), reverse=True)
    return ranked[0][:900]


def investigate(retriever, question, version="0.28.1", as_of=None, backend="extractive"):
    if not question.strip():
        raise ValueError("A troubleshooting question is required")
    found = retriever.search(question, version, as_of)
    supported = [
        s
        for s in found
        if s["keyword_score"] >= 0.045 and len(terms(question) & terms(s["text"] + " " + s["title"])) >= 2
    ]
    evidence = []
    seen = set()
    for source in supported:
        if source["document"] not in seen:
            evidence.append(
                dict(
                    id=source["id"],
                    document=source["document"],
                    url=source["url"],
                    version=source["version"],
                    quote=excerpt(question, source),
                    title=source["title"],
                    kind=source["kind"],
                )
            )
            seen.add(source["document"])
    status = "evidence_found" if evidence else "insufficient_evidence"
    questions = [
        "What is the exact HTTPX version and full exception traceback?",
        "Can you share a minimal reproducer with credentials removed?",
        "Does the problem reproduce with the same proxy, TLS, and timeout settings?",
    ]
    draft = "I need more diagnostic information before suggesting a cause. " + questions[0]
    if evidence:
        draft = (
            "Relevant source observations (candidate evidence, not a confirmed diagnosis):\n\n"
            + "\n\n".join(f"[{i}] {e['quote']}\nSource: {e['url']}" for i, e in enumerate(evidence, 1))
        )
    generated = None
    if backend == "local" and evidence:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        path = ROOT / "models/drafter"
        if not path.exists():
            tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
            model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")
            path.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(path)
            model.save_pretrained(path)
        else:
            tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True)
        context = "\n".join(e["quote"][:450] for e in evidence[:2])
        prompt = f"Based on this documentation, suggest one diagnostic question. Do not claim the issue is solved. Documentation: {context}\nUser problem: {question}\nDiagnostic question:"
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        generated = tokenizer.decode(
            model.generate(**inputs, max_new_tokens=80, do_sample=False)[0], skip_special_tokens=True
        )
    if backend not in ["extractive", "local"]:
        raise ValueError("Unknown draft backend")
    return dict(
        status=status,
        question=question,
        version=version,
        as_of=as_of,
        evidence=evidence,
        draft=draft,
        generated_diagnostic_question=generated,
        generated_text_requires_review=generated is not None,
        missing_information=questions,
        workflow=[
            "validate_context",
            "filter_version_and_date",
            "retrieve",
            "check_lexical_support",
            "assemble_cited_evidence",
            "request_human_review",
        ],
        limitations="Citations establish provenance, not correctness or applicability. Lexical gating is not semantic entailment. Source contents are untrusted evidence, never executed instructions.",
    )
