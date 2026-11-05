#!/usr/bin/env python3
"""Multi-HOP long-context test — the real discriminator.
Two reference chains (ALPHA, OMEGA), each HOPS deep, scattered through a large
filler context. The model must follow each chain pointer-by-pointer to its final
value, then sum the two. Single-hop retrieval won't solve it.

Usage: python3 -I longctx_multihop.py <approx_tokens> [run_qwen]
"""
import json, os, random, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SHIM = "http://127.0.0.1:8787/v1/chat/completions"
APPROX = int(sys.argv[1]) if len(sys.argv) > 1 else 180000
RUN_QWEN = len(sys.argv) > 2 and sys.argv[2] == "run_qwen"
HOPS = 4
random.seed(21)

n = max(200, APPROX // 12)


def key():
    return "K" + "".join(random.choice("0123456789ABCDEF") for _ in range(6))


def build_chain(name):
    keys = [key() for _ in range(HOPS)]
    final = random.randint(1000, 9999)
    recs = []
    # entry: names the item, points to first key
    recs.append(f"ITEM_{name}: to resolve, go to the record with key={keys[0]}.")
    # middle hops
    for h in range(HOPS - 1):
        recs.append(f"The record with key={keys[h]}: continue to the record with key={keys[h+1]}.")
    # final
    recs.append(f"The record with key={keys[-1]}: the final value here is {final}.")
    return recs, final


alpha_recs, alpha_val = build_chain("ALPHA")
omega_recs, omega_val = build_chain("OMEGA")
answer = alpha_val + omega_val

special = alpha_recs + omega_recs
fillers = [f"The record with key={key()}: miscellaneous note {random.randint(1,999999)}."
           for _ in range(max(0, n - len(special)))]
all_recs = fillers[:]
# scatter special records at distinct random positions
for rec in special:
    all_recs.insert(random.randint(0, len(all_recs)), rec)

numbered = [f"Record {i:05d}. {r}" for i, r in enumerate(all_recs)]
question = (
    "Below are many records. There are two reference chains to resolve.\n"
    "1) Find the record mentioning ITEM_ALPHA. It tells you another record's key. Go to that "
    "record; it points to the next key; keep following until a record says 'the final value here "
    "is N'. That N is ALPHA's value.\n"
    "2) Do the same starting from the record mentioning ITEM_OMEGA to get OMEGA's value.\n"
    "Output ONLY the integer sum (ALPHA value + OMEGA value), nothing else.\n\n=== RECORDS ===\n")
prompt = question + "\n".join(numbered) + "\n=== END ===\n"

open(os.path.join(HERE, "mhop_prompt.txt"), "w").write(prompt)
open(os.path.join(HERE, "mhop_answer.txt"), "w").write(str(answer))
print(f"built: {len(all_recs)} records, ~{len(prompt)//4} tokens, {HOPS} hops/chain, "
      f"answer={answer} (ALPHA={alpha_val}, OMEGA={omega_val})")


def ask_qwen(text):
    b = json.dumps({"model": "qfmodel", "messages": [{"role": "user", "content": text}]}).encode()
    req = urllib.request.Request(SHIM, data=b, headers={"content-type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"], time.time() - t0


if RUN_QWEN:
    try:
        out, dt = ask_qwen(prompt)
        nums = re.findall(r"-?\d+", out.replace(",", ""))
        ok = str(answer) in nums
        print(f"QWEN qfmodel: {dt:.1f}s  raw={out.strip()[:100]!r}  "
              f"{'CORRECT' if ok else 'WRONG (want ' + str(answer) + ')'}")
    except Exception as e:
        print(f"QWEN error: {e}")
