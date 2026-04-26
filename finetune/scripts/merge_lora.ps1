# 使用环境变量，未设置时使用默认值
$LLAMAFACTORY_ROOT = if ($env:LLAMAFACTORY_ROOT) { $env:LLAMAFACTORY_ROOT } else { "F:\LlamaFactory-main\LlamaFactory-main" }
$LAWLLM_ROOT     = if ($env:LAWLLM_ROOT)     { $env:LAWLLM_ROOT }     else { "F:\pythoncode\大模型项目\DISC-LawLLM\DISC-LawLLM-main\DISC-LawLLM-main" }

Set-Location $LLAMAFACTORY_ROOT
llamafactory-cli export "$LAWLLM_ROOT\finetune\configs\qwen25_7b_merge_lora.yaml"
