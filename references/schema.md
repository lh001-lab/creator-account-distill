# 数据约定

所有文件 UTF-8，路径指向当前研究目录；复制或分享研究时可改为相对清单所在目录的路径。

## source_manifest.json

数组。稳定键 `id` 来自平台作品 ID，不是列表下标。

```json
[
  {
    "id": "作品ID",
    "platform": "douyin",
    "account_url": "https://www.douyin.com/user/账号ID",
    "title": "作品原配文",
    "published_at": "2026-10-19 20:00:00",
    "source_url": "https://www.douyin.com/video/作品ID",
    "media_kind": "video",
    "file_prefix": "2026-10-19 20-00-00_作品ID",
    "media_paths": []
  }
]
```

`media_kind` 可为 `video`、`image`、`unknown`。图片有音频或多媒体时不要丢失附件，审核脚本保留所有实际文件。`media_paths` 相对清单或绝对路径均可。不存 Cookie、headers、签名媒体地址；数据缺失用 null，不能当作零。

## processed/<短内容哈希>/

- `status.json`：原文件路径、完整 SHA256、后端、模型、语言、时长；`audio_status`、`transcription_status`、`frames_status` 独立，不能用一个 failed 覆盖成功的转写；始终 `human_verified:false`。
- `transcript.json`：全文及 `{start,end,text}` 段落，时间以秒计。
- `transcript.txt` / `transcript.srt`：方便分批阅读与定位。
- `frames/*.jpg` 与可选 `*.ocr.json`：画面及文字定位。
- `review_flags`：需检查的首尾缺口、无语音、过短转写等。警告是检查提示，不等于已确定内容错误。

审核脚本也支持本次早期流水线的 `status:transcribed` 以及带标题的输出目录，但其旧 `status:failed` 必须实际修复后才能当作完整。

## review_index.json

`audit_account.py` 输出对象，包含 `summary` 与 `items`。每条有稳定 `id`、显示编号 `number`、公开字段、媒体路径、各视频处理信息、图片路径、缺口。它只描述机器处理状态，不写入人工阅读状态。

`--notes notes.json` 可用于覆盖率检查：所有视频已完整转写并不代表所有笔记已完成。`summary.note_coverage` 只统计具有必填内容且显式标记已核对的条目。

## notes.json

对象，以作品 ID 为键。每条由研究者在阅读和检查后填写。下面是字段形状，不是伪造的实际笔记：

```json
{
  "作品ID": {
    "kind": "method",
    "method": "作者名称或明确标为研究者归纳的名称",
    "details": "实际讲了什么，子类型、步骤、成立条件是什么",
    "example": "原片用于解释方法的具体案例",
    "action": "本次为用户业务设计的应用建议，与原作者观点区分",
    "related_ids": [],
    "evidence": [{"start": 12.0, "end": 28.0, "note": "分类出现的片段"}],
    "uncertainties": [],
    "review": {
      "full_transcript_read": true,
      "keyframes_checked": true,
      "all_images_checked": false,
      "visual_scope": "开头 中段 转折 结尾及提示词画面"
    }
  }
}
```

`kind` 可为 `method`、`case`、`story`、`promotion`、`image_record`、`other`。无方法也须描述实际内容，不填虚构方法。视频审核至少 `full_transcript_read` 与 `keyframes_checked`；纯图文需 `all_images_checked`。混合媒体按实际内容同时核对。识别不清如实写 `uncertainties`；保留局部不足，不能让工具静默补写。

## synthesis.json

可选对象。它用于报告整体结论，与每条笔记分开。

```json
{
  "title": "某账号内容方法论研究",
  "scope": "资料范围 截点 实际处理方式 已知缺口",
  "chapters": [
    {"title": "方法之间的关系", "paragraphs": ["跨作品综合归纳"], "source_ids": ["作品ID"]}
  ]
}
```

导出器将章节与逐条笔记放到同一可搜索页面，不自动生成观点或改变审核状态。
