# LegalRAG-Qwen2.5 微调模块

基于 DISC-Law-SFT 数据集，使用 LLaMA-Factory 对 Qwen2.5-7B-Instruct 进行 LoRA SFT。

## 目录结构

```
finetune/
├── prepare_sft_data.py       # 数据转换脚本
├── data/                     # 生成的训练数据（不上传）
├── configs/
│   ├── qwen25_7b_lora_rag_sft.yaml    # RAG-SFT LoRA（优先）
│   ├── qwen25_7b_lora_pair_sft.yaml   # Pair-QA LoRA（对照）
│   ├── qwen25_7b_lora_mixed_sft.yaml  # Mixed LoRA
│   └── qwen25_7b_merge_lora.yaml      # Merge adapter
└── scripts/
    ├── train_rag_lora.ps1
    ├── train_pair_lora.ps1
    ├── train_mixed_lora.ps1
    └── merge_lora.ps1
```

## 优先级

1. **RAG-SFT 5K LoRA** — 跑通完整流程（数据→训练→保存→merge→推理）
2. **RAG-SFT 39K LoRA** — 扩展到完整 Triplet 数据
3. **Pair-QA LoRA** — 对照实验
4. **Full SFT** — 仅准备配置，LoRA 全部成功后再考虑

## 环境变量（可选，不设置则使用默认值）

```powershell
$env:LAWLLM_ROOT      = "F:\pythoncode\大模型项目\DISC-LawLLM\DISC-LawLLM-main\DISC-LawLLM-main"
$env:LLAMAFACTORY_ROOT = "F:\LlamaFactory-main\LlamaFactory-main"
```

## 快速开始

### 0. 注册数据集（首次使用，仅需一次）

```powershell
# 在项目根目录执行，自动追加到 LLaMA-Factory 的 dataset_info.json
cd $env:LAWLLM_ROOT
python finetune/patch_dataset_info.py --llamafactory_root $env:LLAMAFACTORY_ROOT
```

### 1. 生成 5K RAG-SFT 数据

```powershell
cd $env:LAWLLM_ROOT
python finetune/prepare_sft_data.py --mode rag_triplet --max_samples 5000
```

输出：`finetune/data/law_rag_sft.json`（随机采样，可重复）

### 2. 启动训练

> 注意：必须先完成步骤 0 和步骤 1，数据文件存在后再启动训练。

```powershell
.\finetune\scripts\train_rag_lora.ps1
```

### 3. Merge adapter

```powershell
# 必须在 LLaMA-Factory 根目录执行，saves/ 路径相对于此目录
cd $env:LLAMAFACTORY_ROOT
.\finetune\scripts\merge_lora.ps1
```

输出目录：`$env:LLAMAFACTORY_ROOT\saves\qwen2.5-7b\merged\law_rag_sft_5k`

### 4. 推理验证

```powershell
# 使用合并后模型
cd $env:LLAMAFACTORY_ROOT
llamafactory-cli chat --model_name_or_path saves/qwen2.5-7b/merged/law_rag_sft_5k --template qwen

# 或使用 adapter 直接推理（不 merge）
llamafactory-cli chat `
  --model_name_or_path Qwen/Qwen2.5-7B-Instruct `
  --adapter_name_or_path saves/qwen2.5-7b/lora/law_rag_sft_5k `
  --template qwen
```

## 数据格式

### rag_triplet（RAG-SFT）

```json
{
  "instruction": "请根据给定法律依据回答问题。",
  "input": "【法律依据】《刑法》第XXX条：...\n\n基于下列案件，推测可能的判决结果。...",
  "output": "根据《刑法》第XXX条..."
}
```

### pair_qa（普通 SFT）

```json
{
  "instruction": "请回答以下法律问题。",
  "input": "请大致描述这篇文书的内容。...",
  "output": "总结：..."
}
```

## 训练配置说明

| 参数 | 值 | 说明 |
|---|---|---|
| `lora_rank` | 16 | 初始值，成功后可升至 32 |
| `cutoff_len` | 2048 | RAG-SFT input 较长，可视情况调整 |
| `batch_size` | 1 × 16 accum = 16 | 5090D 23.5GB 安全范围 |
| `bf16` | true | 5090D 原生支持 |
| `gradient_checkpointing` | true | 降低显存峰值 |
| `max_samples` | 5000 | 第一阶段小样本验证 |

## 版本路线

| 阶段 | 内容 | 状态 |
|---|---|---|
| v0.3a | RAG-SFT 5K LoRA 跑通 | 进行中 |
| v0.3b | RAG-SFT 39K LoRA | 待完成 |
| v0.3c | Pair-QA LoRA 对照 | 待完成 |
| v0.4 | vLLM + FastAPI 部署 | 计划中 |
