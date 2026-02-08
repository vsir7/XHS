# Coze 工作流 API 集成参考

## Table of Contents

1. [API 概览](#api-概览)
2. [请求格式](#请求格式)
3. [流式响应解析](#流式响应解析)
4. [错误处理](#错误处理)
5. [集成代码模板](#集成代码模板)

---

## API 概览

| 项目 | 值 |
|------|-----|
| 端点 | `https://api.coze.cn/v1/workflow/stream_run` |
| 方法 | POST |
| 认证 | Bearer Token |
| 响应 | Server-Sent Events (SSE) 流式 |
| Workflow ID | `7604404057922469922` |
| Token | **占位 - 待用户填入** |

---

## 请求格式

### cURL 示例

```bash
curl -X POST 'https://api.coze.cn/v1/workflow/stream_run' \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "7604404057922469922",
    "parameters": {
      "input": "https://www.xiaohongshu.com/discovery/item/685366cc0000000011003ee8?app_platform=ios&app_version=9.19.3&share_from_user_hidden=true&xsec_source=app_share&type=video&xsec_token=CBZY2_7hoOenkSRsS_tJFT1R6e7xmayIA5hDc9cRxlG80=&author_share=1&xhsshare=WeixinSession&shareRedId=N0k0OTtLNzw2NzUyOTgwNjY4OTdFNj9P&apptime=1770538843&share_id=fe0d8f9a4b9b42cba542a7e8ee2c8b35"
    }
  }'
```

### Python 请求

```python
import requests

resp = requests.post(
    "https://api.coze.cn/v1/workflow/stream_run",
    headers={
        "Authorization": "Bearer <TOKEN>",
        "Content-Type": "application/json"
    },
    json={
        "workflow_id": "7604404057922469922",
        "parameters": {
            "input": xhs_url  # 小红书视频链接
        }
    },
    stream=True
)
```

---

## 流式响应解析

Coze 工作流使用 SSE (Server-Sent Events) 格式返回数据。

### 响应事件类型

| 事件 | 说明 |
|------|------|
| `message` | 工作流中间输出 |
| `done` | 工作流执行完成 |
| `error` | 执行错误 |
| `interrupt` | 需要人工干预 |

### SSE 数据格式

```
event: message
data: {"content": "提取的文案内容片段...", "node_title": "语音识别"}

event: done
data: {"output": "完整的口播文案内容..."}
```

### 解析代码

```python
import json

def parse_coze_stream(response) -> str:
    """解析 Coze 流式响应，提取最终文案"""
    result = ""
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue

        # 处理 SSE 格式
        if line.startswith("event:"):
            event_type = line[6:].strip()
            continue

        if line.startswith("data:"):
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # 根据事件类型处理
            if isinstance(data, dict):
                # 最终输出
                if "output" in data:
                    result = data["output"]
                    break
                # 中间内容
                if "content" in data:
                    result += data["content"]
                # 错误
                if "error_message" in data:
                    raise Exception(f"Coze API Error: {data['error_message']}")

    return result.strip()
```

---

## 错误处理

| HTTP 状态码 | 原因 | 处理方式 |
|-------------|------|---------|
| 401 | Token 无效或过期 | 检查并更新 Bearer Token |
| 400 | 请求参数错误 | 检查 workflow_id 和 parameters 格式 |
| 429 | 请求频率限制 | 等待后重试（指数退避） |
| 500 | Coze 服务端错误 | 重试或提示用户稍后再试 |
| 超时 | 视频过长或网络问题 | 设置合理超时（建议 120s） |

### 重试策略

```python
import time

def call_coze_with_retry(xhs_url: str, token: str, max_retries: int = 3) -> str:
    """带重试的 Coze API 调用"""
    for attempt in range(max_retries):
        try:
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
                stream=True,
                timeout=120
            )
            resp.raise_for_status()
            return parse_coze_stream(resp)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise
    raise Exception("Coze API 调用失败，已达最大重试次数")
```

---

## 集成代码模板

### FastAPI 端点集成

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import asyncio

@app.post("/api/extract-transcript")
async def extract_transcript(data: dict):
    """从小红书链接提取口播文案（通过 Coze 工作流）"""
    xhs_url = data.get("url")
    if not xhs_url:
        raise HTTPException(status_code=400, detail="缺少小红书链接")

    if not COZE_API_TOKEN:
        raise HTTPException(status_code=500, detail="Coze API Token 未配置")

    try:
        transcript = call_coze_with_retry(xhs_url, COZE_API_TOKEN)

        # 复用现有的文本清洗和校验
        cleaned = clean_and_format_text(transcript)
        validation = validate_extracted_content(cleaned)

        return {
            "success": True,
            "data": {
                "transcript": cleaned,
                "validation": validation
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文案提取失败: {str(e)}")
```
