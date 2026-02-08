---
name: xhs-copywriter
description: >
  小红书视频文案提取与仿写工作流。集成 XHS-Downloader（API模式）下载视频、
  Coze 工作流 API 提取口播文案、以及基于参考博主风格分析的文案仿写生成。
  当用户需要：(1) 从小红书视频链接提取口播文案，(2) 分析博主口播风格/框架，
  (3) 基于参考风格+商品信息+历史文章生成仿写文案，(4) 集成或维护 D:\XHS Web 应用中的
  视频文案提取与生成功能时，使用此 Skill。
---

# XHS Copywriter - 小红书视频文案提取与仿写

## Overview

将小红书视频链接转化为可仿写的口播文案。完整工作流：
**XHS链接 → XHS-Downloader下载 → Coze API提取文案 → 风格分析 → 仿写生成**

## Architecture

集成到现有 `D:\XHS` FastAPI Web 应用。核心改造点：

| 模块 | 现有实现 | 改造为 |
|------|---------|--------|
| 视频下载 | 自定义 `parse_xiaohongshu_url()` + `download_video()` | XHS-Downloader API 模式 |
| 文案提取 | Whisper 本地语音识别 | Coze 工作流 API（流式） |
| 文案生成 | 模板拼接 `generate_script()` | LLM 驱动的多步骤仿写流程 |

## Workflow

### Step 1: 视频下载（XHS-Downloader API 模式）

XHS-Downloader 支持 API 模式运行，启动后提供 RESTful 接口。

**启动 XHS-Downloader API 服务：**
```bash
cd XHS-Downloader
python main.py api
# 默认监听 http://127.0.0.1:5556
```

**调用下载接口：**
```python
import requests

def download_via_xhs_downloader(xhs_url: str) -> dict:
    """通过 XHS-Downloader API 下载视频并获取作品信息"""
    resp = requests.post(
        "http://127.0.0.1:5556/",
        json={"url": xhs_url, "download": True}
    )
    resp.raise_for_status()
    return resp.json()
```

**返回数据包含：** 作品标题、描述、视频下载地址、作者信息等。

> 详细 API 参数与配置见 [references/xhs-downloader.md](references/xhs-downloader.md)

### Step 2: 文案提取（Coze 工作流 API）

将小红书链接发送给 Coze 工作流，由 Coze 完成视频→文案的提取。

**关键配置（需用户提供）：**
- `COZE_API_TOKEN`: Bearer Token（**占位，待用户填入**）
- `COZE_WORKFLOW_ID`: `7604404057922469922`

**调用方式：**
```python
import requests
import json

def extract_transcript_via_coze(xhs_url: str, token: str) -> str:
    """通过 Coze 工作流提取视频口播文案（流式）"""
    resp = requests.post(
        "https://api.coze.cn/v1/workflow/stream_run",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "workflow_id": "7604404057922469922",
            "parameters": {"input": xhs_url}
        },
        stream=True
    )
    resp.raise_for_status()

    transcript = ""
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            data = json.loads(line[5:])
            # 根据 Coze 流式返回格式解析文案内容
            if data.get("event") == "done":
                break
            content = data.get("data", "")
            if content:
                transcript += content
    return transcript
```

> 详细 Coze API 格式与错误处理见 [references/coze-api.md](references/coze-api.md)

### Step 3: 风格分析与文案仿写

这是核心创作步骤。采用**两阶段 Prompt 驱动**的方式生成文案。

**阶段一：分析参考博主风格**
- 输入：1-2 个参考博主的口播文案（从 Step 2 提取）
- 输出：风格总结（语言风格、叙事框架、情感表达、内容组织）
- **仅分析总结，不生成文案**

**阶段二：基于风格仿写**
- 输入：阶段一的风格总结 + 商品信息 + 历史文章（用户手动输入）
- 输出：新的口播稿文案

> 完整 Prompt 模板与仿写流程见 [references/prompt-workflow.md](references/prompt-workflow.md)

## Integration Guide

### 改造现有 Web 应用 `D:\XHS\app.py`

#### 1. 新增配置项
```python
# XHS-Downloader API
XHS_DOWNLOADER_API = "http://127.0.0.1:5556"

# Coze 工作流 API
COZE_API_URL = "https://api.coze.cn/v1/workflow/stream_run"
COZE_API_TOKEN = ""  # 占位：用户需填入 Bearer Token
COZE_WORKFLOW_ID = "7604404057922469922"
```

#### 2. 替换 `/api/extract-from-url` 端点
- 移除 `parse_xiaohongshu_url()` + `download_video()` + `speech_recognition()` 调用链
- 改为：`download_via_xhs_downloader()` → `extract_transcript_via_coze()`
- 保留 `clean_and_format_text()` 和 `validate_extracted_content()` 用于后处理

#### 3. 替换 `/api/generate-script` 端点
- 移除模板拼接式 `generate_script()` 函数
- 改为调用 LLM API（或内置 Prompt）执行两阶段仿写流程
- 前端需新增：商品信息输入区、历史文章粘贴区

#### 4. 前端 `index.html` 改造
- 提取标签页：输入框改为支持 XHS 链接即可（去除上传视频入口或保留为可选）
- 生成标签页：新增「商品信息」和「历史文章」文本域
- 结果展示：分步显示（风格分析 → 仿写文案）

## Dependencies

```
# 新增依赖（在现有 FastAPI 基础上）
XHS-Downloader  # 作为独立服务运行
requests        # 已有
```

## Notes

- XHS-Downloader 需独立启动 API 服务（端口 5556），Web 应用通过 HTTP 调用
- Coze API Token 尚未就绪，代码中预留占位符
- 文案仿写当前使用 Prompt 模板驱动，后续可接入 LLM API 实现更智能的生成
- 参考博主数量固定 1-2 个，通过前端文本域输入文案内容
