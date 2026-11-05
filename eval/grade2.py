#!/usr/bin/env python3
"""Grade harder-round solutions. Usage: python3 -I grade2.py <h1|h2|h3|h4> <file>
Prints JSON: {"problem","passed","total","ok","error"}. Efficiency limits via alarm."""
import json, signal, sys, types


def load(path, name):
    src = open(path, encoding="utf-8").read()
    mod = types.ModuleType("sol")
    exec(compile(src, path, "exec"), mod.__dict__)
    fn = mod.__dict__.get(name)
    if not callable(fn):
        raise ValueError(f"{name}() not found")
    return fn


def norm_intervals(x):
    return sorted([list(p) for p in x])


def grade_h1(fn):
    cases = [
        ([[1, 3], [2, 6], [8, 10], [15, 18]], [[1, 6], [8, 10], [15, 18]]),
        ([[1, 4], [4, 5]], [[1, 5]]),
        ([[1, 4], [0, 4]], [[0, 4]]),
        ([[1, 4], [2, 3]], [[1, 4]]),
        ([], []),
        ([[1, 4], [5, 6]], [[1, 4], [5, 6]]),
    ]
    return [norm_intervals(fn([list(i) for i in a])) == norm_intervals(e) for a, e in cases]


def grade_h2(fn):
    cases = [
        (["2", "1", "+", "3", "*"], 9),
        (["4", "13", "5", "/", "+"], 6),
        (["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"], 22),
        (["-7", "2", "/"], -3),   # truncate toward zero, not floor(-4)
        (["7", "-3", "/"], -2),   # truncate toward zero
    ]
    return [fn(list(a)) == e for a, e in cases]


def grade_h3(fn):
    import random
    out = []
    fixed = [("babad", 3), ("cbbd", 2), ("a", 1), ("", 0), ("forgeeksskeegfor", 10)]
    for s, exp_len in fixed:
        r = fn(s)
        ok = (isinstance(r, str) and r in s and r == r[::-1] and len(r) == exp_len)
        out.append(ok)
    # efficiency: long all-same string, must return whole string within alarm
    big = "a" * 2000
    out.append(fn(big) == big)
    return out


def grade_h4(fn):
    # corrected binary search on sorted array -> index or -1
    arr = [1, 3, 5, 7, 9, 11]
    cases = [((arr, 1), 0), ((arr, 11), 5), ((arr, 7), 3), ((arr, 4), -1),
             (([42], 42), 0), (([42], 7), -1), (([], 5), -1)]
    out = []
    for (a, t), e in cases:
        try:
            out.append(fn(list(a), t) == e)
        except Exception:
            out.append(False)
    return out


GRADERS = {"h1": ("merge_intervals", grade_h1), "h2": ("eval_rpn", grade_h2),
           "h3": ("longest_palindromic_substring", grade_h3), "h4": ("bsearch", grade_h4)}


def main():
    pid, path = sys.argv[1], sys.argv[2]
    name, grader = GRADERS[pid]
    out = {"problem": pid, "passed": 0, "total": 0, "ok": False, "error": ""}
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError("time limit")))
    try:
        fn = load(path, name)
        signal.alarm(4)
        results = grader(fn)
        signal.alarm(0)
        out["passed"] = sum(1 for r in results if r)
        out["total"] = len(results)
        out["ok"] = out["passed"] == out["total"]
    except Exception as e:
        signal.alarm(0)
        out["error"] = f"{type(e).__name__}: {e}"[:80]
    print(json.dumps(out))


if __name__ == "__main__":
    main()
