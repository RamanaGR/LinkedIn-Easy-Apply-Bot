"""
Ollama-based intent matching for Q&A memory (pick best candidate by meaning).
"""

from __future__ import annotations

import json
import re
from typing import List, Optional

from src.logger import get_logger
from src.ollama_client import OllamaChatMessage, OllamaClient

logger = get_logger()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity without numpy."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def parse_intent_json_index(raw: str) -> Optional[int]:
    """Parse model output for {"index": n} only."""
    if not raw:
        return None
    text = raw.strip()
    # Strip markdown fences
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            text = m.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "index" in data:
            return int(data["index"])
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    # Fallback: first integer after "index"
    m = re.search(r'"index"\s*:\s*(-?\d+)', text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def ollama_pick_question_index(
    client: OllamaClient,
    model: str,
    current_question: str,
    candidate_questions: List[str],
    timeout_seconds: Optional[int] = None,
) -> Optional[int]:
    """
    Ask Ollama which candidate (by index) matches the current question's intent.

    Returns:
        0-based index into candidate_questions, or None if model says -1 / parse fail.
    """
    if not candidate_questions:
        return None

    lines = []
    for i, q in enumerate(candidate_questions):
        safe = (q or "").replace("\r", " ")[:2000]
        lines.append(f'{i}: """{safe}"""')

    cq = (current_question or "").replace("\r", " ")[:2000]
    user_prompt = (
        "You match job application form questions to previously saved questions (same intent = same field).\n\n"
        'Return ONLY valid JSON with no other text: {"index": <integer>}\n'
        f"Use index 0 to {len(candidate_questions) - 1} if one candidate is the same question or same meaning.\n"
        'Use {"index": -1} if none of the candidates match.\n\n'
        f'Current question:\n"""\n{cq}\n"""\n\n'
        "Candidates:\n"
        + chr(10).join(lines)
    )

    messages = [
        OllamaChatMessage(role="system", content="You output only JSON objects with an integer index field."),
        OllamaChatMessage(role="user", content=user_prompt),
    ]

    to = timeout_seconds or client.timeout_seconds
    old_to = client.timeout_seconds
    try:
        client.timeout_seconds = to
        raw = client.chat(messages, model=model, temperature=0.0, max_tokens=80)
    finally:
        client.timeout_seconds = old_to

    idx = parse_intent_json_index(raw)
    if idx is None:
        logger.debug(f"Intent LLM parse failed, raw={raw[:200]!r}")
        return None
    if idx < 0:
        return None
    if idx >= len(candidate_questions):
        logger.warning(f"Intent LLM index out of range: {idx}")
        return None
    return idx
