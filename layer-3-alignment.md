# Layer 3：素材对齐

核查脚本中的事实、画面和时间范围

先运行：

```bash
python tools/check_alignment.py <脚本> <字幕>
```

将每段旁白、画面范围和保留原话与工具输出的源字幕逐项对照，按 SOP 的[叙事与素材依据](../video-recap-sop/SKILL.md#叙事与素材依据)及[原声保留与翻译](../video-recap-sop/SKILL.md#原声保留与翻译)核查。另检查预计旁白时长能否被规划段落容纳。

可以修正事实和区间边界，或删除无证据的细节。若问题会改变主线、顺序或内容取舍，退回 Layer 2。检查工具 exit 0 且逐段人工核查通过后，进入 Layer 4。
