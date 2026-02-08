#!/usr/bin/env python3
"""
测试视频文件上传功能
"""

import requests
import os

API_URL = "http://localhost:8000"

def test_upload_video():
    """
    测试视频文件上传功能
    """
    print("="*60)
    print("测试视频文件上传功能")
    print("="*60)
    
    # 检查是否有测试视频文件
    test_video_path = "test_video.mp4"
    
    if not os.path.exists(test_video_path):
        print(f"❌ 测试视频文件不存在：{test_video_path}")
        print("请准备一个测试视频文件（MP4格式）")
        return False
    
    # 获取文件大小
    file_size = os.path.getsize(test_video_path)
    print(f"📁 视频文件：{test_video_path}")
    print(f"📏 文件大小：{file_size / (1024 * 1024):.2f}MB")
    
    # 检查文件大小限制
    if file_size > 500 * 1024 * 1024:
        print("❌ 视频文件过大，请上传500MB以内的文件")
        return False
    
    # 上传视频文件
    print("\n📤 正在上传视频文件...")
    
    try:
        with open(test_video_path, 'rb') as f:
            files = {'file': (test_video_path, f, 'video/mp4')}
            response = requests.post(f"{API_URL}/api/upload-video", files=files)
        
        print(f"📡 响应状态码：{response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 上传成功！")
            print(f"📝 提取的文案：")
            print("-"*60)
            print(data['data']['script'])
            print("-"*60)
            print(f"\n📊 视频信息：")
            print(f"   文件名：{data['data']['video_info']['filename']}")
            print(f"   大小：{data['data']['video_info']['size']}")
            print(f"   时长：{data['data']['video_info']['duration']}")
            print(f"\n🎯 内容校验：")
            print(f"   质量分数：{data['data']['validation']['quality_score']*100:.1f}%")
            print(f"   是否有效：{data['data']['validation']['is_valid']}")
            
            if data['data']['validation']['issues']:
                print(f"   问题：{', '.join(data['data']['validation']['issues'])}")
            if data['data']['validation']['warnings']:
                print(f"   警告：{', '.join(data['data']['validation']['warnings'])}")
            
            return True
        else:
            print(f"❌ 上传失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 上传过程中出错：{str(e)}")
        return False

def test_extract_from_url():
    """
    测试从URL提取文案功能
    """
    print("\n" + "="*60)
    print("测试从URL提取文案功能")
    print("="*60)
    
    # 测试URL
    test_url = "http://xhslink.com/o/6ERHmvmf6qG"
    print(f"🔗 测试URL：{test_url}")
    
    print("\n📤 正在提取文案...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/extract-from-url",
            json={"url": test_url}
        )
        
        print(f"📡 响应状态码：{response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 提取成功！")
            print(f"📝 提取的文案：")
            print("-"*60)
            print(data['data']['script'])
            print("-"*60)
            print(f"\n📊 视频信息：")
            print(f"   URL：{data['data']['video_info']['url']}")
            print(f"   大小：{data['data']['video_info']['size']}")
            print(f"   时长：{data['data']['video_info']['duration']}")
            print(f"\n🎯 内容校验：")
            print(f"   质量分数：{data['data']['validation']['quality_score']*100:.1f}%")
            print(f"   是否有效：{data['data']['validation']['is_valid']}")
            
            if data['data']['validation']['issues']:
                print(f"   问题：{', '.join(data['data']['validation']['issues'])}")
            if data['data']['validation']['warnings']:
                print(f"   警告：{', '.join(data['data']['validation']['warnings'])}")
            
            return True
        else:
            print(f"❌ 提取失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 提取过程中出错：{str(e)}")
        return False

def main():
    """
    主函数
    """
    print("="*60)
    print("小红书视频文案提取工具 - 功能测试")
    print("="*60)
    print()
    
    # 测试结果
    results = []
    
    # 测试1：视频文件上传
    results.append(("视频文件上传", test_upload_video()))
    
    # 测试2：URL提取
    results.append(("URL提取", test_extract_from_url()))
    
    # 生成测试报告
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    pass_rate = passed_tests / total_tests if total_tests > 0 else 0
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed_tests}/{total_tests} 通过")
    print(f"通过率: {pass_rate*100:.1f}%")
    
    if pass_rate >= 0.5:
        print("\n✅ 测试完成！")
        return 0
    else:
        print("\n❌ 测试未通过，需要进一步优化")
        return 1

if __name__ == "__main__":
    exit(main())