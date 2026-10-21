# 采集与认证

## 已验证的工具组合

F2 上次用于抖音公开主页批量媒体与元数据采集的版本：
`https://github.com/Johnserf-Seed/f2`，提交 `f6be8c0ffba9a127075bbeafe4838716650b6325`。

这是复现基线，不保证未来平台接口仍可用。按任务需要先检查本地已有环境与源码；遇到接口变化查官方项目，修复适配器后先验证少量作品，不盲目提高重试或伪装授权。MLX Whisper 来源：`https://github.com/ml-explore/mlx-examples/tree/main/whisper`；faster-whisper：`https://github.com/SYSTRAN/faster-whisper`；FFmpeg：`https://ffmpeg.org/`。

## F2 适配器

`f2_account.py` 使用 F2 的 CLI 与下载任务入口，在下载同时保存公开字段。该入口是版本相关的内部接口；启动前在所选版本检查函数签名。不要把原始接口响应、签名媒体链接、headers 或 Cookie 写入报告。

推荐在已有 `uv` 环境运行：

```bash
uv run --with 'f2 @ git+https://github.com/Johnserf-Seed/f2.git@f6be8c0ffba9a127075bbeafe4838716650b6325' --with browser-cookie3 --with pyyaml \
  SKILL_DIR/scripts/f2_account.py --url 'ACCOUNT_URL' --output RUN_DIR --max-items 3
```

确认 ID、账号、音视频、图片和公开清单能对应后，再按用户范围运行全量（`--max-items 0` 表示所有当前可见作品）。`--metadata-only` 只枚举，不下载，不能因此声称已看过。小批验证与全量使用同一输出目录可恢复清单；旧清单账号不匹配时使用新的任务目录。

未登录访问失败，而网页已经登录且用户允许复用时：

```bash
uv run --with 'f2 @ git+https://github.com/Johnserf-Seed/f2.git@f6be8c0ffba9a127075bbeafe4838716650b6325' --with browser-cookie3 --with pyyaml \
  SKILL_DIR/scripts/f2_account.py --url 'ACCOUNT_URL' --output RUN_DIR \
  --max-items 0 --browser chrome --reuse-authorized
```

`--reuse-authorized` 只记录调用者确认已取得授权，不代替用户授权。脚本精确筛选 `douyin.com` 及子域；不导出整个浏览器 Cookie。脚本用权限 0600 的临时配置与 0700 临时工作目录隔离 F2 日志、数据库和配置，结束清理；不在参数或终端打印 Cookie。需要系统钥匙串授权时按系统提示处理，不能绕过。

脚本只接受 `douyin.com/user/...` 主页，短链接先在获准浏览器确认最终主页。拒绝将登录信息发送到任意下载站。原作品不能取得时记录原因，可继续整理已取得部分并清楚说明覆盖率。

## 使用已有本地文件

先建立 `source_manifest.json`。每条至少有 `id`、`title`、`published_at`、`source_url`、`media_kind` 和 `media_paths`。本地离线资料可以无原链接，但交付说明缺少来源网址。若导入本次旧 F2 清单，审核脚本也兼容 `aweme_id`、`desc_raw`、`create_time`、`file_prefix` 等字段。

优先用 ID 命名媒体与建立关联，例如 `{create}_{aweme_id}`，避免长标题、同名标题、特殊字符、置顶排序及标题截断造成错配。不依靠 F2 的 SQLite 数据库作为唯一清单；所验证版本的部分批量路径并不持久写入全部作品。

`--max-items 0` 表示请求遍历，不是已经证明无遗漏。全量研究应将去重清单与网页可见作品数、页尾状态和用户范围对照；置顶重复、平台中途返回空页或账号更新都可能造成差异。采集状态会记录请求上限与UTC截点，但不自动宣称全量覆盖。

采集结束不代表下载完整：后续审核需要逐条确认媒体存在、媒体类型、音频和抽帧状态。图文音频、直播回放等特殊类型按实际媒体处理，不凭一项空字段推断。
