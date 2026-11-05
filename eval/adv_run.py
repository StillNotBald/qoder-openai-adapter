#!/usr/bin/env python3
"""Run adversarial trap tasks against a model via the shim and auto-check.
Reads adv_tasks.json (array of {id,category,prompt,expected,check}).
Usage: python3 -I adv_run.py [model]   (default qfmodel)
"""
import json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SHIM = "http://127.0.0.1:8787/v1/chat/completions"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qfmodel"
tasks = json.load(open(os.path.join(HERE, "adv_tasks.json")))


def ask(prompt):
    b = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(SHIM, data=b, headers={"content-type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"].strip(), time.time() - t0


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower()).strip(" .!?\"'")


def check(kind, expected, got):
    if kind == "numeric":
        g = re.findall(r"-?\d+\.?\d*", got.replace(",", ""))
        return bool(g) and any(abs(float(x) - float(expected)) < 1e-6 for x in g)
    if kind == "contains":
        return norm(expected) in norm(got)
    return norm(expected) == norm(got)  # exact


def main():
    print(f"model={MODEL}  tasks={len(tasks)}")
    passed = 0
    for t in tasks:
        try:
            out, dt = ask(t["prompt"])
            ok = check(t.get("check", "exact"), str(t["expected"]), out)
        except Exception as e:
            out, dt, ok = f"ERROR {e}", 0, False
        passed += ok
        print(f"[{t['id']} {t.get('category','')[:18]:18}] {'PASS' if ok else 'FAIL'} "
              f"({dt:.1f}s) want={t['expected']!r} got={out[:60]!r}")
    print(f"\n{MODEL}: {passed}/{len(tasks)} adversarial tasks passed")


if __name__ == "__main__":
    main()
