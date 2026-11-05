# eval — model comparison harness

Grade any OpenAI-compatible model on coding tasks with hidden test cases.

- `grade.py <p1|p2|p3> <file>` — simple round (palindrome, two-sum, factorial zeros)
- `grade2.py <h1|h2|h3|h4> <file>` — harder round (merge-intervals, RPN w/ trunc-toward-zero,
  longest-palindrome w/ efficiency gate, binary-search bug-fix)
- `qwen_run.py` / `qwen_run2.py [k]` — call the local shim (default model) and save each
  attempt for grading; `qwen_run2.py 5` does pass@5.
- `prompts2.json` — the harder-round prompts (shared across all models).

Point other models at the same prompts (via a Claude Code subagent, the Claude API,
or any OpenAI endpoint), drop their output into `<model>_<problem>.py`, and run the grader.

Model outputs (`*_p*.py`, `*_h*.py`, `*.json`) are gitignored.
