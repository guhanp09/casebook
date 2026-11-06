"""Versioned source ingestion with raw snapshots and stable database keys."""

import hashlib
import json
import os
import re
import tarfile
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, text

from .io import ROOT, dump, fetch

REPOSITORY = "encode/httpx"
VERSIONS = {"0.27.2": "2024-08-27", "0.28.1": "2024-12-06"}


def engine():
    path = ROOT / "data/processed/casebook.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(os.environ.get("DATABASE_URL", f"sqlite:///{path}"))


def chunks(content, max_chars=1400):
    """Small contiguous paragraph groups; exact source excerpts remain attributable."""
    sections = re.split(r"\n(?=#{1,4} )", content)
    for section in sections:
        current = ""
        for paragraph in section.split("\n\n"):
            if len(current) + len(paragraph) > max_chars and current.strip():
                yield current.strip()
                current = ""
            if len(paragraph) > max_chars:
                for i in range(0, len(paragraph), max_chars):
                    yield paragraph[i : i + max_chars].strip()
            else:
                current += paragraph + "\n\n"
        if current.strip():
            yield current.strip()


def ingest(refresh=False, pages=3, comment_limit=12):
    docs, issue_rows, comment_rows, labels = [], [], [], []
    for version, released in VERSIONS.items():
        url = f"https://codeload.github.com/{REPOSITORY}/tar.gz/refs/tags/{version}"
        path = fetch(url, ROOT / f"data/raw/httpx-{version}.tar.gz", refresh)
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                name = "/".join(member.name.split("/")[1:])
                if not member.isfile() or not (
                    (name.startswith("docs/") and name.endswith(".md")) or name == "CHANGELOG.md"
                ):
                    continue
                content = archive.extractfile(member).read().decode("utf-8")
                for i, excerpt in enumerate(chunks(content)):
                    docs.append(
                        dict(
                            id=f"doc:{version}:{name}:{i}",
                            document=f"{version}:{name}",
                            title=name,
                            kind="documentation",
                            version=version,
                            published=released,
                            url=f"https://github.com/{REPOSITORY}/blob/{version}/{name}",
                            text=excerpt,
                        )
                    )
    raw_issues = []
    for page in range(1, pages + 1):
        url = f"https://api.github.com/repos/{REPOSITORY}/issues?state=all&per_page=100&sort=updated&direction=desc&page={page}"
        path = fetch(url, ROOT / f"data/raw/issues-page-{page}.json", refresh)
        raw_issues.extend(json.loads(path.read_text()))
    unique = {issue["number"]: issue for issue in raw_issues if "pull_request" not in issue}
    for number, item in unique.items():
        issue_rows.append(
            dict(
                number=number,
                title=item["title"],
                state=item["state"],
                created=item["created_at"],
                updated=item["updated_at"],
                closed=item["closed_at"],
                url=item["html_url"],
            )
        )
        body = item.get("body") or ""
        version_match = re.search(r"\b0\.(?:27\.2|28\.1)\b", body)
        version = version_match.group(0) if version_match else "unspecified"
        for i, excerpt in enumerate(chunks(item["title"] + "\n\n" + body)):
            docs.append(
                dict(
                    id=f"issue:{number}:{i}",
                    document=f"issue:{number}",
                    title=item["title"],
                    kind="issue",
                    version=version,
                    published=item["created_at"][:10],
                    url=item["html_url"],
                    text=excerpt,
                )
            )
        labels += [dict(number=number, label=label["name"]) for label in item["labels"]]
    # Bounded comment fetch keeps a complete raw archive for the selected sample without exhausting anonymous API limits.
    comment_issues = sorted(unique.values(), key=lambda x: x["number"], reverse=True)
    for item in [x for x in comment_issues if x["comments"] > 0][:comment_limit]:
        number = item["number"]
        url = f"https://api.github.com/repos/{REPOSITORY}/issues/{number}/comments?per_page=100"
        path = fetch(url, ROOT / f"data/raw/comments-{number}.json", refresh)
        for comment in json.loads(path.read_text()):
            comment_rows.append(
                dict(id=comment["id"], issue=number, created=comment["created_at"], url=comment["html_url"])
            )
            for i, excerpt in enumerate(chunks(comment.get("body") or "")):
                docs.append(
                    dict(
                        id=f"comment:{comment['id']}:{i}",
                        document=f"issue:{number}",
                        title=item["title"],
                        kind="comment",
                        version="unspecified",
                        published=comment["created_at"][:10],
                        url=comment["html_url"],
                        text=excerpt,
                    )
                )
    sources = pd.DataFrame(docs).drop_duplicates("id").sort_values("id").reset_index(drop=True)
    issues = pd.DataFrame(issue_rows)
    comments = pd.DataFrame(comment_rows, columns=["id", "issue", "created", "url"])
    label_frame = pd.DataFrame(labels, columns=["number", "label"])
    db = engine()
    with db.begin() as con:
        for name, frame in [
            ("sources", sources),
            ("issues", issues),
            ("comments", comments),
            ("issue_labels", label_frame),
        ]:
            # Transactional delete + insert is idempotent and preserves a coherent snapshot in PostgreSQL.
            frame.head(0).to_sql(name, con, if_exists="append", index=False)
            con.execute(text(f'DELETE FROM "{name}"'))
            frame.to_sql(name, con, if_exists="append", index=False, chunksize=1000)
        con.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS source_id ON sources (id)"))
        con.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS issue_number ON issues (number)"))
    sources.to_json(ROOT / "data/processed/sources.json", orient="records", indent=2)
    issues.to_csv(ROOT / "data/processed/issues.csv", index=False)
    comments.to_csv(ROOT / "data/processed/comments.csv", index=False)
    label_frame.to_csv(ROOT / "data/processed/issue_labels.csv", index=False)
    # API bodies can be edited after creation. Historical queries must not treat today's edited body as original.
    for number, issue in unique.items():
        sources.loc[sources.document == f"issue:{number}", "published"] = issue["updated_at"][:10]
    sources.to_json(ROOT / "data/processed/sources.json", orient="records", indent=2)
    with db.begin() as con:
        for number, issue in unique.items():
            con.execute(
                text("UPDATE sources SET published=:published WHERE document=:document AND kind='issue'"),
                dict(published=issue["updated_at"][:10], document=f"issue:{number}"),
            )
    dump(
        ROOT / "data/provenance.json",
        dict(
            repository=REPOSITORY,
            doc_versions=VERSIONS,
            snapshot_recorded_at=datetime.now(timezone.utc).isoformat(),
            sources=len(sources),
            issues=len(issues),
            comments=len(comments),
            pages=pages,
            attribution="HTTPX documentation and source: encode/httpx, BSD-3-Clause; public issue text remains attributed to linked authors",
            historical_caveat="Edited issue bodies use last-update dates. Comment snapshots do not establish historical edit times; comments are excluded from historical cutoff searches.",
            fingerprint=hashlib.sha256(sources.to_json().encode()).hexdigest(),
        ),
    )
    return sources, issues, comments, label_frame


def load_sources():
    return pd.read_json(ROOT / "data/processed/sources.json").fillna("")
