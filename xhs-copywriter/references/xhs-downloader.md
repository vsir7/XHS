# XHS-Downloader 集成参考

## Table of Contents

1. [安装与部署](#安装与部署)
2. [API 模式](#api-模式)
3. [API 请求参数](#api-请求参数)
4. [集成到现有项目](#集成到现有项目)

---

## 安装与部署

### 源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/JoeanAmier/XHS-Downloader.git

# 2. 安装依赖（Python >= 3.12）
cd XHS-Downloader
pip install -r requirements.txt

# 3. 以 API 模式启动
python main.py api
# 默认监听: http://127.0.0.1:5556
# API 文档: http://127.0.0.1:5556/docs
```

### Docker 运行

```bash
docker pull joeanamier/xhs-downloader
docker run -d -p 5556:5556 joeanamier/xhs-downloader api
```

> 注意：2.2 版本开始，功能正常情况下无需额外处理 Cookie。

---

## API 模式

启动后访问 `http://127.0.0.1:5556/docs` 查看完整 API 文档（Swagger UI）。

---

## API 请求参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `url` | str | ✅ | - | 小红书作品链接 |
| `download` | bool | ❌ | false | 是否下载作品文件 |
| `index` | list[int] | ❌ | null | 指定下载图片序号（图文作品） |
| `cookie` | str | ❌ | 配置文件值 | Cookie |
| `proxy` | str | ❌ | 配置文件值 | 代理地址 |
| `skip` | bool | ❌ | false | 是否跳过已下载记录 |

### 支持的链接格式

```
https://www.xiaohongshu.com/explore/作品ID?xsec_token=XXX
https://www.xiaohongshu.com/discovery/item/作品ID?xsec_token=XXX
https://www.xiaohongshu.com/user/profile/作者ID/作品ID?xsec_token=XXX
https://xhslink.com/分享码
```

### 请求示例

```python
import requests

# 仅获取作品信息（不下载文件）
resp = requests.post(
    "http://127.0.0.1:5556/",
    json={"url": "https://www.xiaohongshu.com/explore/xxxxx?xsec_token=XXX"}
)
info = resp.json()

# 下载视频文件
resp = requests.post(
    "http://127.0.0.1:5556/",
    json={
        "url": "https://www.xiaohongshu.com/explore/xxxxx?xsec_token=XXX",
        "download": True
    }
)
result = resp.json()
```

---

## 集成到现有项目

### 替换现有 `parse_xiaohongshu_url()` + `download_video()`

在 `D:\XHS\app.py` 中，现有的视频下载逻辑（自定义 HTTP 请求 + 正则解析）
可完全替换为 XHS-Downloader API 调用：

```python
XHS_DOWNLOADER_API = "http://127.0.0.1:5556"

def get_xhs_info(xhs_url: str) -> dict:
    """通过 XHS-Downloader 获取作品信息"""
    try:
        resp = requests.post(
            XHS_DOWNLOADER_API,
            json={"url": xhs_url},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise Exception(
            "XHS-Downloader API 未启动，"
            "请先运行: cd XHS-Downloader && python main.py api"
        )
    except Exception as e:
        raise Exception(f"XHS-Downloader 调用失败: {str(e)}")


def download_xhs_video(xhs_url: str) -> dict:
    """通过 XHS-Downloader 下载视频文件"""
    try:
        resp = requests.post(
            XHS_DOWNLOADER_API,
            json={"url": xhs_url, "download": True},
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise Exception(f"视频下载失败: {str(e)}")
```

### 服务健康检查

```python
def check_xhs_downloader_status() -> bool:
    """检查 XHS-Downloader API 是否可用"""
    try:
        resp = requests.get(f"{XHS_DOWNLOADER_API}/docs", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False
```

### 注意事项

- XHS-Downloader 作为独立进程运行，需在 Web 应用启动前先启动
- 默认端口 5556，与现有 Web 应用端口 8000 不冲突
- 视频下载路径默认在 XHS-Downloader 目录下的 `_internal/Volume/Download`
- 如需自定义下载路径，修改 XHS-Downloader 的 `settings.json`
