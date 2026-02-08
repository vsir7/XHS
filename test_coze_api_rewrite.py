#!/usr/bin/env python3
"""
测试Coze API文案改写功能
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_coze_api_rewrite():
    """
    测试Coze API文案改写功能
    """
    print("="*60)
    print("测试Coze API文案改写功能")
    print("="*60)
    
    # 测试文案（从之前提取的结果）
    test_script = "宝子可以把需要仿写的\"提炼文案\"发给我哦， 我会按照小红书风格帮你生成笔记哒～比如是美妆好物/旅行攻略/穿搭分享这类内容， 还是具体的干货教程/情感故事？ 可以先给我一份核心文案（比如产品介绍、 攻略步骤、 个人体验等）， 我就能精准拿捏网感+排版啦～ 😉"
    
    # 测试视频URL（可选）
    test_video_url = "https://www.xiaohongshu.com/discovery/item/685366cc0000000011003ee8?app_platform=ios&app_version=9.19.3&share_from_user_hidden=true&xsec_source=app_share&type=video&xsec_token=CBZY2_7hoOenkSRsS_tJFT1R6e7xmayIA5hDc9cRxlG80=&author_share=1&xhsshare=WeixinSession&shareRedId=N0k0OTtLNzw2NzUyOTgwNjY4OTdFNj9P&apptime=1770538843&share_id=fe0d8f9a4b9b42cba542a7e8ee2c8b35"
    
    print(f"📝 测试文案：")
    print("-"*60)
    print(test_script)
    print("-"*60)
    print()
    
    print(f"📹 测试视频URL：")
    print("-"*60)
    print(test_video_url[:100] + "...")
    print("-"*60)
    print()
    
    # 调用API
    print("🔄 正在调用API改写文案...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/rewrite-script",
            json={"script": test_script, "video_url": test_video_url},
            timeout=120
        )
        
        print(f"📡 响应状态码：{response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API调用成功！")
            print(f"消息：{data.get('message', '')}")
            print()
            
            if data.get('success'):
                original_script = data['data']['original_script']
                rewritten_script = data['data']['rewritten_script']
                validation = data['data']['validation']
                
                print(f"📝 原始文案：")
                print("-"*60)
                print(original_script)
                print("-"*60)
                print()
                
                print(f"📝 改写后的文案：")
                print("-"*60)
                print(rewritten_script)
                print("-"*60)
                print()
                
                print(f"📊 文案分析：")
                print(f"   原始文案长度：{len(original_script)} 字符")
                print(f"   改写文案长度：{len(rewritten_script)} 字符")
                print(f"   质量分数：{validation['quality_score']:.2f}")
                print(f"   是否有效：{validation['is_valid']}")
                print(f"   文本长度：{validation.get('text_length', len(rewritten_script))}")
                print(f"   词汇数：{validation.get('word_count', 0)}")
                print(f"   句子数：{validation.get('sentence_count', 0)}")
                
                if validation.get('issues'):
                    print(f"   问题：{', '.join(validation['issues'])}")
                if validation.get('warnings'):
                    print(f"   警告：{', '.join(validation['warnings'])}")
                
                return True
            else:
                print(f"⚠️  API返回失败")
                print(f"消息：{data.get('message', '')}")
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
    print("Coze API文案改写功能测试")
    print("="*60)
    print()
    
    # 测试API
    result = test_coze_api_rewrite()
    
    # 生成测试报告
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    
    if result:
        print("✅ Coze API文案改写功能测试通过")
        return 0
    else:
        print("❌ Coze API文案改写功能测试未通过")
        return 1

if __name__ == "__main__":
    exit(main())