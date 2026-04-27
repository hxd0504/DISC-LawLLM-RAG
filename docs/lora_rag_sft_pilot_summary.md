# LoRA RAG-SFT Pilot 实验总结

## 训练配置

| 参数 | 值 |
|---|---|
| 基座模型 | Qwen2.5-7B-Instruct |
| 微调框架 | LLaMA-Factory v0.9.5 |
| 微调方式 | LoRA（rank=16, target=all） |
| 数据集 | DISC-Law-SFT Triplet，随机采样 5K（seed=42） |
| cutoff_len | 2048 |
| batch_size | 1 × 16 grad_accum = 16 |
| learning_rate | 1e-4 |
| epochs | 1 |
| bf16 | true |
| gradient_checkpointing | true |
| adapter 路径 | `saves/qwen2.5-7b/lora/law_rag_sft_5k` |

训练 loss / eval loss 以 LLaMA-Factory 训练日志为准（未在此记录具体数值）。

## 50 条生成对比初步结论

评估方式：从 DISC-Law-SFT Triplet 随机抽取 50 条，分别用 Base 模型和 LoRA adapter 生成，人工对比。

**观察到的规律：**

1. **LoRA 更严格遵循 reference**：给定法条后，LoRA 倾向于直接引用并按法条逻辑组织回答，格式更规范。
2. **Base 更能抵抗 reference 错配**：当提供的法条与案情不符时，Base 模型有时能依据常识纠正，而 LoRA 倾向于盲从给定法条。
3. **5K 与新配置 adapter 差异极小**：两个 adapter 在输出质量上无显著差异，边际收益不明确。

**不声称 LoRA 效果整体提升**，上述为初步观察，未经系统性量化评测。

## 典型失败案例

### Sample 13 — 法条与案情不匹配（强迫劳动 vs 故意伤害）

- **案情**：轻伤二级，应定故意伤害罪（刑法第234条）
- **给定 reference**：刑法第244条（强迫劳动罪）
- **Gold**：故意伤害罪，三年以下有期徒刑
- **Base**：正确识别为故意伤害罪
- **LoRA**：错误定性为强迫劳动罪，完全跟随了错误 reference

**根因**：RAG-SFT 训练目标是"遵循给定法条回答"，导致模型在 reference 与案情冲突时无法识别矛盾。

### Sample 9 — 毒品数量档位判断错误

- **案情**：贩卖海洛因 1.63g + 冰毒 0.5g，累犯
- **Gold**：七年以上有期徒刑并处罚金
- **Base**：七年以上有期徒刑，累犯从重（正确）
- **LoRA**：误判为"数量大"，建议十五年以上（错误，50g 才达大量门槛）

**根因**：5K 样本不足以覆盖所有量刑档位的数值边界，模型学到了"毒品案→重判"的表面模式。

## 结论与后续方向

继续扩大同类 RAG-SFT 训练（39K / Full SFT）的边际收益不明确，且无法解决 reference 错配问题。

**后续方向调整为：**

- **Evidence Quality Control**：在检索阶段过滤与案情不匹配的 reference，避免将错误法条送入模型
- **GraphRAG Reranking**：利用知识图谱结构对候选 reference 重排序，提升 reference 与案情的相关性

adapter 和训练日志保留，不删除。
