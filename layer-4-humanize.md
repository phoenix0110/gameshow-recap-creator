# Layer 4：旁白口播润色与审稿

输入是已经完成叙事编辑和素材核查的当前稿

## 加载依赖

从 Skill 注册表定位 `humanizer-zh/SKILL.md` 和 `shuorenhua/SKILL.md`，按需读取。使用已安装版本，不用记忆中的旧版规则代替。在本机优先路径为 `C:/Users/yinsh/.agents/skills/<skill-name>/SKILL.md`；其他环境从注册表或共享 `.agents/skills` 定位。依赖确实找不到时保留稿件、报告缺失，不宣称完成。

## 顺序与边界

执行 SOP 的[旁白润色与审稿](../video-recap-sop/SKILL.md#旁白润色与审稿)。

1. 保存当前稿的润色前快照到 `draft-history/recap-script.before-polish.md`；已有历史快照时用版本后缀保留，不覆盖用户正文。记录口吻依据：已确认人设、用户修改或旁白样本；无样本时沿用输入语域，不擅自添加方言或口头禅。
2. 使用 **humanizer-zh**：只润色 `**旁白**` 字段内的正文。目标为自然口播、现场感和稳定声音，精简不是主目标。允许幽默、反问、短句、悬念、停顿和重复，不按模式命中就删。保留有效信息、确定程度和归属，不制造心理活动或危险。原声与翻译保持原样，不能把译文当旁白润色。
3. 使用 **shuorenhua，annotation mode**：对照润色前后及上下文，指出新增或丢失的信息、主体或限定变化、空泛包装、重复解释和无叙事作用的收尾。每条问题给具体片段、原因和方向，不执行第二次全文清洗。
4. 由创作者逐项处理审稿意见：修正成立的问题，不成立的意见记录保留理由。修改后复核相关句子，不能带未处理问题交付。若需改结构、原声、画面或事实，退回对应层，完成后用新基线重做本层。
5. 按口播语气通读整稿，检查衔接、节奏和原声交接。
6. 保存当前定稿、检查记录与回执，复核非旁白字段未变，运行格式校验及本层交接校验。用户后续改稿后按 SOP 重新核查，不反向覆盖用户改动。

## 检查记录与完成条件

在脚本同目录写 `narration-review.md`：记录实际加载的 Skill、口吻依据、检查范围、代表性的修改前后及理由、说人话审稿意见及每条处理结果、复读发现与处理。没有问题可以如实记录。记录是制作交接附件，不加入旁白正文。

实际完成后才写 `narration-review.json`，所有路径可用绝对路径或相对脚本目录的路径；SHA-256 取真实文件字节。格式如下：

```json
{
  "schema_version": 1,
  "script_sha256": "当前定稿SHA-256",
  "before_path": "draft-history/recap-script.before-polish.md",
  "before_sha256": "润色前快照SHA-256",
  "notes_path": "narration-review.md",
  "notes_sha256": "检查记录SHA-256",
  "skills": {
    "humanizer-zh": {"path": "实际SKILL.md路径", "sha256": "实际SHA-256"},
    "shuorenhua": {"path": "实际SKILL.md路径", "sha256": "实际SHA-256"}
  },
  "checks": {
    "humanizer_completed": true,
    "shuorenhua_annotation_completed": true,
    "issues_resolved": true,
    "semantic_fidelity_checked": true,
    "voice_and_continuity_readthrough": true
  }
}
```

执行 `python tools/validate_script_format.py <脚本>` 和 `python tools/validate_narration_review.py <脚本>`，均 exit 0 才交接。校验器验证文件绑定、记录完整性和保护字段，不能证明实际阅读、润色或语义质量；这些仍须真实执行，禁止为放行伪造记录。不要以修改数量、评分或更短的字数作为完成条件。
