#!/usr/bin/env python3
"""pass@k for Qwen-Flash via the shim. Saves qwen_<pid>_<k>.py for each attempt."""
import json, re, sys, time, urllib.request

SHIM = "http://127.0.0.1:8787/v1/chat/completions"
OUT = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
PROMPTS = json.load(open(f"{OUT}/prompts2.json"))


def extract(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def ask(prompt):
    body = json.dumps({"model": "qfmodel", "messages": [
        {"role": "system", "content": "You are a terse coding assistant. Output only a python code block."},
        {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(SHIM, data=body, headers={"content-type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return extract(data["choices"][0]["message"]["content"]), time.time() - t0


def main():
    timings = []
    for pid, prompt in PROMPTS.items():
        for k in range(1, K + 1):
            try:
                code, dt = ask(prompt)
                open(f"{OUT}/qwen_{pid}_{k}.py", "w").write(code + "\n")
                timings.append(dt)
                print(f"qwen {pid} attempt {k}: {dt:.2f}s")
            except Exception as e:
                open(f"{OUT}/qwen_{pid}_{k}.py", "w").write("# ERROR\n")
                print(f"qwen {pid} attempt {k}: ERROR {e}")
    if timings:
        print(f"[qwen] avg {sum(timings)/len(timings):.2f}s over {len(timings)} calls")


if __name__ == "__main__":
    main()
