"""Load documents from Markdown files with YAML front matter."""
from __future__ import annotations

from pathlib import Path

import yaml

from atlas.retrieval.text import Document


def load_document(path: Path) -> Document:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: missing front matter")
    _, fm, body = text.split("---\n", 2)
    meta = yaml.safe_load(fm) or {}
    return Document(
        doc_id=str(meta["doc_id"]), title=str(meta["title"]), body=body.strip(),
        acl=frozenset(map(str, meta.get("acl", []))), status=str(meta.get("status", "current")),
        source=str(meta.get("source", "wiki")), version=str(meta.get("version", "1")),
        updated=str(meta.get("updated", "")), owner=str(meta.get("owner", "")),
        classification=str(meta.get("classification", "internal")))


def load_corpus(directory: Path) -> list[Document]:
    return [load_document(p) for p in sorted(Path(directory).glob("*.md"))]
