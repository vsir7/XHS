#!/usr/bin/env python3
"""
测试文案改写功能
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_rewrite_script():
    """
    测试文案改写功能
    """
    print("="*60)
    print("测试文案改写功能")
    print("="*60)
    
    # 测试文案
    test_script = """
    今天要和大家分享一个非常好用的产品。这个产品的功能很强大，可以解决我们日常生活中的很多问题。
    使用起来非常简单，只需要几个步骤就能完成操作。效果也很明显，使用之后会有很大的改善。
    我已经用了一段时间，感觉非常好，推荐给大家试试。
    """
    
    print(f"📝 原始文案：")
    print("-"*60)
    print(test_script.strip())
    print("-"*60)
    print()
    
    # 调用改写API
    print("🔄 正在改写文案...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/rewrite-script",
            json={"script": test_script}
        )
        
        print(f"📡 响应状态码：{response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 改写成功！")
            print(f"\n📝 改写后的文案：")
            print("-"*60)
            print(data['data']['rewritten_script'])
            print("-"*60)
            
            # 分析改写结果
            original_length = len(test_script)
            rewritten_length = len(data['data']['rewritten_script'])
            
            print(f"\n📊 改写分析：")
            print(f"   原始文案长度：{original_length} 字符")
            print(f"   改写后长度：{rewritten_length} 字符")
            print(f"   长度变化：{rewritten_length - original_length:+d} 字符")
            
            # 检查小红书特征
            rewritten = data['data']['rewritten_script']
            
            print(f"\n🎯 小红书特征检查：")
            
            # 检查emoji
            emoji_count = sum(1 for c in rewritten if c in '✨💖🔥💕🎉💫💗🌟⭐💝')
            print(f"   Emoji数量：{emoji_count}")
            
            # 检查标签
            if '#' in rewritten:
                tags = [tag for tag in rewritten.split() if tag.startswith('#')]
                print(f"   标签数量：{len(tags)}")
                print(f"   标签内容：{', '.join(tags)}")
            
            # 检查小红书用语
            xhs_phrases = ['姐妹们', '家人们', '绝绝子', 'yyds', '太香了', '冲鸭', '必入清单']
            found_phrases = [phrase for phrase in xhs_phrases if phrase in rewritten]
            if found_phrases:
                print(f"   小红书用语：{', '.join(found_phrases)}")
            
            return True
        else:
            print(f"❌ 改写失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 改写过程中出错：{str(e)}")
        return False

def main():
    """
    主函数
    """
    print("="*60)
    print("小红书视频文案改写功能测试")
    print("="*60)
    print()
    
    # 测试改写功能
    result = test_rewrite_script()
    
    # 生成测试报告
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    
    if result:
        print("✅ 文案改写功能测试通过")
        return 0
    else:
        print("❌ 文案改写功能测试未通过")
        return 1

if __name__ == "__main__":
    exit(main())