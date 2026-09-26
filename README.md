# gameshow-recap-creator

将一条可独立成篇的 YouTube 博主长视频改写为中文二创解说脚本。

完整入口见 [SKILL.md](SKILL.md)。每条视频只加载一个 `genres/` 题材指南；生成 `pre-analysis.md` 后，依次执行 `layer-1-script.md`、`layer-2-selfcheck.md`、`layer-3-alignment.md` 和 `layer-4-humanize.md`。
