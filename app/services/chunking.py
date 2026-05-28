"""Semantic chunk generation for operational DSM documents."""
from dataclasses import dataclass
from typing import Any

SEMANTIC_FIELDS = [
    "diagnostic_rule", "criteria", "clusters", "severity", "specifiers", "subtypes",
    "operational_profiles", "critical_differentials", "key_questions", "alerts",
    "full_operational_summary",
]


@dataclass(slots=True)
class ChunkPayload:
    chunk_type: str
    chunk_title: str
    chunk_text: str
    metadata: dict[str, Any]


class DsmChunkingService:
    max_chars = 5000

    def build_chunks(self, document: dict[str, Any]) -> list[ChunkPayload]:
        item_id = str(document.get("item_id") or document.get("id"))
        name = str(document.get("name") or document.get("title") or item_id)
        chapter_id = str(document.get("chapter_id") or document.get("chapter") or "")
        category = str(document.get("category") or "")
        chunks: list[ChunkPayload] = []
        for field in SEMANTIC_FIELDS:
            value = self._deep_get(document, field)
            text = self._stringify(value)
            if not text:
                continue
            for idx, part in enumerate(self._split_if_needed(text)):
                title_suffix = field.replace("_", " ")
                title = f"{name} — {title_suffix}" + (f" ({idx + 1})" if idx else "")
                chunks.append(
                    ChunkPayload(
                        chunk_type=field,
                        chunk_title=title,
                        chunk_text=part,
                        metadata={"item_id": item_id, "chapter_id": chapter_id, "category": category, "source_field": field},
                    )
                )
        return chunks

    def _deep_get(self, document: dict[str, Any], field: str) -> Any:
        if field in document:
            return document[field]
        clinical = document.get("clinical") or document.get("content") or document.get("operational") or {}
        if isinstance(clinical, dict):
            return clinical.get(field)
        return None

    def _stringify(self, value: Any, indent: int = 0) -> str:
        if value is None or value == "":
            return ""
        prefix = "  " * indent
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            lines = [self._stringify(v, indent + 1) for v in value]
            return "\n".join(f"{prefix}- {line}" for line in lines if line)
        if isinstance(value, dict):
            lines: list[str] = []
            for key, val in value.items():
                text = self._stringify(val, indent + 1)
                if text:
                    lines.append(f"{prefix}{key}: {text}")
            return "\n".join(lines)
        return str(value).strip()

    def _split_if_needed(self, text: str) -> list[str]:
        if len(text) <= self.max_chars:
            return [text]
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        parts: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 > self.max_chars and current:
                parts.append(current)
                current = paragraph
            else:
                current = f"{current}\n{paragraph}".strip()
        if current:
            parts.append(current)
        return parts
