# 使用环境变量，未设置时使用默认值
$LAWLLM_ROOT     = if ($env:LAWLLM_ROOT)     { $env:LAWLLM_ROOT }     else { "F:\pythoncode\大模型项目\DISC-LawLLM\DISC-LawLLM-main\DISC-LawLLM-main" }
$LLAMAFACTORY_ROOT = if ($env:LLAMAFACTORY_ROOT) { $env:LLAMAFACTORY_ROOT } else { "F:\LlamaFactory-main\LlamaFactory-main" }

# 步骤1：生成 5K RAG-SFT 数据
Set-Location $LAWLLM_ROOT
python finetune/prepare_sft_data.py --mode rag_triplet --max_samples 5000

# 步骤2：启动训练
Set-Location $LLAMAFACTORY_ROOT
llamafactory-cli train "$LAWLLM_ROOT\finetune\configs\qwen25_7b_lora_rag_sft.yaml"
