import argparse
import json

from .data import ingest, load_sources
from .pipeline import run
from .retrieval import Retriever, investigate


def main():
    p = argparse.ArgumentParser(description="Ingest, evaluate and investigate versioned software evidence")
    p.add_argument("command", choices=["run", "ingest", "investigate"], nargs="?", default="run")
    p.add_argument("question", nargs="?")
    p.add_argument("--version", default="0.28.1")
    p.add_argument("--as-of")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--skip-ingest", action="store_true")
    p.add_argument("--generative", action="store_true")
    a = p.parse_args()
    if a.command == "ingest":
        sources, issues, comments, _ = ingest(a.refresh)
        result = dict(sources=len(sources), issues=len(issues), comments=len(comments))
    elif a.command == "investigate":
        if not a.question:
            p.error("investigate requires a question")
        result = investigate(
            Retriever(load_sources()),
            a.question,
            a.version,
            a.as_of,
            "local" if a.generative else "extractive",
        )
    else:
        result = run(a.refresh, a.skip_ingest, a.generative)
    print(json.dumps(result, indent=2))
