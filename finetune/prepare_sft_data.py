"""
将 DISC-Law-SFT 数据转换为 LLaMA-Factory alpaca 格式。

用法：
  python finetune/prepare_sft_data.py --mode rag_triplet --max_samples 5000
  python finetune/prepare_sft_data.py --mode pair_qa
  python finetune/prepare_sft_data.py --mode mixed --max_samples 10000
"""
import json
import random
import argparse
from pathlib import Path

TRIPLET_FILE = "data/DISC-Law-SFT/DISC-Law-SFT-Triplet-released.jsonl"
PAIR_FILE    = "data/DISC-Law-SFT/DISC-Law-SFT-Pair-QA-released.jsonl"
OUT_DIR      = Path("finetune/data")

RAG_INSTRUCTION  = "请根据给定法律依据回答问题。"
PAIR_INSTRUCTION = "请回答以下法律问题。"


def load_triplet(max_samples=None, seed=42):
    samples = []
    with open(TRIPLET_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            refs = rec.get("reference", [])
            ref_text = "\n".join(f"【法律依据】{r}" for r in refs if r.strip())
            question = rec.get("input", "").strip()
            answer   = rec.get("output", "").strip()
            if not question or not answer:
                continue
            inp = f"{ref_text}\n\n{question}" if ref_text else question
            samples.append({"instruction": RAG_INSTRUCTION, "input": inp, "output": answer})
    if max_samples and len(samples) > max_samples:
        random.seed(seed)
        samples = random.sample(samples, max_samples)
    return samples


def load_pair(max_samples=None, seed=42):
    samples = []
    with open(PAIR_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            question = rec.get("input", "").strip()
            answer   = rec.get("output", "").strip()
            if not question or not answer:
                continue
            samples.append({"instruction": PAIR_INSTRUCTION, "input": question, "output": answer})
    if max_samples and len(samples) > max_samples:
        random.seed(seed)
        samples = random.sample(samples, max_samples)
    return samples


def save(samples, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)
    print(f"saved {len(samples)} samples → {path}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["rag_triplet", "pair_qa", "mixed"], default="rag_triplet")
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--triplet_ratio", type=float, default=0.7, help="mixed 模式下 triplet 占比")
    args = parser.parse_args()

    if args.mode == "rag_triplet":
        samples = load_triplet(args.max_samples)
        save(samples, "law_rag_sft")

    elif args.mode == "pair_qa":
        samples = load_pair(args.max_samples)
        save(samples, "law_pair_sft")

    elif args.mode == "mixed":
        n = args.max_samples
        n_triplet = int(n * args.triplet_ratio) if n else None
        n_pair    = (n - n_triplet) if n else None
        triplet = load_triplet(n_triplet)
        pair    = load_pair(n_pair)
        samples = triplet + pair
        random.shuffle(samples)
        if n:
            samples = samples[:n]
        save(samples, "law_mixed_sft")


if __name__ == "__main__":
    main()
