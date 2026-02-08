#!/usr/bin/env python3
"""
小红书视频口播稿提取测试脚本
测试10个不同类型的小红书视频，验证提取准确率
"""

import requests
import json
import time
from datetime import datetime

# API端点
API_URL = "http://localhost:8000/api/extract-from-url"

# 测试视频链接（不同类型的小红书视频）
TEST_VIDEOS = [
    {
        "name": "美妆教程",
        "url": "http://xhslink.com/o/example1",
        "description": "美妆博主分享化妆技巧",
        "expected_keywords": ["口红", "粉底", "眼影", "化妆", "教程"]
    },
    {
        "name": "美食分享",
        "url": "http://xhslink.com/o/example2",
        "description": "美食博主分享菜谱",
        "expected_keywords": ["食材", "做法", "步骤", "美味", "食谱"]
    },
    {
        "name": "穿搭推荐",
        "url": "http://xhslink.com/o/example3",
        "description": "穿搭博主分享搭配技巧",
        "expected_keywords": ["搭配", "风格", "时尚", "衣服", "穿搭"]
    },
    {
        "name": "旅行攻略",
        "url": "http://xhslink.com/o/example4",
        "description": "旅行博主分享旅游经验",
        "expected_keywords": ["景点", "攻略", "路线", "美食", "住宿"]
    },
    {
        "name": "健身教程",
        "url": "http://xhslink.com/o/example5",
        "description": "健身博主分享锻炼方法",
        "expected_keywords": ["运动", "锻炼", "动作", "健身", "训练"]
    },
    {
        "name": "数码评测",
        "url": "http://xhslink.com/o/example6",
        "description": "数码博主评测电子产品",
        "expected_keywords": ["手机", "电脑", "性能", "配置", "体验"]
    },
    {
        "name": "家居装修",
        "url": "http://xhslink.com/o/example7",
        "description": "家居博主分享装修经验",
        "expected_keywords": ["装修", "设计", "风格", "家具", "空间"]
    },
    {
        "name": "育儿经验",
        "url": "http://xhslink.com/o/example8",
        "description": "育儿博主分享育儿心得",
        "expected_keywords": ["孩子", "教育", "成长", "育儿", "经验"]
    },
    {
        "name": "职场技巧",
        "url": "http://xhslink.com/o/example9",
        "description": "职场博主分享工作经验",
        "expected_keywords": ["工作", "职场", "技巧", "经验", "发展"]
    },
    {
        "name": "生活小技巧",
        "url": "http://xhslink.com/o/example10",
        "description": "生活博主分享实用技巧",
        "expected_keywords": ["技巧", "方法", "实用", "生活", "方便"]
    }
]

def test_single_video(video_info):
    """
    测试单个视频的提取功能
    """
    print(f"\n{'='*60}")
    print(f"测试视频：{video_info['name']}")
    print(f"描述：{video_info['description']}")
    print(f"链接：{video_info['url']}")
    print(f"{'='*60}")
    
    try:
        # 发送API请求
        start_time = time.time()
        response = requests.post(API_URL, json={"url": video_info["url"]}, timeout=120)
        end_time = time.time()
        
        # 计算响应时间
        response_time = end_time - start_time
        
        # 解析响应
        result = response.json()
        
        # 检查是否成功
        if not result.get("success"):
            print(f"❌ 提取失败：{result.get('message')}")
            return {
                "name": video_info["name"],
                "success": False,
                "error": result.get("message"),
                "response_time": response_time
            }
        
        # 获取提取的文本
        script = result["data"]["script"]
        validation = result["data"].get("validation", {})
        
        print(f"✅ 提取成功")
        print(f"响应时间：{response_time:.2f}秒")
        print(f"文本长度：{len(script)}字符")
        
        if validation:
            print(f"质量分数：{validation.get('quality_score', 0):.2f}")
            print(f"句子数量：{validation.get('sentence_count', 0)}")
            print(f"词汇数量：{validation.get('word_count', 0)}")
            
            if validation.get("warnings"):
                print(f"警告：{', '.join(validation['warnings'])}")
        
        # 检查关键词匹配
        matched_keywords = []
        for keyword in video_info["expected_keywords"]:
            if keyword in script:
                matched_keywords.append(keyword)
        
        keyword_match_rate = len(matched_keywords) / len(video_info["expected_keywords"]) if video_info["expected_keywords"] else 0
        
        print(f"关键词匹配：{matched_keywords}")
        print(f"关键词匹配率：{keyword_match_rate*100:.1f}%")
        
        # 显示提取的文本（前200字符）
        print(f"\n提取的文本预览：")
        print(script[:200] + "..." if len(script) > 200 else script)
        
        return {
            "name": video_info["name"],
            "success": True,
            "script": script,
            "script_length": len(script),
            "validation": validation,
            "matched_keywords": matched_keywords,
            "keyword_match_rate": keyword_match_rate,
            "response_time": response_time
        }
        
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return {
            "name": video_info["name"],
            "success": False,
            "error": "请求超时",
            "response_time": 120
        }
    except Exception as e:
        print(f"❌ 测试失败：{str(e)}")
        return {
            "name": video_info["name"],
            "success": False,
            "error": str(e),
            "response_time": 0
        }

