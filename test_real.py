#!/usr/bin/env python3
"""
小红书视频口播稿文案提取工具测试脚本 - 真实链接测试
"""

import requests
import json

# 测试小红书视频链接
# 请替换为真实的小红书视频链接
TEST_URL = "https://www.xiaohongshu.com/explore/64d8c7c6000000001a03b8a8"

def test_real_xiaohongshu_link():
    """
    测试真实小红书视频链接的解析与文案提取
    """
    try:
        print("测试真实小红书视频链接解析与文案提取...")
        print(f"测试链接：{TEST_URL}")
        print("=" * 80)
        
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
                video_url = data.get("data", {}).get("video_info", {}).get("video_url", "")
                
                print("\n" + "=" * 80)
                print("提取的文案内容：")
                print("=" * 80)
                print(script)
                print("=" * 80)
                
                print("\n" + "=" * 80)
                print("视频信息：")
                print("=" * 80)
                print(f"视频真实地址：{video_url}")
                print("=" * 80)
                print("测试成功！")
            else:
                print("测试失败：" + data.get("message", "未知错误"))
        else:
            print("测试失败：API调用失败")
            
    except Exception as e:
        print(f"测试失败：{str(e)}")

if __name__ == "__main__":
    test_real_xiaohongshu_link()