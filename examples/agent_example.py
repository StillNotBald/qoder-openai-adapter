#!/usr/bin/env python3
"""Minimal 'wire it into your agent' example — a QA/code-review call.

No third-party deps. Points at the local shim exactly like any OpenAI client
would. Start the shim first (npm start), then: python3 examples/agent_example.py
"""
import json
import os
import urllib.request

BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8787/v1")
API_KEY = os.environ.get("OPENAI_API_KEY", "unused")       # SHIM_API_KEY if you set one
MODEL = os.environ.get("MODEL", "qfmodel")                  # free Qwen3.8-Flash


def chat(messages, model=MODEL):
    body = json.dumps({"model": model, "messages": messages}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=body,
        headers={"content-type": "application/json", "authorization": f"Bearer {API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # Example QA task: review a function for bugs.
    code = (
        "def average(nums):\n"
        "    total = 0\n"
        "    for n in nums:\n"
        "        total += n\n"
        "    return total / len(nums)\n"
    )
    answer = chat([
        {"role": "system", "content": "You are a code reviewer. Be terse."},
        {"role": "user", "content": f"Review this function. Name any bug in one line.\n\n{code}"},
    ])
    print(answer)
