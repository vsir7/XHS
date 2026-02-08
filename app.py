#!/usr/bin/env python3
"""
小红书视频口播稿文案提取工具 - 后端服务
集成 XHS-Downloader API + Coze 工作流 API
"""

from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import tempfile
import json
import re
import time
import requests
from datetime import datetime

load_dotenv()

# ============================================================
# Configuration
# ============================================================

# XHS-Downloader API (need to start separately: python main.py api)
XHS_DOWNLOADER_API = os.getenv("XHS_DOWNLOADER_API", "http://127.0.0.1:5556")

# Coze Workflow API
COZE_API_URL = "https://api.coze.cn/v1/workflow/stream_run"
COZE_API_TOKEN = os.getenv("COZE_API_TOKEN", "")
COZE_WORKFLOW_ID = os.getenv("COZE_WORKFLOW_ID", "7604404057922469922")

# 创建FastAPI应用
app = FastAPI(
    title="小红书视频口播稿文案提取API",
    description="提供视频上传、语音识别、文案提取等功能",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Coze API Integration
# ============================================================

def extract_transcript_via_coze(xhs_url: str, max_retries: int = 3) -> str:
    """
    Call Coze workflow API to extract transcript from XHS video link (SSE stream).
    """
    if not COZE_API_TOKEN:
        raise Exception("Coze API Token is not configured")

    for attempt in range(max_retries):
        try:
            print(f"[Coze] Sending request (attempt {attempt + 1}): {xhs_url}")
            resp = requests.post(
                COZE_API_URL,
                headers={
                    "Authorization": f"Bearer {COZE_API_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "workflow_id": COZE_WORKFLOW_ID,
                    "parameters": {"input": xhs_url},
                },
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()
            return _parse_coze_stream(resp)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            print(f"[Coze] HTTP {status} on attempt {attempt + 1}")
            if status == 429 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise Exception(f"Coze API error (HTTP {status}): {str(e)}")
        except Exception as e:
            print(f"[Coze] Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise
    raise Exception("Coze API call failed after max retries")


def _parse_coze_stream(response) -> str:
    """Parse Coze SSE stream and extract final transcript."""
    result = ""
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data:"):
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                if "output" in data:
                    result = data["output"]
                    break
                if "content" in data:
                    result += data["content"]
                if "error_message" in data:
                    raise Exception(f"Coze workflow error: {data['error_message']}")
    transcript = result.strip()
    if not transcript:
        raise Exception("Coze returned empty transcript")
    print(f"[Coze] Transcript received, length: {len(transcript)} chars")
    return transcript


# ============================================================
# XHS-Downloader Integration
# ============================================================

def check_xhs_downloader_status() -> bool:
    """Check if XHS-Downloader API is available."""
    try:
        resp = requests.get(f"{XHS_DOWNLOADER_API}/docs", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def download_via_xhs_downloader(xhs_url: str, download_file: bool = False) -> dict:
    """
    Call XHS-Downloader API to get note info and optionally download video.
    """
    try:
        resp = requests.post(
            XHS_DOWNLOADER_API,
            json={"url": xhs_url, "download": download_file},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise Exception(
            "XHS-Downloader API is not running. "
            "Start it with: cd XHS-Downloader && python main.py api"
        )
    except Exception as e:
        raise Exception(f"XHS-Downloader call failed: {str(e)}")

def clean_and_format_text(text):
    """
    文本清洗与格式化处理（优化版，避免过度清洗）
    """
    try:
        if not text:
            return ""
        
        # 1. 去除首尾空白字符
        text = text.strip()
        
        # 2. 标准化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 3. 去除多余的空白字符（保留单个空格）
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 4. 优化标点符号（中文标点后添加空格，提高可读性）
        text = re.sub(r'([，。！？；：、])', r'\1 ', text)
        text = re.sub(r'([,.!?:;])', r'\1 ', text)
        
        # 5. 去除多余的空格（但保留标点后的空格）
        text = re.sub(r' +', ' ', text)
        
        # 6. 断句处理（保持原有结构，不做过度分割）
        sentences = []
        current_sentence = ""
        
        # 按标点符号分割句子
        punctuation = r'[，。！？；：,.!?:;]'
        parts = re.split(f'({punctuation})', text)
        
        for part in parts:
            if part:
                current_sentence += part
                if re.match(punctuation, part):
                    sentence = current_sentence.strip()
                    if sentence:
                        sentences.append(sentence)
                    current_sentence = ""
        
        # 处理最后一个句子
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # 7. 段落划分（基于语义，每5-8个句子为一个段落）
        paragraphs = []
        current_paragraph = []
        
        for i, sentence in enumerate(sentences):
            current_paragraph.append(sentence)
            if (i + 1) % 6 == 0 or i == len(sentences) - 1:
                paragraph = ' '.join(current_paragraph)
                if paragraph.strip():
                    paragraphs.append(paragraph.strip())
                current_paragraph = []
        
        # 8. 格式美化
        formatted_text = '\n\n'.join(paragraphs)
        
        # 9. 去除重复内容（使用更智能的相似度检测）
        lines = formatted_text.split('\n')
        unique_lines = []
        seen_hashes = set()
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:
                # 使用简单的哈希来检测完全重复
                line_hash = hash(line_stripped)
                if line_hash not in seen_hashes:
                    unique_lines.append(line)
                    seen_hashes.add(line_hash)
        
        formatted_text = '\n'.join(unique_lines)
        
        # 10. 最终清理
        formatted_text = formatted_text.strip()
        
        return formatted_text
    except Exception as e:
        print(f"文本处理失败（将使用原始文本）：{str(e)}")
        return text

def validate_extracted_content(text, audio_duration=None):
    """
    内容校验机制，验证提取的文本质量
    """
    try:
        validation_result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "quality_score": 0.0,
            "text_length": len(text),
            "sentence_count": 0,
            "word_count": 0
        }
        
        if not text or not text.strip():
            validation_result["is_valid"] = False
            validation_result["issues"].append("提取的文本为空")
            return validation_result
        
        # 1. 检查文本长度
        text_length = len(text.strip())
        validation_result["text_length"] = text_length
        
        if text_length < 10:
            validation_result["is_valid"] = False
            validation_result["issues"].append(f"文本过短（{text_length}字符），可能提取失败")
        elif text_length < 50:
            validation_result["warnings"].append(f"文本较短（{text_length}字符），请检查是否完整")
        
        # 2. 检查句子数量
        sentences = re.split(r'[，。！？；：,.!?:;]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        validation_result["sentence_count"] = len(sentences)
        
        if len(sentences) < 2:
            validation_result["warnings"].append("句子数量较少，可能不完整")
        
        # 3. 检查词汇数量
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
        validation_result["word_count"] = len(words)
        
        if len(words) < 5:
            validation_result["warnings"].append("词汇数量较少")
        
        # 4. 检查重复内容
        lines = text.split('\n')
        unique_lines = len(set(line.strip() for line in lines if line.strip()))
        if len(lines) > 0 and unique_lines / len(lines) < 0.5:
            validation_result["warnings"].append("存在较多重复内容")
        
        # 5. 检查是否包含常见的识别错误标记
        error_patterns = [
            r'\[.*?\]',  # 方括号内容
            r'\{.*?\}',  # 花括号内容
            r'<.*?>',    # 尖括号内容
            r'\(.*?\)',  # 圆括号内容（过多）
            r'&nbsp;',   # HTML实体
            r'&amp;',    # HTML实体
            r'&lt;',     # HTML实体
            r'&gt;',     # HTML实体
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, text)
            if matches:
                validation_result["warnings"].append(f"发现可能的格式标记：{pattern}")
        
        # 6. 检查是否包含模拟数据标记
        if "MOCK" in text.upper() or "模拟" in text:
            validation_result["is_valid"] = False
            validation_result["issues"].append("检测到模拟数据标记")
        
        # 7. 计算质量分数
        quality_score = 1.0
        
        # 文本长度扣分
        if text_length < 50:
            quality_score -= 0.3
        elif text_length < 100:
            quality_score -= 0.1
        
        # 句子数量扣分
        if len(sentences) < 2:
            quality_score -= 0.2
        
        # 重复内容扣分
        if len(lines) > 0 and unique_lines / len(lines) < 0.5:
            quality_score -= 0.2
        
        # 错误标记扣分
        for pattern in error_patterns:
            if re.search(pattern, text):
                quality_score -= 0.1
        
        validation_result["quality_score"] = max(0.0, min(1.0, quality_score))
        
        # 8. 如果有严重问题，标记为无效
        if validation_result["issues"]:
            validation_result["is_valid"] = False
        
        return validation_result
        
    except Exception as e:
        print(f"内容校验失败：{str(e)}")
        return {
            "is_valid": False,
            "issues": [f"校验过程出错：{str(e)}"],
            "warnings": [],
            "quality_score": 0.0
        }

def analyze_script_style(script):
    """
    分析口播稿的语言风格特点
    """
    try:
        # 1. 基础统计
        sentences = re.split(r'[，。！？；：,.!?:;]', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = re.findall(r'\b\w+\b', script)
        
        # 2. 语言风格分析
        style_analysis = {
            "sentence_count": len(sentences),
            "average_sentence_length": round(len(words) / len(sentences), 2) if sentences else 0,
            "word_count": len(words),
            "vocabulary_diversity": round(len(set(words)) / len(words), 2) if words else 0,
            "tone": "",
            "style": [],
            "features": []
        }
        
        # 分析语气
        if any(word in script for word in ["大家好", "欢迎", "谢谢", "希望"]):
            style_analysis["tone"] = "友好亲切"
        elif any(word in script for word in ["推荐", "必备", "好用", "实用"]):
            style_analysis["tone"] += " 推荐种草" if style_analysis["tone"] else "推荐种草"
        elif any(word in script for word in ["教程", "步骤", "方法", "技巧"]):
            style_analysis["tone"] += " 教程指导" if style_analysis["tone"] else "教程指导"
        else:
            style_analysis["tone"] = "中性客观"
        
        # 分析风格特点
        if style_analysis["average_sentence_length"] < 10:
            style_analysis["style"].append("简洁明快")
        elif style_analysis["average_sentence_length"] > 20:
            style_analysis["style"].append("详细全面")
        else:
            style_analysis["style"].append("适中流畅")
        
        # 分析用词特点
        if any(word in script for word in ["超级", "非常", "特别", "真的"]):
            style_analysis["features"].append("使用强调词")
        if any(word in script for word in ["我觉得", "个人认为", "推荐给", "适合"]):
            style_analysis["features"].append("主观性表达")
        if any(word in script for word in ["首先", "然后", "接下来", "最后"]):
            style_analysis["features"].append("逻辑清晰")
        
        return style_analysis
    except Exception as e:
        print(f"风格分析失败：{str(e)}")
        return {"error": str(e)}

def analyze_narrative_structure(script):
    """
    分析口播稿的叙事框架结构
    """
    try:
        structure_analysis = {
            "structure": [],
            "opening": "",
            "body": [],
            "closing": "",
            "transitions": []
        }
        
        # 分析开头
        lines = script.split('\n')
        opening_lines = []
        body_lines = []
        closing_lines = []
        
        # 识别开头
        for i, line in enumerate(lines):
            if any(pattern in line for pattern in ["大家好", "欢迎", "今天", "分享", "介绍"]):
                opening_lines.append(line)
            else:
                break
        
        # 识别结尾
        for i in range(len(lines)-1, -1, -1):
            if any(pattern in lines[i] for pattern in ["谢谢", "点赞", "收藏", "关注", "下期", "再见"]):
                closing_lines.insert(0, lines[i])
            else:
                break
        
        # 剩余部分为主体
        if opening_lines and closing_lines:
            body_lines = lines[len(opening_lines):-len(closing_lines)]
        elif opening_lines:
            body_lines = lines[len(opening_lines):]
        elif closing_lines:
            body_lines = lines[:-len(closing_lines)]
        else:
            body_lines = lines
        
        # 分析主体结构
        body_structure = []
        if any(pattern in script for pattern in ["首先", "第一步"]):
            body_structure.append("步骤式")
        if any(pattern in script for pattern in ["优点", "好处", "优势"]):
            body_structure.append("优缺点分析")
        if any(pattern in script for pattern in ["对比", "相比", "区别"]):
            body_structure.append("对比式")
        
        if not body_structure:
            body_structure.append("叙述式")
        
        structure_analysis["opening"] = ' '.join(opening_lines)
        structure_analysis["body"] = body_structure
        structure_analysis["closing"] = ' '.join(closing_lines)
        structure_analysis["structure"] = ["开头", "主体", "结尾"]
        
        # 分析过渡词
        transitions = []
        if "首先" in script:
            transitions.append("首先")
        if "然后" in script:
            transitions.append("然后")
        if "接下来" in script:
            transitions.append("接下来")
        if "最后" in script:
            transitions.append("最后")
        structure_analysis["transitions"] = transitions
        
        return structure_analysis
    except Exception as e:
        print(f"结构分析失败：{str(e)}")
        return {"error": str(e)}

def analyze_content_organization(script):
    """
    分析口播稿的内容组织方式
    """
    try:
        organization_analysis = {
            "organization": [],
            "key_points": [],
            "emphasis": [],
            "pace": ""
        }
        
        # 分析内容组织
        if any(pattern in script for pattern in ["第一步", "第二步", "第三步"]):
            organization_analysis["organization"].append("步骤顺序")
        if any(pattern in script for pattern in ["重点", "关键", "注意", "提醒"]):
            organization_analysis["organization"].append("重点突出")
        if any(pattern in script for pattern in ["案例", "例子", "比如", "例如"]):
            organization_analysis["organization"].append("案例辅助")
        
        # 提取关键点
        key_patterns = ["重点是", "关键是", "注意", "提醒", "推荐", "必备", "好用"]
        for pattern in key_patterns:
            matches = re.findall(f'{pattern}[^，。！？；：,.!?:;]*', script)
            organization_analysis["key_points"].extend([m.strip() for m in matches])
        
        # 分析强调方式
        if any(word in script for word in ["记住", "一定要", "千万", "必须"]):
            organization_analysis["emphasis"].append("直接强调")
        if any(word in script for word in ["重复", "再说一遍", "强调"]):
            organization_analysis["emphasis"].append("重复强调")
        
        # 分析节奏
        sentences = re.split(r'[，。！？；：,.!?:;]', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) < 5:
            organization_analysis["pace"] = "缓慢从容"
        elif len(sentences) > 15:
            organization_analysis["pace"] = "快速紧凑"
        else:
            organization_analysis["pace"] = "适中平稳"
        
        return organization_analysis
    except Exception as e:
        print(f"内容组织分析失败：{str(e)}")
        return {"error": str(e)}

def analyze_emotional_expression(script):
    """
    分析口播稿的情感表达模式
    """
    try:
        emotional_analysis = {
            "emotion": [],
            "intensity": "",
            "expression": []
        }
        
        # 分析情感倾向
        positive_words = ["喜欢", "爱", "好用", "满意", "推荐", "惊喜", "开心", "激动"]
        negative_words = ["不喜欢", "失望", "难用", "不满意", "缺点", "问题", "麻烦"]
        neutral_words = ["客观", "实际", "事实", "数据", "效果", "功能"]
        
        positive_count = sum(1 for word in positive_words if word in script)
        negative_count = sum(1 for word in negative_words if word in script)
        
        if positive_count > negative_count:
            emotional_analysis["emotion"].append("积极正面")
        elif negative_count > positive_count:
            emotional_analysis["emotion"].append("消极负面")
        else:
            emotional_analysis["emotion"].append("中性客观")
        
        # 分析情感强度
        intensity_words = ["超级", "非常", "特别", "真的", "太", "极其", "绝对"]
        intensity_count = sum(1 for word in intensity_words if word in script)
        
        if intensity_count > 3:
            emotional_analysis["intensity"] = "强烈"
        elif intensity_count > 0:
            emotional_analysis["intensity"] = "中等"
        else:
            emotional_analysis["intensity"] = "温和"
        
        # 分析表达方式
        if any(word in script for word in ["觉得", "感受", "体验", "分享"]):
            emotional_analysis["expression"].append("个人体验分享")
        if any(word in script for word in ["建议", "推荐", "应该", "可以"]):
            emotional_analysis["expression"].append("建议式表达")
        if any(word in script for word in ["惊叹", "没想到", "震惊", "意外"]):
            emotional_analysis["expression"].append("惊讶式表达")
        
        return emotional_analysis
    except Exception as e:
        print(f"情感分析失败：{str(e)}")
        return {"error": str(e)}

def analyze_script(script):
    """
    综合分析口播稿
    """
    try:
        analysis = {
            "style": analyze_script_style(script),
            "narrative": analyze_narrative_structure(script),
            "content": analyze_content_organization(script),
            "emotion": analyze_emotional_expression(script),
            "summary": ""
        }
        
        # 生成分析总结
        summary_parts = []
        
        # 风格总结
        if analysis["style"].get("tone"):
            summary_parts.append(f"语言风格{analysis['style']['tone']}")
        if analysis["style"].get("style"):
            summary_parts.append(f"，{', '.join(analysis['style']['style'])}")
        
        # 结构总结
        if analysis["narrative"].get("structure"):
            summary_parts.append(f"。采用{'-'.join(analysis['narrative']['structure'])}的叙事结构")
        if analysis["narrative"].get("body"):
            summary_parts.append(f"，主体部分为{'-'.join(analysis['narrative']['body'])}结构")
        
        # 内容组织总结
        if analysis["content"].get("organization"):
            summary_parts.append(f"。内容组织{', '.join(analysis['content']['organization'])}")
        if analysis["content"].get("pace"):
            summary_parts.append(f"，节奏{analysis['content']['pace']}")
        
        # 情感表达总结
        if analysis["emotion"].get("emotion"):
            summary_parts.append(f"。情感表达{', '.join(analysis['emotion']['emotion'])}")
        if analysis["emotion"].get("intensity"):
            summary_parts.append(f"，强度{analysis['emotion']['intensity']}")
        
        analysis["summary"] = ''.join(summary_parts)
        
        return analysis
    except Exception as e:
        print(f"综合分析失败：{str(e)}")
        return {"error": str(e)}

def parse_xiaohongshu_url(url):
    """
    解析小红书视频链接，获取视频真实地址
    """
    try:
        # 发送请求获取页面内容
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.xiaohongshu.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": "abRequestId=00000000-0000-0000-0000-000000000000; xsecappid=xhs-pc-web; a1=198bcf85656rpl7j7k8cqdpiy97ufv8dtmx3t20790000324993; webId=00000000-0000-0000-0000-000000000000; gsid=00000000000000000000000000000000; webBuild=4.8.2; acw_tc=00000000000000000000000000000000; sec_poison_id=00000000-0000-0000-0000-000000000000"
        }
        print(f"正在请求小红书链接：{url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"请求成功，状态码：{response.status_code}")
        
        # 保存页面内容到临时文件，方便调试
        debug_file = os.path.join(TEMP_DIR, f"xiaohongshu_debug_{datetime.now().timestamp()}.html")
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)  # 保存完整页面内容
        print(f"页面内容已保存到：{debug_file}")
        
        # 从页面内容中提取视频地址
        print("尝试提取视频地址...")
        
        # 1. 尝试从页面中提取JSON数据
        print("尝试从页面中提取JSON数据...")
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__data__\s*=\s*({.*?});',
            r'window\.__page__\s*=\s*({.*?});',
            r'window\.__NEXT_DATA__\s*=\s*({.*?});',
            r'{"note":.*?}',
            r'{"video":.*?}'
        ]
        
        video_url = None
        for json_pattern in json_patterns:
            print(f"尝试JSON模式：{json_pattern}")
            json_matches = re.findall(json_pattern, response.text, re.DOTALL)
            if json_matches:
                print(f"找到JSON数据，长度：{len(json_matches[0])}")
                try:
                    json_data = json.loads(json_matches[0])
                    # 递归查找视频地址
                    def find_video_url(data):
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if key in ['video', 'videoUrl', 'video_url', 'main_url', 'play_url', 'url']:
                                    if isinstance(value, str) and value.startswith('https://'):
                                        return value
                                elif isinstance(value, (dict, list)):
                                    result = find_video_url(value)
                                    if result:
                                        return result
                        elif isinstance(data, list):
                            for item in data:
                                result = find_video_url(item)
                                if result:
                                    return result
                        return None
                    
                    video_url = find_video_url(json_data)
                    if video_url:
                        print(f"从JSON数据中找到视频地址：{video_url}")
                        break
                except json.JSONDecodeError:
                    print("JSON解析失败，尝试下一个模式")
        
        # 2. 如果没有从JSON中找到，尝试使用正则表达式
        if not video_url:
            print("尝试使用正则表达式提取视频地址...")
            patterns = [
                # 格式1: "video": {"play_addr": {"url_list": ["https://..."]
                r'"video":\s*{"play_addr":\s*{"url_list":\s*\["([^"]+)"',
                # 格式2: "video": {"url": "https://..."
                r'"video":\s*{"url":\s*"([^"]+)"',
                # 格式3: "videoUrl": "https://..."
                r'"videoUrl":\s*"([^"]+)"',
                # 格式4: "video_url": "https://..."
                r'"video_url":\s*"([^"]+)"',
                # 格式5: 直接匹配mp4链接
                r'https://[^\s"]+\.mp4',
                # 格式6: "main_url": "https://..."
                r'"main_url":\s*"([^"]+)"',
                # 格式7: "play_url": "https://..."
                r'"play_url":\s*"([^"]+)"',
                # 格式8: "url": "https://..." （在video对象内）
                r'video[^}]*"url"\s*:\s*"([^"]+)"',
                # 格式9: 匹配包含video的链接
                r'https://[^\s"]*video[^\s"]*',
                # 格式10: 匹配xhsvideo.com域名的链接
                r'https://[^\s"]*xhsvideo[^\s"]*',
                # 格式11: 匹配带有video参数的链接
                r'https://[^\s"]+\?.*?video[^\s"]*',
                # 格式12: 匹配较长的视频链接
                r'https://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}/[a-zA-Z0-9\-\._~:/?#[\\\]@!\$&\'\(\)\*\+,;=.]+video[a-zA-Z0-9\-\._~:/?#[\\\]@!\$&\'\(\)\*\+,;=.]+'
            ]
            
            potential_video_urls = []
            for i, pattern in enumerate(patterns):
                print(f"尝试模式 {i+1}: {pattern}")
                matches = re.findall(pattern, response.text)
                if matches:
                    for match in matches:
                        potential_video_urls.append(match)
                        print(f"找到潜在视频地址：{match}")
            
            # 过滤掉非视频文件
            non_video_extensions = ['.ico', '.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.json', '.svg', '.txt', '.html']
            valid_video_urls = []
            
            for url in potential_video_urls:
                url_lower = url.lower()
                # 检查是否包含非视频扩展名
                if not any(ext in url_lower for ext in non_video_extensions):
                    # 检查是否包含明显不是视频的关键词
                    if not any(keyword in url_lower for keyword in ['icon', 'logo', 'image', 'css', 'js', 'json']):
                        valid_video_urls.append(url)
                        print(f"验证为有效视频地址：{url}")
            
            if valid_video_urls:
                video_url = valid_video_urls[0]
                print(f"从有效视频地址中选择：{video_url}")
        
        # 3. 如果没有找到，尝试从页面中提取所有链接
        if not video_url:
            print("尝试提取所有链接...")
            all_links = re.findall(r'https://[^\s"]+', response.text)
            print(f"找到 {len(all_links)} 个链接")
            
            # 过滤出可能的视频链接
            video_keywords = ['video', 'mp4', 'xhsvideo', 'play', 'main', 'source', 'media']
            non_video_extensions = ['.ico', '.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.json', '.svg', '.txt', '.html']
            video_links = []
            
            for link in all_links:
                link_lower = link.lower()
                
                # 过滤掉非视频文件扩展名
                if any(ext in link_lower for ext in non_video_extensions):
                    print(f"过滤掉非视频文件：{link}")
                    continue
                
                # 过滤掉明显不是视频的链接
                if 'icon' in link_lower or 'logo' in link_lower or 'image' in link_lower:
                    print(f"过滤掉非视频链接：{link}")
                    continue
                
                # 保留可能的视频链接
                if any(keyword in link_lower for keyword in video_keywords):
                    video_links.append(link)
                    print(f"可能的视频链接：{link}")
            
            if video_links:
                video_url = video_links[0]
                print(f"从所有链接中选择视频地址：{video_url}")
            else:
                # 如果没有找到视频链接，尝试从所有链接中选择一个可能的视频地址
                print("尝试从所有链接中选择可能的视频地址...")
                for link in all_links:
                    link_lower = link.lower()
                    if not any(ext in link_lower for ext in non_video_extensions):
                        if 'xhscdn' in link_lower or 'video' in link_lower:
                            video_url = link
                            print(f"选择可能的视频地址：{link}")
                            break
        
        # 4. 如果仍然没有找到，使用模拟数据
        if not video_url:
            print("未找到视频地址，使用模拟数据")
            video_url = "https://example.com/sample_video.mp4"
        
        # 修复视频地址（如果需要）
        video_url = video_url.replace("\\u0026", "&")
        video_url = video_url.replace("\\/", "/")
        video_url = video_url.split('?')[0]  # 去除查询参数
        
        print(f"最终视频地址：{video_url}")
        return video_url
    except Exception as e:
        print(f"解析小红书链接失败：{str(e)}")
        # 返回模拟视频地址，确保流程能够继续
        return "https://example.com/sample_video.mp4"

def download_video(video_url, output_path):
    """
    下载视频文件，支持重试机制
    """
    try:
        # 检查是否为模拟视频地址
        if video_url == "https://example.com/sample_video.mp4":
            print("使用模拟视频数据")
            # 创建一个空的视频文件作为占位符
            with open(output_path, 'w') as f:
                f.write('')
            return output_path
        
        # 检查是否为视频服务器域名（无具体路径）
        if video_url in ['https://sns-video-qc.xhscdn.com', 'https://sns-video-hw.xhscdn.com', 'https://sns-video-bd.xhscdn.com', 'https://sns-video-qn.xhscdn.com']:
            print(f"检测到视频服务器域名：{video_url}，使用模拟数据")
            # 创建一个空的视频文件作为占位符
            with open(output_path, 'w') as f:
                f.write('')
            return output_path
        
        # 尝试多种User-Agent
        user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        
        for i, user_agent in enumerate(user_agents):
            try:
                headers = {
                    "User-Agent": user_agent,
                    "Referer": "https://www.xiaohongshu.com/",
                    "Accept": "*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive"
                }
                print(f"正在下载视频（尝试 {i+1}/{len(user_agents)}）：{video_url}")
                response = requests.get(video_url, headers=headers, stream=True, timeout=60)
                
                # 检查响应状态码
                if response.status_code == 403:
                    print(f"视频下载失败：403 Forbidden（尝试 {i+1}/{len(user_agents)}）")
                    if i < len(user_agents) - 1:
                        continue
                    else:
                        raise Exception("所有User-Agent尝试均失败，视频需要授权")
                
                response.raise_for_status()
                
                # 计算文件大小
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                
                # 检查下载的文件大小
                if downloaded_size < 1000:
                    raise Exception(f"下载的文件太小（{downloaded_size}字节），可能下载失败")
                
                print(f"视频下载完成，大小：{downloaded_size}字节")
                return output_path
                
            except Exception as e:
                print(f"下载尝试 {i+1} 失败：{str(e)}")
                if i < len(user_agents) - 1:
                    continue
                else:
                    raise e
                    
    except Exception as e:
        print(f"下载视频失败（将使用模拟数据）：{str(e)}")
        # 创建一个空的视频文件作为占位符
        with open(output_path, 'w') as f:
            f.write('')
        return output_path

def extract_audio(video_path, audio_path):
    """
    使用ffmpeg-python提取音频轨道
    """
    try:
        # 检查视频文件是否存在且不为空
        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            raise Exception("视频文件不存在或为空")
        
        # 使用ffmpeg-python提取音频
        import ffmpeg
        print(f"正在从视频提取音频：{video_path}")
        
        # 构建ffmpeg命令
        (ffmpeg
         .input(video_path)
         .output(audio_path, format='wav', acodec='pcm_s16le', ar='16000', ac='1')
         .overwrite_output()
         .run(capture_stdout=True, capture_stderr=True)
         )
        
        # 检查生成的音频文件
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise Exception("音频文件生成失败")
        
        print(f"音频提取完成：{audio_path}")
        print(f"音频文件大小：{os.path.getsize(audio_path)}字节")
        return audio_path
    except ffmpeg.Error as e:
        print(f"FFmpeg执行失败：{e.stderr.decode('utf-8')}")
        raise Exception(f"FFmpeg执行失败：{e.stderr.decode('utf-8')}")
    except ImportError:
        print("ffmpeg-python未安装，尝试使用系统命令")
        # 降级到使用系统命令
        try:
            import subprocess
            print(f"使用系统命令提取音频：{video_path}")
            command = [
                'ffmpeg', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1',
                audio_path, '-y'
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"系统命令执行失败：{result.stderr}")
            print(f"音频提取完成：{audio_path}")
            return audio_path
        except Exception as e:
            print(f"系统命令提取失败：{str(e)}")
            raise Exception(f"音频提取失败：{str(e)}")
    except Exception as e:
        print(f"音频提取失败：{str(e)}")
        raise Exception(f"音频提取失败：{str(e)}")

# 模拟数据 - 用于演示
MOCK_SCRIPT = """大家好，欢迎来到我的小红书频道！今天我要给大家分享一个超级实用的生活小技巧，就是如何在3分钟内快速整理好你的衣柜。

首先，我们需要准备一些工具：几个收纳盒、衣架、还有分类标签。然后，按照季节把衣服分开，夏天的衣服放在一起，冬天的衣服放在一起。

接下来，我们要按照颜色进行排列，这样找衣服的时候会更方便。另外，对于那些不常穿的衣服，我们可以用真空袋压缩起来，节省空间。

最后，记得定期整理你的衣柜，这样才能保持整洁。好了，今天的分享就到这里，如果你觉得有用的话，记得点赞收藏哦！我们下期再见，拜拜！"""

# 临时文件存储目录
TEMP_DIR = tempfile.gettempdir()

@app.post("/api/extract-from-url")
async def extract_from_url(data: dict):
    """
    Extract transcript from XHS video link via Coze workflow API.
    """
    try:
        print(f"Received API request: {data}")
        url = data.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="缺少url参数")

        # Extract URL from share text
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]，。！？；：、，]+'
        urls = re.findall(url_pattern, url)
        extracted_url = urls[0] if urls else url

        # Validate URL
        if not extracted_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="无效的视频链接")
        if "xiaohongshu.com" not in extracted_url and "xhslink.com" not in extracted_url:
            raise HTTPException(status_code=400, detail="仅支持小红书视频链接")

        # Call Coze API to extract transcript
        print(f"[Extract] Calling Coze API for: {extracted_url}")
        transcript = extract_transcript_via_coze(extracted_url)

        # Clean and validate
        script = clean_and_format_text(transcript)
        validation = validate_extracted_content(script)
        print(f"Validation: score={validation['quality_score']:.2f}, valid={validation['is_valid']}")

        # Optionally get note info from XHS-Downloader (non-blocking, best effort)
        note_info = {}
        if check_xhs_downloader_status():
            try:
                note_info = download_via_xhs_downloader(extracted_url, download_file=False)
            except Exception as e:
                print(f"[XHS-Downloader] Info fetch failed (non-critical): {e}")

        return {
            "success": True if validation["is_valid"] else False,
            "message": "文案提取成功" if validation["is_valid"] else "提取的内容可能存在问题",
            "data": {
                "script": script,
                "validation": validation,
                "video_info": {
                    "url": url,
                    "source": "coze_workflow",
                    "note_info": note_info,
                },
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取失败：{str(e)}")

@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """
    上传视频文件并提取文案
    """
    try:
        print(f"收到视频文件上传请求：{file.filename}")
        
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="仅支持视频文件")
        
        # 验证文件扩展名
        allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的视频格式，仅支持：{', '.join(allowed_extensions)}")
        
        # 保存上传的视频文件
        video_filename = f"uploaded_video_{datetime.now().timestamp()}{file_ext}"
        video_path = os.path.join(TEMP_DIR, video_filename)
        
        print(f"保存视频文件到：{video_path}")
        with open(video_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # 检查文件大小
        file_size = os.path.getsize(video_path)
        print(f"视频文件大小：{file_size}字节")
        
        if file_size < 1000:
            os.remove(video_path)
            raise HTTPException(status_code=400, detail="视频文件过小或为空")
        
        if file_size > 500 * 1024 * 1024:  # 500MB限制
            os.remove(video_path)
            raise HTTPException(status_code=400, detail="视频文件过大，请上传500MB以内的文件")
        
        # 使用librosa提取音频并进行语音识别
        try:
            print(f"开始处理视频文件：{video_path}")
            
            # 使用librosa提取音频
            import librosa
            import numpy as np
            
            print("使用librosa提取音频")
            
            # 加载音频，librosa可以自动处理视频文件
            y, sr = librosa.load(video_path, sr=16000, mono=True)
            
            audio_duration = len(y) / sr
            print(f"音频加载完成，采样率：{sr}Hz，音频长度：{audio_duration:.2f}秒")
            
            # 检查音频时长
            if audio_duration < 1:
                os.remove(video_path)
                raise HTTPException(status_code=400, detail="视频时长过短，请上传至少1秒的视频")
            
            if audio_duration > 900:  # 15分钟
                os.remove(video_path)
                raise HTTPException(status_code=400, detail="视频时长过长，请上传15分钟以内的视频")
            
            # 使用Whisper进行语音识别
            import whisper
            print("使用Whisper进行语音识别")
            
            # 加载模型
            model = whisper.load_model("base")
            
            # 直接使用librosa提取的音频数据
            audio_float32 = y.astype(np.float32)
            
            print(f"音频数据形状：{audio_float32.shape}")
            
            # 使用Whisper进行语音识别
            result = model.transcribe(audio_float32, language="zh", fp16=False)
            
            # 获取识别的文本
            script = result["text"].strip()
            
            if not script:
                os.remove(video_path)
                raise HTTPException(status_code=500, detail="语音识别结果为空，可能视频中没有语音内容")
            
            print(f"语音识别完成，文本长度：{len(script)}字符")
            print(f"识别到的文本：{script[:100]}...")
            
        except ImportError as e:
            print(f"导入库失败：{str(e)}")
            os.remove(video_path)
            raise HTTPException(status_code=500, detail=f"缺少必要的库：{str(e)}")
        except Exception as e:
            print(f"语音识别失败：{str(e)}")
            os.remove(video_path)
            raise HTTPException(status_code=500, detail=f"语音识别失败：{str(e)}")
        
        # 文本清洗与格式化
        script = clean_and_format_text(script)
        print("文本清洗完成")
        
        # 内容校验
        validation = validate_extracted_content(script)
        print(f"内容校验结果：质量分数={validation['quality_score']:.2f}, 有效={validation['is_valid']}")
        
        # 清理临时文件
        if os.path.exists(video_path):
            os.remove(video_path)
        print("临时文件清理完成")
        
        # 返回结果
        return {
            "success": True,
            "message": "文案提取成功",
            "data": {
                "script": script,
                "validation": validation,
                "video_info": {
                    "filename": file.filename,
                    "size": f"{file_size / (1024 * 1024):.2f}MB",
                    "duration": f"{int(audio_duration // 60)}:{int(audio_duration % 60):02d}"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败：{str(e)}")

@app.post("/api/export")
async def export_script(data: dict):
    """
    导出文案
    """
    try:
        script = data.get("script")
        format = data.get("format")
        
        if not script:
            raise HTTPException(status_code=400, detail="缺少script参数")
        if not format:
            raise HTTPException(status_code=400, detail="缺少format参数")
        
        if format == "txt":
            # 生成TXT文件
            file_path = os.path.join(TEMP_DIR, f"script_{datetime.now().timestamp()}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(script)
            return FileResponse(path=file_path, filename="小红书口播文案.txt", media_type="text/plain")
        elif format == "json":
            # 生成JSON文件
            file_path = os.path.join(TEMP_DIR, f"script_{datetime.now().timestamp()}.json")
            json_data = {
                "title": "小红书口播文案",
                "content": script,
                "timestamp": datetime.now().isoformat(),
                "source": "小红书视频"
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            return FileResponse(path=file_path, filename="小红书口播文案.json", media_type="application/json")
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")

@app.post("/api/analyze-script")
async def analyze_script_endpoint(data: dict):
    """
    分析口播稿的语言风格、叙事框架等特点
    """
    try:
        script = data.get("script")
        if not script:
            raise HTTPException(status_code=400, detail="缺少script参数")
        
        # 分析口播稿
        analysis = analyze_script(script)
        
        return {
            "success": True,
            "message": "口播稿分析成功",
            "data": analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败：{str(e)}")

@app.post("/api/upload-reference")
async def upload_reference(data: dict):
    """
    Upload reference blogger transcript for style analysis.
    Supports: XHS video URL (via Coze) or direct text input.
    """
    try:
        video_url = data.get("video_url")
        script_text = data.get("script_text")

        if not video_url and not script_text:
            raise HTTPException(status_code=400, detail="缺少视频链接或文本内容")

        extracted_script = ""

        if video_url:
            # Validate URL
            if not video_url.startswith(('http://', 'https://')):
                raise HTTPException(status_code=400, detail="无效的视频链接")
            if "xiaohongshu.com" not in video_url and "xhslink.com" not in video_url:
                raise HTTPException(status_code=400, detail="仅支持小红书视频链接")

            # Extract transcript via Coze API
            print(f"[Reference] Extracting transcript via Coze: {video_url}")
            extracted_script = extract_transcript_via_coze(video_url)
            extracted_script = clean_and_format_text(extracted_script)
        elif script_text:
            extracted_script = clean_and_format_text(script_text)

        # Analyze the script
        analysis_result = analyze_script(extracted_script)

        return {
            "success": True,
            "message": "参考口播稿上传并分析成功",
            "data": {
                "analysis": analysis_result,
                "script": extracted_script,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败：{str(e)}")

def analyze_product_bf(content):
    """
    分析产品背景文件(BF)，提取核心信息、卖点及宣传需求
    """
    try:
        # 1. 基础信息提取
        product_analysis = {
            "product_name": "",
            "core_features": [],
            "selling_points": [],
            "target_audience": [],
            "promotion_needs": [],
            "usage_scenarios": [],
            "competitive_advantages": [],
            "price_info": ""
        }
        
        # 提取产品名称
        product_name_patterns = [
            r'产品名称[:：]\s*(.*?)[\n，。！？；：]',
            r'品牌[:：]\s*(.*?)[\n，。！？；：]',
            r'名称[:：]\s*(.*?)[\n，。！？；：]',
            r'(\S+)\s*是\s*[一款一种].*?产品'
        ]
        
        for pattern in product_name_patterns:
            matches = re.findall(pattern, content)
            if matches:
                product_analysis["product_name"] = matches[0].strip()
                break
        
        # 提取核心功能
        feature_patterns = [
            r'功能[:：]\s*([^\n，。！？；：]+)',
            r'特点[:：]\s*([^\n，。！？；：]+)',
            r'核心功能[:：]\s*([^\n，。！？；：]+)',
            r'主要功能[:：]\s*([^\n，。！？；：]+)',
            r'支持.*?([^，。！？；：]+)',
            r'可以.*?([^，。！？；：]+)',
            r'能够.*?([^，。！？；：]+)'
        ]
        
        for pattern in feature_patterns:
            matches = re.findall(pattern, content)
            product_analysis["core_features"].extend([m.strip() for m in matches])
        
        # 提取卖点
        selling_point_patterns = [
            r'卖点[:：]\s*([^\n，。！？；：]+)',
            r'优势[:：]\s*([^\n，。！？；：]+)',
            r'好处[:：]\s*([^\n，。！？；：]+)',
            r'价值[:：]\s*([^\n，。！？；：]+)',
            r'值得.*?([^，。！？；：]+)',
            r'推荐.*?([^，。！？；：]+)'
        ]
        
        for pattern in selling_point_patterns:
            matches = re.findall(pattern, content)
            product_analysis["selling_points"].extend([m.strip() for m in matches])
        
        # 提取目标受众
        audience_patterns = [
            r'目标用户[:：]\s*([^\n，。！？；：]+)',
            r'适合.*?([^，。！？；：]+)',
            r'针对.*?([^，。！？；：]+)',
            r'面向.*?([^，。！？；：]+)',
            r'受众[:：]\s*([^\n，。！？；：]+)'
        ]
        
        for pattern in audience_patterns:
            matches = re.findall(pattern, content)
            product_analysis["target_audience"].extend([m.strip() for m in matches])
        
        # 提取宣传需求
        promotion_patterns = [
            r'宣传需求[:：]\s*([^\n，。！？；：]+)',
            r'营销目标[:：]\s*([^\n，。！？；：]+)',
            r'推广重点[:：]\s*([^\n，。！？；：]+)',
            r'需要.*?([^，。！？；：]+)',
            r'希望.*?([^，。！？；：]+)'
        ]
        
        for pattern in promotion_patterns:
            matches = re.findall(pattern, content)
            product_analysis["promotion_needs"].extend([m.strip() for m in matches])
        
        # 提取使用场景
        scenario_patterns = [
            r'使用场景[:：]\s*([^\n，。！？；：]+)',
            r'适用场景[:：]\s*([^\n，。！？；：]+)',
            r'场景[:：]\s*([^\n，。！？；：]+)',
            r'在.*?时使用',
            r'适合在.*?使用'
        ]
        
        for pattern in scenario_patterns:
            matches = re.findall(pattern, content)
            product_analysis["usage_scenarios"].extend([m.strip() for m in matches])
        
        # 提取竞争优势
        advantage_patterns = [
            r'竞争优势[:：]\s*([^\n，。！？；：]+)',
            r'相比.*?优势[:：]\s*([^\n，。！？；：]+)',
            r'优于.*?([^，。！？；：]+)',
            r'比.*?更.*?([^，。！？；：]+)'
        ]
        
        for pattern in advantage_patterns:
            matches = re.findall(pattern, content)
            product_analysis["competitive_advantages"].extend([m.strip() for m in matches])
        
        # 提取价格信息
        price_patterns = [
            r'价格[:：]\s*([^\n，。！？；：]+)',
            r'售价[:：]\s*([^\n，。！？；：]+)',
            r'定价[:：]\s*([^\n，。！？；：]+)',
            r'\d+\.?\d*\s*元'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, content)
            if matches:
                product_analysis["price_info"] = matches[0].strip()
                break
        
        # 去重处理
        for key in product_analysis:
            if isinstance(product_analysis[key], list):
                product_analysis[key] = list(set(product_analysis[key]))
        
        return product_analysis
    except Exception as e:
        print(f"产品背景文件分析失败：{str(e)}")
        return {"error": str(e)}

@app.post("/api/upload-bf")
async def upload_bf(data: dict):
    """
    上传产品背景文件(BF)并分析
    """
    try:
        bf_content = data.get("content")
        if not bf_content:
            raise HTTPException(status_code=400, detail="缺少产品背景文件内容")
        
        # 分析产品背景文件
        product_analysis = analyze_product_bf(bf_content)
        
        return {
            "success": True,
            "message": "产品背景文件分析成功",
            "data": product_analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败：{str(e)}")

@app.post("/api/upload-bf-file")
async def upload_bf_file(file: UploadFile = File(...)):
    """
    上传产品背景文件(BF)文件并分析
    """
    try:
        # 读取文件内容
        content = await file.read()
        content = content.decode('utf-8')
        
        # 分析产品背景文件
        product_analysis = analyze_product_bf(content)
        
        return {
            "success": True,
            "message": "产品背景文件分析成功",
            "data": product_analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败：{str(e)}")

def generate_script(reference_analysis, product_info,
                     blogger_persona="", historical_articles="",
                     reference_transcripts=None):
    """
    Two-phase prompt-driven script generation.
    Phase 1: Analyze reference style (returns style summary).
    Phase 2: Generate new script using style + product + history.
    Returns dict with both phase outputs.
    """
    try:
        if reference_transcripts is None:
            reference_transcripts = []

        # ---- Phase 1: Style Analysis ----
        style_summary = _build_style_summary(reference_analysis)

        # ---- Phase 2: Script Generation ----
        # Build the prompt context
        persona = blogger_persona or "小红书母婴赛道宝爸类型博主"

        # Extract product details
        if isinstance(product_info, dict):
            product_name = product_info.get("product_name", "新产品")
            product_text = _format_product_info(product_info)
        else:
            product_name = "新产品"
            product_text = str(product_info) if product_info else ""

        # Build generation prompt for display
        prompt = _build_generation_prompt(
            persona=persona,
            style_summary=style_summary,
            product_name=product_name,
            product_text=product_text,
            historical_articles=historical_articles,
            reference_transcripts=reference_transcripts,
        )

        # For now, generate locally using template + style adaptation
        # This will be replaced by LLM API call when available
        script = _generate_from_template(
            reference_analysis=reference_analysis,
            product_info=product_info if isinstance(product_info, dict) else {},
            persona=persona,
            style_summary=style_summary,
        )

        return {
            "style_analysis": style_summary,
            "generation_prompt": prompt,
            "script": script,
        }
    except Exception as e:
        print(f"Script generation failed: {str(e)}")
        return {
            "style_analysis": "",
            "generation_prompt": "",
            "script": f"生成失败：{str(e)}",
        }


def _build_style_summary(analysis: dict) -> str:
    """Build a readable style summary from analysis result."""
    parts = []
    style = analysis.get("style", {})
    narrative = analysis.get("narrative", {})
    content = analysis.get("content", {})
    emotion = analysis.get("emotion", {})

    if style.get("tone"):
        parts.append(f"【语言风格】语气{style['tone']}")
    if style.get("style"):
        parts.append(f"  特点：{', '.join(style['style'])}")
    if style.get("features"):
        parts.append(f"  用词特征：{', '.join(style['features'])}")

    if narrative.get("body"):
        parts.append(f"【叙事框架】主体结构：{', '.join(narrative['body'])}")
    if narrative.get("transitions"):
        parts.append(f"  过渡词：{', '.join(narrative['transitions'])}")

    if content.get("organization"):
        parts.append(f"【内容组织】{', '.join(content['organization'])}")
    if content.get("pace"):
        parts.append(f"  节奏：{content['pace']}")

    if emotion.get("emotion"):
        parts.append(f"【情感表达】倾向：{', '.join(emotion['emotion'])}")
    if emotion.get("intensity"):
        parts.append(f"  强度：{emotion['intensity']}")

    summary = analysis.get("summary", "")
    if summary:
        parts.insert(0, f"【总结】{summary}")

    return "\n".join(parts) if parts else "风格分析数据不足"


def _format_product_info(info: dict) -> str:
    """Format product info dict into readable text."""
    lines = []
    if info.get("product_name"):
        lines.append(f"产品名称：{info['product_name']}")
    if info.get("core_features"):
        lines.append(f"核心功能：{', '.join(info['core_features'][:5])}")
    if info.get("selling_points"):
        lines.append(f"产品卖点：{', '.join(info['selling_points'][:5])}")
    if info.get("target_audience"):
        lines.append(f"目标受众：{', '.join(info['target_audience'][:3])}")
    if info.get("usage_scenarios"):
        lines.append(f"使用场景：{', '.join(info['usage_scenarios'][:3])}")
    if info.get("price_info"):
        lines.append(f"价格信息：{info['price_info']}")
    return "\n".join(lines) if lines else "暂无详细产品信息"


def _build_generation_prompt(persona, style_summary, product_name,
                              product_text, historical_articles,
                              reference_transcripts):
    """Build the full generation prompt (for display or LLM call)."""
    prompt_parts = [
        f"你现在是{persona}。\n",
        "## 参考风格",
        f"以下是你需要模仿的口播风格分析：\n{style_summary}\n",
    ]

    if reference_transcripts:
        prompt_parts.append("## 参考博主原文")
        for i, t in enumerate(reference_transcripts, 1):
            prompt_parts.append(f"博主{i}：\n{t[:500]}{'...' if len(t) > 500 else ''}\n")

    prompt_parts.extend([
        "## 推广商品",
        f"商品名称：{product_name}",
        f"商品信息：\n{product_text}\n",
    ])

    if historical_articles:
        prompt_parts.extend([
            "## 历史文章参考",
            f"以下是你之前写过的文章，请保持一致的个人风格：\n{historical_articles}\n",
        ])

    prompt_parts.extend([
        "## 写作要求",
        "1. 严格模仿参考风格中总结的框架结构",
        "2. 融入商品的核心卖点和使用场景",
        "3. 保持与历史文章一致的个人风格和语气",
        "4. 口播稿时长控制在 1-2 分钟左右",
        "5. 语言自然口语化，适合视频口播录制",
        "6. 包含开头引入、主体测评/分享、结尾总结推荐三个部分",
        "\n请直接输出完整的口播稿文案：",
    ])

    return "\n".join(prompt_parts)


def _generate_from_template(reference_analysis, product_info,
                             persona, style_summary):
    """
    Template-based script generation (fallback when no LLM available).
    Uses reference style analysis to adapt template output.
    """
    style = reference_analysis.get("style", {})
    narrative = reference_analysis.get("narrative", {})
    emotion = reference_analysis.get("emotion", {})

    product_name = product_info.get("product_name", "新产品")
    core_features = product_info.get("core_features", [])
    selling_points = product_info.get("selling_points", [])
    target_audience = product_info.get("target_audience", [])
    usage_scenarios = product_info.get("usage_scenarios", [])
    price_info = product_info.get("price_info", "")

    tone = style.get("tone", "友好亲切")
    body_structure = narrative.get("body", ["叙述式"])

    # Opening
    if "推荐种草" in tone:
        opening = f"家人们，今天必须给你们安利这款{product_name}，我已经用了一段时间，真的太好用了！"
    elif "教程指导" in tone:
        opening = f"大家好，今天给大家带来{product_name}的详细分享，让你快速了解这款产品！"
    else:
        opening = f"大家好，今天我要给大家分享一个超级实用的好物——{product_name}，绝对是生活中的必备神器！"

    # Body
    body_parts = []
    if "对比式" in body_structure:
        if selling_points:
            body_parts.append(f"相比市面上其他同类产品，{product_name}最大的优势是{selling_points[0]}。")
        if core_features:
            body_parts.append(f"它的{core_features[0]}功能比其他产品更加出色，使用体验更好。")
    elif "步骤式" in body_structure:
        if core_features:
            body_parts.append(f"首先，{product_name}的核心功能是{core_features[0]}，这一点真的非常实用。")
        if selling_points:
            body_parts.append(f"然后，它的最大卖点是{selling_points[0]}，相比其他产品有很大优势。")
        if usage_scenarios:
            body_parts.append(f"接下来，它特别适合{usage_scenarios[0]}，使用场景非常广泛。")
    else:
        if core_features:
            body_parts.append(f"{product_name}的核心功能包括{'、'.join(core_features[:3])}，这些功能真的非常实用。")
        if selling_points:
            body_parts.append(f"它的主要卖点是{'、'.join(selling_points[:3])}，绝对值得入手。")
        if usage_scenarios:
            body_parts.append(f"这款产品特别适合{'、'.join(usage_scenarios[:3])}，使用场景非常广泛。")
        if target_audience:
            body_parts.append(f"它的目标用户是{'、'.join(target_audience[:3])}，是为你们量身打造的。")

    if price_info:
        body_parts.append(f"关于价格方面，{product_name}的定价是{price_info}，性价比非常高。")

    # Closing
    if "推荐种草" in tone:
        closing = "话不多说，链接我会放在评论区，想要的小伙伴们赶紧去看看吧！记得点赞收藏，手慢无哦！"
    else:
        closing = "好了，今天的分享就到这里，如果你们觉得有用的话，记得点赞收藏哦！有什么问题可以在评论区留言。我们下期再见！"

    parts = [opening] + body_parts + [closing]
    script = "\n\n".join(parts)

    # Apply emotion intensity
    intensity = emotion.get("intensity", "中等")
    if intensity == "强烈":
        import random
        emphasis_words = ["超级", "非常", "特别", "真的", "太"]
        for word in ["好用", "推荐", "喜欢", "实用"]:
            if word in script and random.random() > 0.5:
                script = script.replace(word, f"{random.choice(emphasis_words)}{word}", 1)

    return clean_and_format_text(script)

@app.post("/api/generate-script")
async def generate_script_endpoint(data: dict):
    """
    Two-phase script generation:
    Phase 1 - style analysis from reference; Phase 2 - script generation.
    """
    try:
        reference_analysis = data.get("reference_analysis")
        product_info = data.get("product_info")
        blogger_persona = data.get("blogger_persona", "")
        historical_articles = data.get("historical_articles", "")
        reference_transcripts = data.get("reference_transcripts", [])

        if not reference_analysis:
            raise HTTPException(status_code=400, detail="缺少参考博主分析结果")
        if not product_info:
            raise HTTPException(status_code=400, detail="缺少产品信息")

        result = generate_script(
            reference_analysis=reference_analysis,
            product_info=product_info,
            blogger_persona=blogger_persona,
            historical_articles=historical_articles,
            reference_transcripts=reference_transcripts,
        )

        return {
            "success": True,
            "message": "口播稿生成成功",
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")


@app.get("/api/check-services")
async def check_services():
    """Health check for external services."""
    xhs_ok = check_xhs_downloader_status()
    coze_ok = bool(COZE_API_TOKEN)
    return {
        "xhs_downloader": {
            "available": xhs_ok,
            "url": XHS_DOWNLOADER_API,
        },
        "coze_api": {
            "configured": coze_ok,
            "workflow_id": COZE_WORKFLOW_ID,
        },
    }

@app.get("/")
async def root():
    """
    根路径 - 返回前端HTML页面
    """
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)