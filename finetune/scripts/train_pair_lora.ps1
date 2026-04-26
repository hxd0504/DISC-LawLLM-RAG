# 使用环境变量，未设置时使用默认值
$LAWLLM_ROOT     = if ($env:LAWLLM_ROOT)     { $env:LAWLLM_ROOT }     else { "F:\pythoncode\大模型项目\DISC-LawLLM\DISC-LawLLM-main\DISC-LawLLM-main" }
$LLAMAFACTORY_ROOT = if ($env:LLAMAFACTORY_ROOT) { $env:LLAMAFACTORY_ROOT } else { "F:\LlamaFactory-main\LlamaFactory-main" }

# 步骤1：生成 Pair-QA 数据（全量）
Set-Location $LAWLLM_ROOT
python finetune/prepare_sft_data.py --mode pair_qa

# 步骤2：启动训练
Set-Location $LLAMAFACTORY_ROOT
llamafactory-cli train "$LAWLLM_ROOT\finetune\configs\qwen25_7b_lora_pair_sft.yaml"
