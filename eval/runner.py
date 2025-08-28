from __future__ import annotations
import json, os
from llm import ask_llm_full

DATA = os.path.join(os.path.dirname(__file__), "datasets", "example.jsonl")

def run_eval():
    if not os.path.exists(DATA):
        print("No dataset found.")
        return
    good = 0; total = 0
    with open(DATA, "r", encoding="utf-8") as f:
        for line in f:
            total += 1
            row = json.loads(line)
            q = row.get("question","")
            gold = row.get("gold","").lower()
            out = ask_llm_full(q) or ""
            ans = out.split("assistant\n",1)[-1].strip().lower() if "assistant\n" in out else out.strip().lower()
            if gold and gold in ans:
                good += 1
    print(f"Eval done: {good}/{total} matched substring.")
if __name__ == "__main__":
    run_eval()
