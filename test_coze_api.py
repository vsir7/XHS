#!/usr/bin/env python3
"""
测试Coze API功能
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_coze_api():
    """
    测试Coze API提取文案功能
    """
    print("="*60)
    print("测试Coze API文案提取功能")
    print("="*60)
    
    # 测试URL（用户提供的小红书视频链接）
    test_url = "https://www.xiaohongshu.com/discovery/item/685366cc0000000011003ee8?app_platform=ios&app_version=9.19.3&share_from_user_hidden=true&xsec_source=app_share&type=video&xsec_token=CBZY2_7hoOenkSRsS_tJFT1R6e7xmayIA5hDc9cRxlG80=&author_share=1&xhsshare=WeixinSession&shareRedId=N0k0OTtLNzw2NzUyOTgwNjY4OTdFNj9P&apptime=1770538843&share_id=fe0d8f9a4b9b42cba542a7e8ee2c8b35"
    
    print(f"📝 测试URL：")
    print("-"*60)
    print(test_url[:100] + "...")
    print("-"*60)
    print()
    
    # 调用API
    print("🔄 正在调用API提取文案...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/extract-from-url",
            json={"url": test_url},
            timeout=120
        )
        
        print(f"📡 响应状态码：{response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API调用成功！")
            print(f"消息：{data.get('message', '')}")
            print()
            
            if data.get('success'):
                script = data['data']['script']
                validation = data['data']['validation']
                video_info = data['data']['video_info']
                
                print(f"📝 提取的文案：")
                print("-"*60)
                print(script)
                print("-"*60)
                print()
                
                print(f"📊 文案分析：")
                print(f"   文案长度：{len(script)} 字符")
                print(f"   质量分数：{validation['quality_score']:.2f}")
                print(f"   是否有效：{validation['is_valid']}")
                print(f"   文本长度：{validation.get('text_length', len(script))}")
                print(f"   词汇数：{validation.get('word_count', 0)}")
                print(f"   句子数：{validation.get('sentence_count', 0)}")
                
                if validation.get('issues'):
                    print(f"   问题：{', '.join(validation['issues'])}")
                
                print()
                print(f"📹 视频信息：")
                print(f"   原始URL：{video_info['url'][:50]}...")
                print(f"   视频URL：{video_info['video_url'][:50]}...")
                print(f"   时长：{video_info['duration']}")
                print(f"   大小：{video_info['size']}")
                
                return True
            else:
                print(f"⚠️  API返回失败")
                print(f"消息：{data.get('message', '')}")
                if 'data' in data:
                    script = data['data'].get('script', '')
                    if script:
                        print(f"文案内容：{script[:200]}...")
                return False
                
        else:
            print(f"❌ API调用失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 请求过程中出错：{str(e)}")
        return False

def main():
    """
    主函数
    """
    print("="*60)
    print("Coze API文案提取功能测试")
    print("="*60)
    print()
    
    # 测试API
    result = test_coze_api()
    
    # 生成测试报告
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    
    if result:
        print("✅ Coze API文案提取功能测试通过")
        return 0
    else:
        print("❌ Coze API文案提取功能测试未通过")
        return 1

if __name__ == "__main__":
    exit(main())