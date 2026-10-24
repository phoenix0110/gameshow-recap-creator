---
name: gameshow-recap-creator
description: >
  将一条可独立理解的 YouTube 博主长视频压缩并重写为中文二创解说脚本。
  适用于旅行、美食、生活、科技、金融、游戏和人文等单条视频；不处理需要跨集
  前情衔接的连载内容。
license: MIT
metadata:
  version: "1.6.2"
  type: prompt
  interface: prompt
  runtime: any
  languages:
    - zh-CN
  tags:
    - bilibili
    - recap
    - youtube
    - creator-video
    - video-recap
    - secondary-creation
    - script
---

# 单条 YouTube 视频二创解说脚本生成器

把一条完整长视频压缩为中文二创解说脚本，产出旁白、画面提示和时间轴

## 共用规则来源

开始前读取相邻 [Video Recap SOP](../video-recap-sop/SKILL.md#共用制作规则) 的“共用制作规则”，单独调用本 Skill 时也加载该节。各层直接引用相关小节，本 Skill 保留脚本方法、字段格式和题材特有指南。

## 题材路由与前置分析

先读 [genres/_index.md](genres/_index.md)，选择一个题材，读对应的题材文件。

读取 [旁白主持人人设](narrator-personas.md)，确认用户选择的主持人并加载其对应章节，与题材选择独立。

结合完整素材和题材指南，生成 `pre-analysis.md`：

```markdown
# 前置分析

## 题材路由
- 题材：
- 判定依据：
- 已加载：

## 旁白主持人
- 用户选择：
- TTS 音色：

## 人物与称呼
| 原名 | 身份与关系 | 中文昵称 | 昵称依据 | 证据时间 |

## 核心问题
- 目标：
- 阻力：
- 观众等待的答案：

## 故事地图
| 时间范围 | 事件单元 | 主线作用 | 必须保留的信息 |

## 关键证据
| 事实或原话 | 时间范围 | 用途 |

## 钩子候选
| 候选 | 时间范围 | 吸引力来源 | 风险 |

## 推荐钩子与正文回接点
```

完成后按 SOP 的[前置确认](../video-recap-sop/SKILL.md#前置确认)交接，再进入后续流程。

## 后续流程

1. 读 [Layer 1](layer-1-script.md)，生成完整初稿。
2. 运行 `python tools/validate_script_format.py <脚本>`，修到 exit 0。
3. 读 [Layer 2](layer-2-selfcheck.md)，完成叙事编辑。
4. 读 [Layer 3](layer-3-alignment.md)，运行对齐工具并核查素材证据。
5. 读 [Layer 4](layer-4-humanize.md)，实际加载 `humanizer-zh` 做口播润色，再加载 `shuorenhua` 只标问题；修正后完成复读和记录。此步必做，不能用“初稿已经口语化”或前面的校验替代。
6. 复核保护字段，运行格式校验和 `python tools/validate_narration_review.py <脚本>`，均修到 exit 0 后交付。记录缺失、过期或未完成时继续 Layer 4，不交接 TTS 或剪辑。

续写、局部修改和恢复会话也适用上述交付条件。始终以用户当前打开的 `recap-script.md` 为正文，不用历史稿覆盖用户改动。

每个文件只处理自己的职责。发现其他类型的问题时退回对应步骤，不复制其他文件的检查清单。
