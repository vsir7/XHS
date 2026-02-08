#!/usr/bin/env python3
"""
测试小红书视频口播稿提取功能
使用真实的小红书视频链接进行测试
"""

import requests
import json
import time

# API端点
API_URL = "http://localhost:8000/api/extract-from-url"

# 测试视频链接
TEST_VIDEO = "想出门又怕敏敏？育儿成分党实战经验总结 想带娃撒欢... http://xhslink.com/o/6ERHmvmf6qG  复制后打开【小红书】查看笔记！"

def test_extraction():
    """
    测试视频提取功能
    """
    print("="*60)
    print("测试小红书视频口播稿提取功能")
    print("="*60)
    print(f"测试视频：{TEST_VIDEO}")
    print("="*60)
    
    try:
        # 发送API请求
        start_time = time.time()
        response = requests.post(API_URL, json={"url": TEST_VIDEO}, timeout=180)
        end_time = time.time()
        
        # 计算响应时间
        response_time = end_time - start_time
        
        # 解析响应
        result = response.json()
        
        print(f"响应状态码：{response.status_code}")
        print(f"响应时间：{response_time:.2f}秒")
        print(f"响应结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 检查是否成功
        if result.get("success"):
            print("\n" + "="*60)
            print("✅ 提取成功！")
            print("="*60)
            
            script = result["data"]["script"]
            print(f"提取的口播稿：")
            print(script)
            print(f"\n文本长度：{len(script)}字符")
            
            # 检查是否包含模拟数据标记
            if "模拟" in script or "MOCK" in script:
                print("\n❌ 警告：提取的内容可能包含模拟数据！")
            else:
                print("\n✅ 确认：提取的内容为真实语音识别结果！")
                
        else:
            print("\n" + "="*60)
            print("❌ 提取失败")
            print("="*60)
            print(f"错误信息：{result.get('message')}")
            
    except requests.exceptions.Timeout:
        print("\n" + "="*60)
        print("❌ 请求超时")
        print("="*60)
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ 测试失败：{str(e)}")
        print("="*60)

def main():
    """
    主函数
    """
    test_extraction()

if __name__ == "__main__":
    main()