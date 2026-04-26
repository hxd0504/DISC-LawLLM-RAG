"""
将 law_rag_sft / law_pair_sft / law_mixed_sft 追加到 LLaMA-Factory 的 dataset_info.json。

用法：
  python finetune/patch_dataset_info.py --llamafactory_root F:\LlamaFactory-main\LlamaFactory-main
  # 或设置环境变量 LLAMAFACTORY_ROOT，不传参数
"""
import json
import shutil
import argparse
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

NEW_ENTRIES = {
    "law_rag_sft":   {"file_name": str(DATA_DIR / "law_rag_sft.json").replace("\\", "/")},
    "law_pair_sft":  {"file_name": str(DATA_DIR / "law_pair_sft.json").replace("\\", "/")},
    "law_mixed_sft": {"file_name": str(DATA_DIR / "law_mixed_sft.json").replace("\\", "/")},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llamafactory_root", default=os.getenv("LLAMAFACTORY_ROOT", ""))
    args = parser.parse_args()

    root = Path(args.llamafactory_root)
    if not root.exists():
        raise SystemExit(f"LLAMAFACTORY_ROOT not found: {root}\n"
                         "请传入 --llamafactory_root 或设置环境变量 LLAMAFACTORY_ROOT")

    info_path = root / "data" / "dataset_info.json"
    bak_path  = info_path.with_suffix(".json.bak")

    shutil.copy2(info_path, bak_path)
    print(f"备份 → {bak_path}")

    with open(info_path, encoding="utf-8") as f:
        info = json.load(f)

    for k, v in NEW_ENTRIES.items():
        if k in info:
            print(f"已存在，跳过: {k}")
        else:
            info[k] = v
            print(f"追加: {k} → {v['file_name']}")

    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print("完成。")


if __name__ == "__main__":
    main()
