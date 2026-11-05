#!/usr/bin/env python3
"""Capped rate-limit probe for the free model via the shim.
Fires a bounded number of tiny calls (sequential + one concurrent burst) and
reports successes, failures, any rate-limit signal, and achievable throughput.
Intentionally small so it does not abuse the account."""
import concurrent.futures as cf
import json, time, urllib.error, urllib.request

SHIM = "http://127.0.0.1:8787/v1/chat/completions"
SEQ_N = 25      # sequential calls
BURST_N = 10    # simultaneous calls


def call(i):
    body = json.dumps({"model": "qfmodel",
                       "messages": [{"role": "user", "content": "Reply with just: ok"}]}).encode()
    req = urllib.request.Request(SHIM, data=body, headers={"content-type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        txt = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        err = d.get("error")
        return {"i": i, "ok": err is None, "dt": time.time() - t0,
                "err": (err or {}).get("message", "") if err else "", "len": len(txt)}
    except urllib.error.HTTPError as e:
        return {"i": i, "ok": False, "dt": time.time() - t0, "err": f"HTTP{e.code}", "len": 0}
    except Exception as e:
        return {"i": i, "ok": False, "dt": time.time() - t0, "err": str(e)[:60], "len": 0}


def main():
    print(f"=== sequential x{SEQ_N} ===")
    seq = []
    t0 = time.time()
    for i in range(SEQ_N):
        r = call(i)
        seq.append(r)
        flag = "ok" if r["ok"] else f"FAIL({r['err']})"
        print(f"  {i:2d}: {r['dt']:.2f}s {flag}")
        if not r["ok"] and ("429" in r["err"] or "limit" in r["err"].lower() or "quota" in r["err"].lower()):
            print("  >> rate/quota limit hit; stopping sequential early")
            break
    seq_wall = time.time() - t0
    ok_seq = sum(1 for r in seq if r["ok"])
    print(f"sequential: {ok_seq}/{len(seq)} ok in {seq_wall:.1f}s "
          f"= {ok_seq/seq_wall*60:.0f} ok-calls/min")

    print(f"=== concurrent burst x{BURST_N} ===")
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=BURST_N) as ex:
        burst = list(ex.map(call, range(BURST_N)))
    burst_wall = time.time() - t0
    ok_b = sum(1 for r in burst if r["ok"])
    errs = {}
    for r in burst:
        if not r["ok"]:
            errs[r["err"]] = errs.get(r["err"], 0) + 1
    print(f"concurrent: {ok_b}/{BURST_N} ok in {burst_wall:.1f}s; errors={errs or 'none'}")

    total_ok = ok_seq + ok_b
    print(f"\nSUMMARY: {total_ok} successful free calls, "
          f"{len(seq)+BURST_N-total_ok} failures. "
          f"{'NO explicit rate-limit error seen.' if not any('429' in (r['err']) or 'limit' in r['err'].lower() for r in seq+burst) else 'Rate/quota limit observed.'}")


if __name__ == "__main__":
    main()
