#!/usr/bin/env python3
"""Grade a model-generated solution file against hidden tests.

Usage: python3 -I grade.py <problem_id> <solution_file>
Prints one JSON line: {"problem","passed","total","ok","error"}
Runs with a wall-clock alarm so a pathological solution can't hang the harness.
"""
import json
import signal
import sys
import types

CASES = {
    "p1": {  # is_palindrome(s) -> bool, ignore case + non-alphanumerics
        "func": "is_palindrome",
        "cases": [
            (("A man, a plan, a canal: Panama",), True),
            (("race a car",), False),
            (("",), True),
            (("Was it a car or a cat I saw?",), True),
            (("0P",), False),
        ],
        "cmp": "eq",
    },
    "p2": {  # two_sum(nums, target) -> two distinct indices summing to target
        "func": "two_sum",
        "cases": [
            (([2, 7, 11, 15], 9), None),
            (([3, 2, 4], 6), None),
            (([3, 3], 6), None),
            (([-1, -2, -3, -4, -5], -8), None),
        ],
        "cmp": "two_sum",
    },
    "p3": {  # trailing_zeros_factorial(n) -> count of trailing zeros in n!
        "func": "trailing_zeros_factorial",
        "cases": [
            ((5,), 1), ((10,), 2), ((25,), 6), ((3,), 0),
            ((0,), 0), ((100,), 24), ((1000,), 249),
        ],
        "cmp": "eq",
    },
}


def load_func(path, name):
    src = open(path, "r", encoding="utf-8").read()
    mod = types.ModuleType("sol")
    mod.__dict__["__name__"] = "sol"
    exec(compile(src, path, "exec"), mod.__dict__)
    fn = mod.__dict__.get(name)
    if not callable(fn):
        raise ValueError(f"function {name}() not found")
    return fn


def check(cmp, args, expected, got):
    if cmp == "eq":
        return got == expected
    if cmp == "two_sum":
        nums, target = args
        try:
            i, j = got
        except Exception:
            return False
        return i != j and 0 <= i < len(nums) and 0 <= j < len(nums) and nums[i] + nums[j] == target
    return False


def main():
    pid, path = sys.argv[1], sys.argv[2]
    spec = CASES[pid]
    out = {"problem": pid, "passed": 0, "total": len(spec["cases"]), "ok": False, "error": ""}

    def on_alarm(signum, frame):
        raise TimeoutError("solution exceeded time limit")

    signal.signal(signal.SIGALRM, on_alarm)
    try:
        fn = load_func(path, spec["func"])
        for args, expected in spec["cases"]:
            signal.alarm(5)
            try:
                got = fn(*args)
                if check(spec["cmp"], args, expected, got):
                    out["passed"] += 1
            except Exception as e:
                out["error"] = f"runtime: {type(e).__name__}: {e}"
            finally:
                signal.alarm(0)
        out["ok"] = out["passed"] == out["total"]
    except Exception as e:
        out["error"] = f"load: {type(e).__name__}: {e}"
    print(json.dumps(out))


if __name__ == "__main__":
    main()
