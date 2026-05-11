import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

files = [
    "content/phase1/ch03_market_basics/exercises.json",
    "content/phase2/ch04_ddb_intro/exercises.json",
    "content/phase2/ch05_ddb_table/exercises.json",
    "content/phase2/ch06_ddb_sql/exercises.json",
    "content/phase2/ch07_ddb_lang/exercises.json",
    "content/phase5/ch16_risk_management/exercises.json",
    "content/phase5/ch17_ddb_backtest/exercises.json",
]


def fix_json(raw: str) -> str:
    """Replace content double quotes with Unicode curly quotes."""
    result = []
    i = 0
    quote_pair = 0
    while i < len(raw):
        ch = raw[i]
        if ch == '"':
            prev = raw[i - 1] if i > 0 else ""
            nxt = raw[i + 1] if i + 1 < len(raw) else ""

            if prev == "\\":
                result.append(ch)
                i += 1
                continue

            if prev in ("", " ", "\n", "\t", "{", "[", ",", ":") or nxt in (
                " ",
                "\n",
                "\t",
                "}",
                "]",
                ",",
                ":",
            ):
                result.append(ch)
                i += 1
                continue

            quote_pair += 1
            if quote_pair % 2 == 1:
                result.append("\u201c")
            else:
                result.append("\u201d")
            i += 1
            continue
        result.append(ch)
        i += 1
    return "".join(result)


for rel_path in files:
    full = os.path.join(BASE, rel_path)
    with open(full, "r", encoding="utf-8") as f:
        raw = f.read()

    fixed = fix_json(raw)

    try:
        data = json.loads(fixed)
        with open(full, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"FIXED: {rel_path}")
    except json.JSONDecodeError as e:
        print(f"FAILED: {rel_path} - line {e.lineno} col {e.colno}")
        lines = fixed.split("\n")
        for li in range(max(0, e.lineno - 3), min(len(lines), e.lineno + 2)):
            print(f"  L{li + 1}: {lines[li][:120]}")

print("Done!")
