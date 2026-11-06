import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from casebook import retrieval
from casebook.data import chunks
from casebook.retrieval import Retriever, excerpt, investigate


@pytest.fixture
def index(tmp_path, monkeypatch):
    sources = pd.DataFrame(
        [
            dict(
                id="current",
                document="current",
                title="SSL",
                text="Configure custom SSL certificate verification with a certificate authority bundle.",
                version="0.28.1",
                published="2024-12-06",
                kind="documentation",
                url="https://example.org/current",
            ),
            dict(
                id="old",
                document="old",
                title="SSL",
                text="SSL certificate verification older configuration.",
                version="0.27.2",
                published="2024-08-27",
                kind="documentation",
                url="https://example.org/old",
            ),
            dict(
                id="future",
                document="future",
                title="SSL",
                text="SSL certificate verification future configuration.",
                version="0.28.1",
                published="2027-01-01",
                kind="documentation",
                url="https://example.org/future",
            ),
        ]
    )
    monkeypatch.setattr(retrieval, "ROOT", tmp_path)
    (tmp_path / "models").mkdir()
    vectorizer = TfidfVectorizer()
    sparse = vectorizer.fit_transform(sources.text)
    joblib.dump(
        dict(ids=sources.id.tolist(), vectorizer=vectorizer, sparse=sparse),
        tmp_path / "models/keyword.joblib",
    )
    np.save(tmp_path / "models/embeddings.npy", np.zeros((3, 2)))

    class Embeddings:
        def encode(self, *args, **kwargs):
            return np.array([[1.0, 0.0]])

    monkeypatch.setattr(retrieval, "embedder", lambda: Embeddings())
    return Retriever(sources)


def test_version_and_historical_availability_filters(index):
    result = index.search("SSL certificate", version="0.28.1", as_of="2025-01-01", method="keyword")
    assert [r["id"] for r in result] == ["current"]
    assert index.search("SSL certificate", version="0.28.1", as_of="2024-12-01", method="keyword") == []


def test_insufficient_context_abstains(index):
    result = investigate(index, "How do I repair a bicycle brake?")
    assert result["status"] == "insufficient_evidence"
    assert result["evidence"] == []
    assert result["missing_information"]


def test_quotes_are_exact_source_content(index):
    result = investigate(index, "Configure custom SSL certificate verification", as_of="2025-01-01")
    assert result["status"] == "evidence_found"
    assert result["evidence"][0]["quote"] in index.sources.iloc[0].text
    assert result["generated_diagnostic_question"] is None


def test_reordered_source_snapshot_is_rejected(index):
    with pytest.raises(ValueError, match="snapshot"):
        Retriever(index.sources.iloc[::-1], use_dense=False)


def test_invalid_search_inputs_and_empty_question(index):
    with pytest.raises(ValueError, match="method"):
        index.search("SSL", method="invalid")
    with pytest.raises(ValueError, match="between"):
        index.search("SSL", k=100)
    with pytest.raises(ValueError, match="required"):
        investigate(index, " ")


def test_chunking_and_excerpt_preserve_source():
    source = "# TLS\n\nCertificate verification.\n\n" + "a" * 3000
    pieces = list(chunks(source, max_chars=100))
    assert pieces
    assert all(p in source for p in pieces)
    quote = excerpt("certificate verification", {"text": "Unrelated paragraph.\n\nCertificate verification."})
    assert quote == "Certificate verification."


def test_historical_search_excludes_comment_snapshots(index):
    index.sources.loc[0, "kind"] = "comment"
    assert index.search("SSL certificate", as_of="2025-01-01", method="keyword") == []
