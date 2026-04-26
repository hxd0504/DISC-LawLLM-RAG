"""
推理对比评测：Base Qwen2.5-7B-Instruct vs LoRA RAG-SFT adapter
用法：
  python finetune/eval_lora_outputs.py
输出：
  finetune/eval/lora_eval_outputs.jsonl
  finetune/eval/lora_eval_review.csv
"""
import json
import csv
import random
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# ── 路径配置 ──────────────────────────────────────────────────────────────────
BASE_MODEL   = "Qwen/Qwen2.5-7B-Instruct"
ADAPTER_PATH = r"F:\pythoncode\大模型项目\DISC-LawLLM\DISC-LawLLM-main\DISC-LawLLM-main\saves\qwen2.5-7b\lora\law_rag_sft_5k\checkpoint-200"
DATA_FILE    = Path("finetune/data/law_rag_sft.json")
OUT_DIR      = Path("finetune/eval")
N_SAMPLES    = 50
SEED         = 42

SYSTEM_PROMPT = "你是一个专业的法律助手，请根据给定法律依据准确回答问题。"

# ── 推理工具 ──────────────────────────────────────────────────────────────────
def build_prompt(tokenizer, instruction: str, inp: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"{instruction}\n{inp}"},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def generate(model, tokenizer, prompt: str, max_new_tokens: int = 512) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
        )
    new_tokens = out[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 采样
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    random.seed(SEED)
    samples = random.sample(data, N_SAMPLES)

    # 加载 tokenizer & base model
    print("Loading base model...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )
    base_model.eval()

    # 加载 LoRA adapter
    print("Loading LoRA adapter...")
    lora_model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    lora_model.eval()

    # 推理
    results = []
    for i, s in enumerate(samples):
        print(f"[{i+1}/{N_SAMPLES}]", end="\r")
        prompt = build_prompt(tokenizer, s["instruction"], s["input"])

        # base：禁用 adapter
        with lora_model.disable_adapter():
            base_ans = generate(base_model, tokenizer, prompt)

        # lora
        lora_ans = generate(lora_model, tokenizer, prompt)

        # 拆分 reference 和 question（input 格式：法律依据\n\n问题）
        parts = s["input"].split("\n\n", 1)
        reference = parts[0] if len(parts) == 2 else ""
        question  = parts[1] if len(parts) == 2 else s["input"]

        results.append({
            "sample_id":   i,
            "reference":   reference,
            "question":    question,
            "gold_answer": s["output"],
            "base_answer": base_ans,
            "lora_answer": lora_ans,
        })

    # 保存 JSONL
    out_jsonl = OUT_DIR / "lora_eval_outputs.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(results)} results → {out_jsonl}")

    # 生成人工评审 CSV（空白待填写）
    out_csv = OUT_DIR / "lora_eval_review.csv"
    fields = ["sample_id", "question_preview",
              "cite_law(0/1)", "no_hallucination(0/1)", "answer_core(0/1)",
              "format_clarity(1-5)", "overall_score(1-5)", "notes"]
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({
                "sample_id":       r["sample_id"],
                "question_preview": r["question"][:60].replace("\n", " "),
                "cite_law(0/1)":    "",
                "no_hallucination(0/1)": "",
                "answer_core(0/1)": "",
                "format_clarity(1-5)": "",
                "overall_score(1-5)": "",
                "notes": "",
            })
    print(f"Saved review sheet → {out_csv}")


if __name__ == "__main__":
    main()
