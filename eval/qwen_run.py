#!/usr/bin/env python3
"""Call the local shim (Qwen-Flash) for each problem, extract code, save, time it."""
import json
import re
import time
import urllib.request

SHIM = "http://127.0.0.1:8787/v1/chat/completions"
OUT = __import__("os").path.dirname(__import__("os").path.abspath(__file__))

PROMPTS = {
    "p1": "Write a Python function `is_palindrome(s)` that returns True if the string is a palindrome considering only alphanumeric characters and ignoring case. Return ONLY a python code block.",
    "p2": "Write a Python function `two_sum(nums, target)` that returns a list of two distinct indices whose values sum to target (assume exactly one solution exists). Return ONLY a python code block.",
    "p3": "Write a Python function `trailing_zeros_factorial(n)` that returns the number of trailing zeros in n! (n factorial). It must work efficiently for n up to 1,000,000,000 (do not actually compute the factorial). Return ONLY a python code block.",
}


def extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def ask(prompt):
    body = json.dumps({
        "model": "qfmodel",
        "messages": [
            {"role": "system", "content": "You are a terse coding assistant. Output only a python code block."},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    req = urllib.request.Request(SHIM, data=body, headers={"content-type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    dt = time.time() - t0
    content = data["choices"][0]["message"]["content"]
    return content, dt


def main():
    timings = {}
    for pid, prompt in PROMPTS.items():
        try:
            content, dt = ask(prompt)
            code = extract_code(content)
            with open(f"{OUT}/qwen_{pid}.py", "w") as f:
                f.write(code + "\n")
            timings[pid] = round(dt, 2)
            print(f"qwen {pid}: {dt:.2f}s, {len(code)} chars")
        except Exception as e:
            timings[pid] = None
            print(f"qwen {pid}: ERROR {e}")
    with open(f"{OUT}/qwen_timings.json", "w") as f:
        json.dump(timings, f)


if __name__ == "__main__":
    main()
