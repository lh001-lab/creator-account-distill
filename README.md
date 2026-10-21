# 博主账号蒸馏

可复用的 Codex Skill，用于把博主账号的作品整理为可追溯的方法库。

支持抖音公开作品采集和本地视频素材，包含完整转写、关键画面抽查、OCR、逐条笔记、方法去重及离线可搜索报告。其他平台可更换采集适配器后沿用后续流程。

## 安装与调用

把本仓库复制到个人 Skills 目录，例如：

```bash
git clone https://github.com/lh001-lab/creator-account-distill.git ~/.codex/skills/creator-account-distill
```

如果该目录已经存在，请先检查已有版本，不要直接覆盖。安装后在支持本地 Skills 的 Codex 会话中调用：

> 使用 $creator-account-distill 蒸馏这个博主：[主页链接]，逐条整理公开视频，并结合我的业务输出拍摄方法。

主流程和命令见 [SKILL.md](SKILL.md)。

## 包含的工具

| 文件 | 用途 |
| --- | --- |
| `scripts/f2_account.py` | 抖音 F2 采集适配器，公开清单与临时认证隔离 |
| `scripts/process_media.py` | 本地语音转写、时间戳、字幕与独立续跑的抽帧 |
| `scripts/ocr_frames.swift` | macOS Apple Vision 本地画面文字识别 |
| `scripts/audit_account.py` | 核对来源、媒体和处理状态，检查笔记覆盖率 |
| `scripts/contact_sheets.py` | 生成画面定位缩略图 |
| `scripts/export_report.py` | 导出可搜索的离线 HTML 报告 |

转写和缩略图脚本包含 uv 依赖声明，按需运行即可。Apple Silicon 默认 MLX Whisper，其他系统默认 faster-whisper；F2 依赖及已验证提交见 [采集说明](references/acquisition.md)。首次运行可能需要下载依赖与模型。

## 研究与凭据边界

- 完整转写和关键画面抽查不等同于逐帧人工审片，报告应说明实际核对方式。
- 逐条笔记与跨作品归纳由研究者完成，脚本不自动编造方法或标记人工审核完成。
- 读取浏览器登录状态需在用户授权范围内；临时配置执行后清理。
- 仓库只包含工具和流程，不包含账号媒体、研究报告、Cookie 或模型缓存。
- 使用者需要遵守平台规则与原作品的使用范围。

本地验证覆盖了 Apple Silicon 转写、断点续跑、含百分号路径、抽帧失败隔离、OCR、清单核对和报告搜索。F2 适配器通过离线字段与认证清理测试；平台接口可能变化，运行时应先小批验证。

## 许可证

本仓库的工具代码与流程文档采用 [MIT License](LICENSE)，允许使用、修改与分发，需保留许可证及版权声明。

F2、Whisper 实现、FFmpeg 等外部依赖遵循各自许可证；本许可证不授予第三方视频、图片或账号内容的使用权。
