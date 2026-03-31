#!/usr/bin/env python3
"""
Smoke test for local LLM answering via Ollama.

This does NOT touch LinkedIn; it only:
1) Loads Config (.env + config.yaml)
2) Instantiates AIQuestionAnswerer (Ollama provider)
3) Calls get_smart_answer for checkbox/select cases
"""

import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_root))

    from src.config import Config
    from src.application import AIQuestionAnswerer

    print("Loading configuration...")
    config = Config("config.yaml")

    provider = getattr(config, "ai_provider_name", "ollama")
    print(f"AI provider configured: {provider}")

    print("Initializing AIQuestionAnswerer...")
    answerer = AIQuestionAnswerer(config=config)

    print(f"LLM enabled: {answerer.llm_enabled} (provider={answerer.provider})")
    if not answerer.llm_enabled:
        print("Ollama not reachable / model not resolved. Skipping smoke test.")
        return 0

    resume_len = len((answerer.resume_text or "").strip())
    print(f"Resume text loaded length: {resume_len}")
    if resume_len < 50:
        print("WARNING: Resume text seems empty/too short; JSON/PDF resume loading may not be working.")

    ctx = {"salary": 160000, "rate": 60}

    print("\nCheckbox test (expect 'yes' or 'no')...")
    out1 = answerer.get_smart_answer(
        "Do you have 5+ years of Python experience?",
        context=ctx,
        input_type="checkbox",
        options=["Yes", "No"],
    )
    print(f"Result: {out1!r}")
    if out1 is not None and out1.lower() not in ("yes", "no"):
        print("WARNING: Checkbox result not normalized to yes/no.")

    print("\nSelect test (expect non-empty option-like string)...")
    out2 = answerer.get_smart_answer(
        "Which seniority best matches you?",
        context=ctx,
        input_type="select",
        options=["Associate", "Mid-Senior level", "Director", "Executive"],
    )
    print(f"Result: {out2!r}")
    if out2 is None:
        print("WARNING: Select result was None.")

    print("\nSmoke test finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

