"""
Q&A Memory Manager - Self-Learning Question Answering System

This module handles persistent storage and retrieval of question-answer pairs
learned from user interactions during job applications.

Lookup uses exact match, normalized short keys, fuzzy matching, optional
Ollama embeddings, and optional Ollama intent selection for paraphrased questions.
"""

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.logger import get_logger

logger = get_logger()

# Filter ultra-common words so word-overlap pool is not dominated by boilerplate
_WORD_STOP = frozenset(
    """
    the a an is are was were be been being do does did done you your we our they their
    have has had with for and or not this that these those any all will shall can could
    would should may might must how what when where which who whom whose why can
    to of in on at as by from if it its at least more most some such only just also than
    then there than into about over out up down
    """.split()
)

try:
    from thefuzz import fuzz, process

    FUZZY_MATCHING_AVAILABLE = True
except ImportError:
    FUZZY_MATCHING_AVAILABLE = False
    fuzz = None  # type: ignore
    process = None  # type: ignore
    logger.warning("⚠️ thefuzz not installed - using exact matching only")
    logger.warning("Install with: pip install thefuzz python-Levenshtein")


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v).lower().strip() in ("1", "true", "yes", "on")


def _yaml_bool(val: Any, default: bool) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower().strip() in ("1", "true", "yes", "on")


@dataclass
class QAMemoryLookupSettings:
    """Settings for multi-tier Q&A lookup (env QA_MEMORY_* overrides yaml qa_memory)."""

    fuzzy_threshold_high: int = 88
    fuzzy_threshold_low: int = 62
    fuzzy_candidate_limit: int = 40
    intent_llm_enabled: bool = True
    intent_top_k: int = 25
    embedding_enabled: bool = False
    embedding_model: str = "nomic-embed-text"
    embedding_threshold: float = 0.82
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = ""

    @classmethod
    def from_config(cls, config: Optional[Any]) -> "QAMemoryLookupSettings":
        q: Dict[str, Any] = {}
        if config is not None and hasattr(config, "get"):
            raw = config.get("qa_memory", None)
            if isinstance(raw, dict):
                q = raw

        high = _env_int("QA_MEMORY_FUZZY_HIGH", q.get("fuzzy_threshold_high", 88))
        low = _env_int("QA_MEMORY_FUZZY_LOW", q.get("fuzzy_threshold_low", 62))
        limit = _env_int("QA_MEMORY_FUZZY_CANDIDATE_LIMIT", q.get("fuzzy_candidate_limit", 40))
        intent_on = _env_bool("QA_MEMORY_INTENT_LLM", _yaml_bool(q.get("intent_llm_enabled"), True))
        top_k = _env_int("QA_MEMORY_INTENT_TOP_K", q.get("intent_top_k", 25))
        emb_on = _env_bool("QA_MEMORY_EMBEDDING", _yaml_bool(q.get("embedding_enabled"), False))
        emb_model = os.getenv("QA_MEMORY_EMBEDDING_MODEL") or str(
            q.get("embedding_model") or "nomic-embed-text"
        )
        emb_thr = _env_float("QA_MEMORY_EMBEDDING_THRESHOLD", float(q.get("embedding_threshold", 0.82)))

        base = "http://127.0.0.1:11434"
        if config is not None and hasattr(config, "ollama_base_url"):
            base = getattr(config, "ollama_base_url") or base
        base = os.getenv("OLLAMA_BASE_URL") or os.getenv("QA_MEMORY_OLLAMA_URL") or base

        chat_model = ""
        if config is not None and hasattr(config, "ollama_model"):
            chat_model = (getattr(config, "ollama_model") or "").strip()
        chat_model = os.getenv("QA_MEMORY_CHAT_MODEL") or chat_model

        return cls(
            fuzzy_threshold_high=max(50, min(100, int(high))),
            fuzzy_threshold_low=max(40, min(100, int(low))),
            fuzzy_candidate_limit=max(5, min(200, int(limit))),
            intent_llm_enabled=intent_on,
            intent_top_k=max(3, min(50, int(top_k))),
            embedding_enabled=emb_on,
            embedding_model=emb_model.strip() or "nomic-embed-text",
            embedding_threshold=max(0.5, min(0.99, float(emb_thr))),
            ollama_base_url=base.rstrip("/"),
            ollama_chat_model=chat_model,
        )


