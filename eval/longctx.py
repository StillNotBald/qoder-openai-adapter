#!/usr/bin/env python3
"""Long-context needle test — showcases qfmodel's huge free context window and
discriminates models that lose the thread in long inputs.

Builds N item records with two planted 'needles', writes the full prompt to a
file, asks for the sum of the two needle values, and (for Qwen) calls the shim.
Claude models can be pointed at the same longctx_prompt.txt via a subagent Read.

Usage: python3 -I longctx.py <approx_tokens> [run_qwen]
"""
import json, os, random, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SHIM = "http://127.0.0.1:8787/v1/chat/completions"
APPROX_TOKENS = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
RUN_QWEN = len(sys.argv) > 2 and sys.argv[2] == "run_qwen"

random.seed(7)
# ~4 chars/token; each record ~ 40 chars -> ~10 tokens
n_records = max(50, APPROX_TOKENS // 10)
alpha_val = random.randint(1000, 9999)
omega_val = random.randint(1000, 9999)
answer = alpha_val + omega_val
alpha_pos = random.randint(int(n_records * 0.15), int(n_records * 0.35))
omega_pos = random.randint(int(n_records * 0.65), int(n_records * 0.85))

lines = []
for i in range(n_records):
    if i == alpha_pos:
        lines.append(f"Record {i:05d}: ITEM_ALPHA has secret_value = {alpha_val}.")
    elif i == omega_pos:
        lines.append(f"Record {i:05d}: ITEM_OMEGA has secret_value = {omega_val}.")
    else:
        lines.append(f"Record {i:05d}: item_{random.randint(0,99999)} has secret_value = {random.randint(1,999)}.")

body_text = "\n".join(lines)
question = ("You are given many records below. Find the secret_value of ITEM_ALPHA and the "
            "secret_value of ITEM_OMEGA, add them together, and output ONLY that integer sum "
            "(no words, no explanation).\n\n=== RECORDS ===\n")
prompt = question + body_text + "\n=== END ===\n"

open(os.path.join(HERE, "longctx_prompt.txt"), "w").write(prompt)
open(os.path.join(HERE, "longctx_answer.txt"), "w").write(str(answer))
approx_tok = len(prompt) // 4
print(f"built: {n_records} records, ~{approx_tok} tokens, answer={answer} "
      f"(ALPHA={alpha_val}@{alpha_pos}, OMEGA={omega_val}@{omega_pos})")
print(f"prompt file: {os.path.join(HERE, 'longctx_prompt.txt')}")


def ask_qwen(text):
    b = json.dumps({"model": "qfmodel", "messages": [{"role": "user", "content": text}]}).encode()
    req = urllib.request.Request(SHIM, data=b, headers={"content-type": "application/json"})
    import time
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"], time.time() - t0


if RUN_QWEN:
    try:
        out, dt = ask_qwen(prompt)
        import re
        nums = re.findall(r"-?\d+", out.replace(",", ""))
        got = nums[-1] if nums else ""
        ok = str(answer) in nums
        print(f"QWEN qfmodel: {dt:.1f}s  raw={out.strip()[:80]!r}  parsed={got}  "
              f"{'CORRECT' if ok else 'WRONG (want ' + str(answer) + ')'}")
    except Exception as e:
        print(f"QWEN error: {e}")
