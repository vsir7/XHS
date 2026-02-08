#!/usr/bin/env python3
"""
小红书视频口播稿文案提取工具测试脚本
"""

import requests
import json

# 测试小红书视频链接
# 注意：请替换为真实的小红书视频链接
TEST_URL = "https://www.xiaohongshu.com/explore/64d8c7c6000000001a03b8a8"

def test_extract_from_url():
    """
    测试从小红书链接提取文案
    """
    try:
        print("测试小红书视频链接解析与文案提取...")
        print(f"测试链接：{TEST_URL}")
        print("=" * 60)
        
        # 调用API
        api_url = "http://localhost:8000/api/extract-from-url"
        response = requests.post(api_url, json={"url": TEST_URL})
        
        # 打印响应结果
        print(f"响应状态码：{response.status_code}")
        print(f"响应内容：")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                script = data.get("data", {}).get("script", "")
                print("\n" + "=" * 60)
                print("提取的文案内容：")
                print("=" * 60)
                print(script)
                print("=" * 60)
                print("测试成功！")
            else:
                print("测试失败：" + data.get("message", "未知错误"))
        else:
            print("测试失败：API调用失败")
            
    except Exception as e:
        print(f"测试失败：{str(e)}")

if __name__ == "__main__":
    test_extract_from_url()