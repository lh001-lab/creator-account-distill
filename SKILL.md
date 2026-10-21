---
name: creator-account-distill
description: 蒸馏抖音等博主账号的内容方法论。用于逐条研究账号作品、转写视频、核对画面、去重归纳方法和建立原作品索引；支持本地素材与获准访问的公开视频。适合“把这个博主的视频看完并详细总结”，不用于仅凭标题猜内容或日常剪辑。
---

# 博主账号蒸馏

将账号作品整理成有来源、可执行的方法库，区分原作者讲授、案例表现和本次研究的应用建议。默认用中文交付；沿用用户指定的语言、范围和格式。

## 开始与范围

1. 用主页链接、账号名与可见身份确认对象。重名时先查证，不把近似名称当同一账号。
2. 遵守用户指定的全量、日期或样本范围。用户要求全量时，列出本次可见作品总数和截点；未完整取得时明确缺口，不用样本冒充全量。只需选题总结时无需启动完整下载流水线。
3. 在当前任务目录下建立 `research/<account-slug>/`，保存公开清单、素材、转写、笔记与检查结果。Skill 目录只放工具，不放账号素材、Cookie、模型缓存或私人资料。
4. 浏览器已登录可直接核对网页；提取浏览器 Cookie 是不同操作。仅在当前授权范围内读取该平台 Cookie。过去另一个账号的授权不自动覆盖新账号。若需要授权，用一句话说明读取范围、用途和临时保存方式；已有明确授权时继续执行，不重复问。

## 工具选择

- 已有本地素材：从整理清单与转写开始。
- 抖音：先读 [采集说明](references/acquisition.md)。本 Skill 带 F2 适配器，使用上次验证过的代码版本，先小批验证再全量。工具接口变化时检查当前源码或官方文档。
- 其他平台：优先可用的连接器、平台导出或适配的公开工具。换采集适配器即可，后续数据格式不变；不要把 F2 抖音适配器宣称为全平台下载器。
- Apple Silicon：本地 MLX Whisper；其他系统可用 faster-whisper。脚本按平台选择默认后端。模型、OCR、ffmpeg 依赖按需准备，不擅自读取其他账号或安装全局组件。

## 可续跑的处理顺序

### 作品清单和本地证据

保留稳定作品 ID、日期、原配文、原链接、类型与本地媒体对应关系。不要靠置顶顺序、文件排序或标题模糊匹配编号；去重后按日期与 ID 稳定排序。图文和视频单列，不能由缺少时长推断为图文。数据结构见 [数据约定](references/schema.md)。

`f2_account.py` 保存安全的公开元数据与媒体；`process_media.py` 为本地媒体生成完整带时间戳的转写、SRT、画面和独立状态。默认每 3 秒取帧，用途是画面核对，并非已完成逐帧审片。`ocr_frames.swift` 是 macOS 本地 Apple Vision 辅助，不是开源 OCR；其他平台可换已有 OCR 或直接查看画面。

```bash
uv run SKILL_DIR/scripts/process_media.py --input-dir RUN_DIR/media --output RUN_DIR/processed
swift SKILL_DIR/scripts/ocr_frames.swift RUN_DIR/processed
python3 SKILL_DIR/scripts/audit_account.py --manifest RUN_DIR/source_manifest.json --media-dir RUN_DIR/media --processed RUN_DIR/processed --output RUN_DIR/review_index.json
uv run SKILL_DIR/scripts/contact_sheets.py --index RUN_DIR/review_index.json --output RUN_DIR/boards
```

将示例中的 `SKILL_DIR` 和 `RUN_DIR` 替换成实际绝对路径；路径包含空格时引用整个路径。依赖不存在时不要声称执行成功。完整转写可能需时，持续报告完成数、失败数与下一步。

### 逐条阅读与画面核对

完整阅读每条转写；分批输出时控制批量，输出被截断的部分必须补读。查看每条开头、中段、转折、结尾的画面；对分类名称、示范动作、图表、提示词以及语音含糊处增加检查。图片作品查看全部图片。画面抽样不足以支持结论时继续查看相应片段。

转写首尾缺失、重复幻觉、无语音、音乐覆盖、低清屏幕均需记录并处理。抽帧失败可单独续跑，不重新转写已完成音频。不要因文件存在或脚本成功就把人工核对标为完成。`audit_account.py` 只核对文件完整性，不会替你声称看完。

### 形成方法库

按 [分析说明](references/analysis.md) 为每条写笔记，再做跨视频归纳。保留重复作品的条目，明确其与先前方法的重合或新增条件。案例、故事、广告、课程记录不能强行编成新教学方法。作者的播放量、粉丝、销量、因果与平台算法判断，未独立核实则按引用或自述处理。

笔记由研究者写入 `notes.json`，以作品 ID 为键；章节归纳可写 `synthesis.json`。不要把原始 ASR 文本直接当成最终笔记。格式、必填项和审核状态见数据约定。

## 交付

按用户需求输出详细正文和逐条索引，含可点击原链接。至少说明范围、实际处理方式、尚未解决的缺口；不能把全长转写加抽看画面说成逐帧人工看完。原作者观点与本次应用建议用明确标签区分。

默认可以用配套导出器生成可搜索的本地 HTML 报告，满足长资料查阅；若用户指定 Word、PDF、表格或其他格式则遵循该格式，使用可用的对应文档 Skill，完成渲染与检查后交付。见 [交付与故障处理](references/delivery.md)。

```bash
python3 SKILL_DIR/scripts/export_report.py --index RUN_DIR/review_index.json --notes RUN_DIR/notes.json --synthesis RUN_DIR/synthesis.json --output RUN_DIR/report.html
```

执行采集与整理属于研究授权，不包含代关注、点赞、评论、联系作者、购买课程、发布报告或上传私人素材。临时认证配置用后删除，成品与分享包只含公开来源和研究结果。