class QAMemoryManager:
    """Manages the persistent Q&A knowledge base."""

    def __init__(self, memory_file: str = "qa_memory.csv", config: Optional[Any] = None):
        """
        Initialize the Q&A memory manager.

        Args:
            memory_file: Path to the CSV file storing Q&A pairs
            config: Optional Config instance (yaml `qa_memory` + env QA_MEMORY_*)
        """
        self.memory_file = Path(memory_file)
        self.memory: Dict[str, str] = {}
        self._settings = QAMemoryLookupSettings.from_config(config)
        self._ollama = None
        self._embedding_cache: Dict[str, List[float]] = {}

        if self._settings.intent_llm_enabled or self._settings.embedding_enabled:
            try:
                from src.ollama_client import OllamaClient

                self._ollama = OllamaClient(
                    base_url=self._settings.ollama_base_url,
                    model=self._settings.ollama_chat_model,
                    timeout_seconds=45,
                )
            except Exception as e:
                logger.warning(f"Ollama client not available for Q&A matching: {e}")
                self._ollama = None

        self._ensure_memory_file()
        self._load_memory()

    def _ensure_memory_file(self):
        """Create the memory file if it doesn't exist."""
        if not self.memory_file.exists():
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["question_text", "answer_text"])
            logger.info(f"Created Q&A memory file: {self.memory_file}")

    def _load_memory(self):
        """Load all Q&A pairs from the CSV file into memory."""
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_q = row.get("question_text") or ""
                    answer = (row.get("answer_text") or "").strip()
                    question = self._normalize_text_for_match(raw_q)
                    if not question:
                        continue
                    self.memory[question] = answer

            logger.info(f"Loaded {len(self.memory)} Q&A pairs from memory")
        except Exception as e:
            logger.error(f"Failed to load Q&A memory: {e}")
            self.memory = {}

    def _normalize_text(self, text: str) -> str:
        """Legacy normalize (kept for compatibility)."""
        text = text.lower().strip()
        text = " ".join(text.split())
        text = text.replace("?", "").replace(":", "").replace("*", "")
        return text

    def _collapse_duplicate_sentences(self, text: str) -> str:
        """Remove immediately repeated sentence segments (LinkedIn duplicates labels)."""
        parts = [p.strip() for p in text.split(".") if p.strip()]
        if len(parts) < 2:
            return text
        out: List[str] = []
        for p in parts:
            if not out or out[-1] != p:
                out.append(p)
        return ". ".join(out) if out else text

    def _collapse_repeated_words(self, text: str) -> str:
        """Collapse consecutive duplicate words (e.g. 'gender gender')."""
        words = text.split()
        if len(words) < 2:
            return text
        out: List[str] = []
        for w in words:
            if not out or out[-1] != w:
                out.append(w)
        return " ".join(out)

    def _normalize_text_for_match(self, text: str) -> str:
        """
        Normalize question text for storage and lookup: lowercase, punctuation,
        collapse duplicate sentences and words, single spaces.
        """
        text = text.lower().strip()
        text = " ".join(text.split())
        text = text.replace("?", "").replace(":", "").replace("*", "")
        text = self._collapse_repeated_words(text)
        text = self._collapse_duplicate_sentences(text)
        text = " ".join(text.split())
        return text

    def _short_key(self, normalized: str, max_len: int = 160) -> str:
        """First segment of normalized text for looser exact match."""
        if not normalized:
            return ""
        for marker in (
            "race categories are defined",
            "protected veterans may have",
            "uniformed services employment",
        ):
            idx = normalized.find(marker)
            if idx > 20:
                return normalized[:idx].strip()[:max_len]
        return normalized[:max_len].strip()

    def _word_overlap_pool(self, normalized_query: str, limit: int) -> List[Tuple[str, int]]:
        """Rank memory keys by count of overlapping words (when thefuzz is unavailable)."""
        words = {
            w
            for w in re.split(r"\W+", normalized_query)
            if len(w) > 2 and w not in _WORD_STOP
        }
        if not words:
            return []
        scored: List[Tuple[str, int]] = []
        for k in self.memory:
            kw = {
                w
                for w in re.split(r"\W+", k)
                if len(w) > 2 and w not in _WORD_STOP
            }
            overlap = len(words & kw)
            if overlap > 0:
                scored.append((k, overlap))
        scored.sort(key=lambda x: -x[1])
        return [(k, s) for k, s in scored[:limit]]

    def lookup_answer(self, question: str) -> Optional[str]:
        """
        Look up an answer: exact / short-key / fuzzy / embeddings / Ollama intent.
        """
        if not question or not str(question).strip():
            return None

        raw = str(question).strip()
        nq = self._normalize_text_for_match(raw)

        if not nq:
            return None

        # 1) Exact
        ans = self.memory.get(nq)
        if ans:
            logger.debug(f"✅ [EXACT] '{raw[:60]}...'")
            return ans

        # 2) Short-key exact (handles long duplicated EEO text vs short new label)
        sk = self._short_key(nq)
        if sk and sk != nq and sk in self.memory:
            logger.info(f"✅ [SHORT-KEY] matched stored key via prefix: '{sk[:50]}...'")
            return self.memory[sk]

        # 3) Prefix: short new label vs long stored question (same field)
        if len(nq) >= 12:
            for key, val in self.memory.items():
                if key.startswith(nq):
                    logger.info("✅ [PREFIX] stored question starts with normalized query")
                    return val
        if sk and len(sk) >= 12:
            for key, val in self.memory.items():
                if key.startswith(sk):
                    logger.info("✅ [PREFIX] stored question starts with short-key prefix")
                    return val

        # Stored short key, new question is longer (same leading text)
        for key, val in self.memory.items():
            if len(key) >= 12 and nq.startswith(key):
                logger.info("✅ [PREFIX] query starts with stored question prefix")
                return val

        candidates: List[Tuple[str, int]] = []
        best_fuzzy_score = 0

        if FUZZY_MATCHING_AVAILABLE and self.memory:
            try:
                candidates = process.extract(  # type: ignore
                    nq,
                    list(self.memory.keys()),
                    scorer=fuzz.token_set_ratio,  # type: ignore
                    limit=self._settings.fuzzy_candidate_limit,
                )
            except Exception as e:
                logger.error(f"Fuzzy extract error: {e}")
                candidates = []

        if candidates:
            best_key, best_fuzzy_score = candidates[0][0], int(candidates[0][1])

            if best_fuzzy_score >= self._settings.fuzzy_threshold_high:
                logger.info(
                    f"✅ [FUZZY {best_fuzzy_score}%] '{raw[:40]}...' ~ "
                    f"'{best_key[:40]}...'"
                )
                return self.memory[best_key]

            pool = [
                (k, int(s))
                for k, s in candidates
                if int(s) >= self._settings.fuzzy_threshold_low
            ]
            if not pool:
                pool = candidates[: max(8, min(len(candidates), 12))]
        else:
            # No thefuzz or empty extract: word-overlap candidates only (avoid wrong LLM picks)
            pool = self._word_overlap_pool(nq, self._settings.fuzzy_candidate_limit)
            if not pool:
                logger.debug(f"❌ No word overlap with memory: '{raw[:50]}...'")
                return None

        top_k = min(self._settings.intent_top_k, len(pool))
        pool = pool[:top_k]

        # 5) Embeddings
        if self._settings.embedding_enabled and self._ollama:
            emb_ans = self._lookup_by_embedding(nq, pool)
            if emb_ans is not None:
                return emb_ans

        # 6) Ollama intent
        if self._settings.intent_llm_enabled and self._ollama:
            intent_ans = self._lookup_by_intent_llm(raw, nq, pool)
            if intent_ans is not None:
                return intent_ans

        logger.debug(
            f"❌ No match after tiers (best fuzzy was {best_fuzzy_score}%): '{raw[:50]}...'"
        )
        return None

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        if not self._ollama:
            return None
        key = text[:4000]
        if key in self._embedding_cache:
            return self._embedding_cache[key]
        try:
            vec = list(
                self._ollama.embeddings(key, self._settings.embedding_model)
            )
            self._embedding_cache[key] = vec
            return vec
        except Exception as e:
            logger.warning(f"Embedding failed ({self._settings.embedding_model}): {e}")
            return None

    def _lookup_by_embedding(
        self, normalized_query: str, pool: List[Tuple[str, int]]
    ) -> Optional[str]:
        from src.qa_intent import cosine_similarity

        qvec = self._get_embedding(normalized_query)
        if not qvec:
            return None

        best_key = None
        best_sim = -1.0
        for key, _score in pool:
            kvec = self._get_embedding(key)
            if not kvec:
                continue
            sim = cosine_similarity(qvec, kvec)
            if sim > best_sim:
                best_sim = sim
                best_key = key

        if best_key is not None and best_sim >= self._settings.embedding_threshold:
            logger.info(
                f"✅ [EMBED sim={best_sim:.3f}] matched '{best_key[:50]}...'"
            )
            return self.memory.get(best_key)
        return None

    def _lookup_by_intent_llm(
        self, raw_question: str, normalized_query: str, pool: List[Tuple[str, int]]
    ) -> Optional[str]:
        from src.qa_intent import ollama_pick_question_index

        keys = [k for k, _ in pool]
        if not keys:
            return None

        model = (self._settings.ollama_chat_model or "").strip()
        if not model and self._ollama:
            model = self._ollama.resolve_model() or ""

        if not model:
            logger.debug("Intent LLM skipped: no chat model resolved")
            return None

        try:
            idx = ollama_pick_question_index(
                self._ollama,
                model,
                raw_question,
                keys,
                timeout_seconds=45,
            )
        except Exception as e:
            logger.warning(f"Intent LLM call failed: {e}")
            return None

        if idx is None or idx < 0 or idx >= len(keys):
            return None

        matched = keys[idx]
        # Reject unrelated picks when we can score similarity
        if FUZZY_MATCHING_AVAILABLE and fuzz is not None:
            conf = int(fuzz.token_set_ratio(normalized_query, matched))  # type: ignore
            min_conf = max(35, self._settings.fuzzy_threshold_low - 15)
            if conf < min_conf:
                logger.debug(
                    f"Intent LLM pick rejected (token_set_ratio={conf}% < {min_conf}%): "
                    f"'{matched[:40]}...'"
                )
                return None
        else:
            q_words = {
                w
                for w in re.split(r"\W+", normalized_query)
                if len(w) > 2 and w not in _WORD_STOP
            }
            m_words = {
                w
                for w in re.split(r"\W+", matched)
                if len(w) > 2 and w not in _WORD_STOP
            }
            if len(q_words & m_words) < 2 and len(normalized_query) > 12:
                logger.debug("Intent LLM pick rejected (insufficient word overlap)")
                return None

        logger.info(
            f"✅ [INTENT-LLM] picked candidate {idx}: '{matched[:50]}...'"
        )
        return self.memory.get(matched)

    def learn_answer(self, question: str, answer: str) -> bool:
        """
        Learn a new Q&A pair and save it immediately.
        Prevents duplicates by rewriting the entire CSV.
        """
        try:
            normalized_question = self._normalize_text_for_match(question)

            is_update = normalized_question in self.memory
            self.memory[normalized_question] = answer

            with open(self.memory_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["question_text", "answer_text"])
                for q, a in self.memory.items():
                    writer.writerow([q, a])
                f.flush()

            if is_update:
                logger.info(f"🔄 Updated: '{question[:50]}...' -> '{answer}'")
            else:
                logger.info(f"✅ Learned: '{question[:50]}...' -> '{answer}'")

            return True

        except Exception as e:
            logger.error(f"Failed to save Q&A pair: {e}")
            return False

    def prompt_user_for_answer(self, question: str) -> Tuple[Optional[str], bool]:
        """Prompt user for an answer to an unknown question."""
        print("\n" + "=" * 80)
        print("[MISSING ANSWER] Q&A Memory Gap Detected!")
        print("=" * 80)
        print(f"Question: \"{question}\"")
        print("=" * 80)
        print("\a")

        logger.warning(f"Missing answer for: {question[:50]}...")

        response = input(
            "\n👉 Enter answer for this question (or type 'SKIP' to ignore): "
        ).strip()

        if response.upper() == "SKIP":
            logger.info("User chose to skip this question")
            return None, True

        if not response:
            logger.warning("Empty answer provided, treating as skip")
            return None, True

        return response, False

    def get_memory_stats(self) -> Dict[str, int]:
        """Get statistics about the Q&A memory."""
        return {
            "total_pairs": len(self.memory),
            "file_size_bytes": self.memory_file.stat().st_size
            if self.memory_file.exists()
            else 0,
        }

    def export_memory(self, output_file: str):
        """Export the current memory to a different file."""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["question_text", "answer_text"])

                for question, answer in self.memory.items():
                    writer.writerow([question, answer])

            logger.info(f"Exported {len(self.memory)} Q&A pairs to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export memory: {e}")

    def clear_memory(self):
        """Clear all Q&A pairs from memory (use with caution!)."""
        self.memory.clear()
        logger.warning("Cleared all Q&A pairs from memory (not from file)")

    def reload_memory(self):
        """Reload Q&A pairs from file."""
        self.memory.clear()
        self._embedding_cache.clear()
        self._load_memory()
        logger.info("Reloaded Q&A memory from file")

    def deduplicate_memory(self) -> int:
        """Remove duplicate entries from the CSV file."""
        try:
            original_count = 0
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    original_count = sum(1 for _ in f) - 1
            except Exception:
                pass

            self.reload_memory()

            with open(self.memory_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["question_text", "answer_text"])

                for question, answer in self.memory.items():
                    writer.writerow([question, answer])

            duplicates_removed = original_count - len(self.memory)

            if duplicates_removed > 0:
                logger.info(
                    f"🧹 Deduplication complete: "
                    f"{original_count} entries → {len(self.memory)} unique "
                    f"(removed {duplicates_removed} duplicates)"
                )
            else:
                logger.info(f"✅ No duplicates found ({len(self.memory)} unique entries)")

            return len(self.memory)

        except Exception as e:
            logger.error(f"Failed to deduplicate memory: {e}")
            return len(self.memory)