def generate_test_report(results):
    """
    生成测试报告
    """
    print(f"\n{'='*80}")
    print("测试报告")
    print(f"{'='*80}")
    
    # 统计数据
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    success_rate = successful_tests / total_tests if total_tests > 0 else 0
    
    total_response_time = sum(r.get("response_time", 0) for r in results)
    avg_response_time = total_response_time / total_tests if total_tests > 0 else 0
    
    # 质量分数统计
    quality_scores = [r.get("validation", {}).get("quality_score", 0) for r in results if r["success"]]
    avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    # 关键词匹配率统计
    keyword_match_rates = [r.get("keyword_match_rate", 0) for r in results if r["success"]]
    avg_keyword_match_rate = sum(keyword_match_rates) / len(keyword_match_rates) if keyword_match_rates else 0
    
    print(f"总测试数量：{total_tests}")
    print(f"成功数量：{successful_tests}")
    print(f"成功率：{success_rate*100:.1f}%")
    print(f"平均响应时间：{avg_response_time:.2f}秒")
    print(f"平均质量分数：{avg_quality_score*100:.1f}%")
    print(f"平均关键词匹配率：{avg_keyword_match_rate*100:.1f}%")
    
    # 详细结果
    print(f"\n{'='*80}")
    print("详细结果")
    print(f"{'='*80}")
    
    for i, result in enumerate(results, 1):
        status = "✅" if result["success"] else "❌"
        print(f"\n{i}. {status} {result['name']}")
        
        if result["success"]:
            print(f"   文本长度：{result['script_length']}字符")
            print(f"   质量分数：{result.get('validation', {}).get('quality_score', 0)*100:.1f}%")
            print(f"   关键词匹配率：{result.get('keyword_match_rate', 0)*100:.1f}%")
            print(f"   响应时间：{result.get('response_time', 0):.2f}秒")
        else:
            print(f"   错误：{result.get('error', 'Unknown')}")
    
    # 保存报告到文件
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "avg_quality_score": avg_quality_score,
            "avg_keyword_match_rate": avg_keyword_match_rate
        },
        "results": results
    }
    
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print(f"测试报告已保存到：{report_file}")
    print(f"{'='*80}")
    
    return report

def main():
    """
    主函数
    """
    print(f"{'='*80}")
    print("小红书视频口播稿提取测试")
    print(f"{'='*80}")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查API是否可用
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        print("✅ API服务正常运行")
    except:
        print("❌ API服务未启动，请先启动服务：python app.py")
        return
    
    # 执行测试
    results = []
    for i, video_info in enumerate(TEST_VIDEOS, 1):
        print(f"\n进度：{i}/{len(TEST_VIDEOS)}")
        result = test_single_video(video_info)
        results.append(result)
        
        # 等待一段时间，避免请求过快
        if i < len(TEST_VIDEOS):
            time.sleep(2)
    
    # 生成测试报告
    report = generate_test_report(results)
    
    # 最终评估
    print(f"\n{'='*80}")
    print("最终评估")
    print(f"{'='*80}")
    
    success_rate = report["summary"]["success_rate"]
    avg_quality_score = report["summary"]["avg_quality_score"]
    avg_keyword_match_rate = report["summary"]["avg_keyword_match_rate"]
    
    if success_rate >= 0.95 and avg_quality_score >= 0.9 and avg_keyword_match_rate >= 0.8:
        print("✅ 测试通过！提取准确率达到95%以上")
    elif success_rate >= 0.8 and avg_quality_score >= 0.8 and avg_keyword_match_rate >= 0.7:
        print("⚠️ 测试基本通过，但仍有改进空间")
    else:
        print("❌ 测试未通过，需要进一步优化")
    
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()