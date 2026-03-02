#!/usr/bin/env python3
"""
Quick test: load config, create AI answerer, call get_smart_answer.
Run from project root: python test_ai_answer.py
Verifies OPENAI_API_KEY is loaded and AI form-filling path works.
"""
import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def main():
    from src.config import Config
    from src.application import AIQuestionAnswerer

    print("1. Loading config (reads .env from project root)...")
    try:
        config = Config("config.yaml")
    except Exception as e:
        print(f"   FAIL: {e}")
        return 1
    print(f"   OK: user={config.username[:3]}***")

    print("2. Checking OPENAI_API_KEY...")
    key = config.openai_api_key
    if not key or not key.strip():
        print("   FAIL: OPENAI_API_KEY is empty. Set it in .env")
        return 1
    print(f"   OK: key present ({key[:7]}...{key[-4:] if len(key) > 11 else '***'})")

    print("3. Creating AIQuestionAnswerer...")
    answerer = AIQuestionAnswerer(key)
    if not answerer.client:
        print("   FAIL: OpenAI client is None (check key / openai package)")
        return 1
    print("   OK: client initialized")

    print("4. Calling get_smart_answer (text field, no options)...")
    ctx = {"salary": 100000, "rate": 50}
    answer = answerer.get_smart_answer(
        "How many years of Python experience do you have?",
        context=ctx,
        input_type="text",
        options=[],
    )
    if answer is None:
        print("   WARN: AI returned None (no resume or uncertain)")
    else:
        print(f"   OK: answer = {repr(answer)}")

    print("5. Calling get_smart_answer (checkbox: should box be checked?)...")
    answer2 = answerer.get_smart_answer(
        "Do you have 5+ years of Python experience?",
        context=ctx,
        input_type="checkbox",
        options=["Yes", "No"],
    )
    if answer2 is None:
        print("   WARN: AI returned None")
    else:
        print(f"   OK: answer = {repr(answer2)} (expect 'yes' or 'no')")

    print("\nAll checks passed. AI form-filling path is working.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
