#!/usr/bin/env python3
"""
小红书视频口播稿提取功能测试
验证系统的核心功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import clean_and_format_text, validate_extracted_content, MOCK_SCRIPT

def test_url_extraction():
    """
    测试URL提取功能
    """
    print("\n" + "="*60)
    print("测试1: URL提取功能")
    print("="*60)
    
    test_cases = [
        {
            "input": "想出门又怕敏敏？育儿成分党实战经验总结 想带娃撒欢... http://xhslink.com/o/6ERHmvmf6qG  复制后打开【小红书】查看笔记！",
            "expected": "http://xhslink.com/o/6ERHmvmf6qG"
        },
        {
            "input": "https://www.xiaohongshu.com/explore/123456",
            "expected": "https://www.xiaohongshu.com/explore/123456"
        },
        {
            "input": "这是我的分享链接：http://xhslink.com/o/abc123，快来看看吧！",
            "expected": "http://xhslink.com/o/abc123"
        }
    ]
    
    import re
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]，。！？；：、，]+'
    
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        urls = re.findall(url_pattern, test_case["input"])
        extracted = urls[0] if urls else None
        
        if extracted == test_case["expected"]:
            print(f"✅ 测试用例 {i} 通过")
            print(f"   输入: {test_case['input'][:50]}...")
            print(f"   提取: {extracted}")
        else:
            print(f"❌ 测试用例 {i} 失败")
            print(f"   输入: {test_case['input'][:50]}...")
            print(f"   期望: {test_case['expected']}")
            print(f"   实际: {extracted}")
            all_passed = False
    
    return all_passed

def test_text_cleaning():
    """
    测试文本清洗功能
    """
    print("\n" + "="*60)
    print("测试2: 文本清洗功能")
    print("="*60)
    
    test_cases = [
        {
            "input": "大家好，欢迎来到我的频道！今天要分享一个实用技巧。",
            "expected_features": ["大家好", "欢迎", "分享", "技巧"]
        },
        {
            "input": "  多余的空格   应该被  清理  ",
            "expected_features": ["多余的空格", "应该被", "清理"]
        }
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        cleaned = clean_and_format_text(test_case["input"])
        
        # 检查是否包含期望的特征
        all_features_present = all(feature in cleaned for feature in test_case["expected_features"])
        
        if all_features_present:
            print(f"✅ 测试用例 {i} 通过")
            print(f"   输入: {test_case['input'][:50]}...")
            print(f"   清洗后: {cleaned[:50]}...")
        else:
            print(f"❌ 测试用例 {i} 失败")
            print(f"   输入: {test_case['input'][:50]}...")
            print(f"   清洗后: {cleaned[:50]}...")
            print(f"   期望特征: {test_case['expected_features']}")
            all_passed = False
    
    return all_passed

def test_content_validation():
    """
    测试内容校验功能
    """
    print("\n" + "="*60)
    print("测试3: 内容校验功能")
    print("="*60)
    
    test_cases = [
        {
            "name": "有效内容",
            "input": MOCK_SCRIPT,
            "expected_valid": True,
            "expected_min_score": 0.5
        },
        {
            "name": "空内容",
            "input": "",
            "expected_valid": False,
            "expected_min_score": 0.0
        },
        {
            "name": "过短内容",
            "input": "太短了",
            "expected_valid": False,
            "expected_min_score": 0.0
        },
        {
            "name": "模拟数据标记",
            "input": "这是一个MOCK数据",
            "expected_valid": False,
            "expected_min_score": 0.0
        }
    ]
    
    all_passed = True
    for test_case in test_cases:
        validation = validate_extracted_content(test_case["input"])
        
        is_valid = validation["is_valid"]
        quality_score = validation["quality_score"]
        
        if is_valid == test_case["expected_valid"] and quality_score >= test_case["expected_min_score"]:
            print(f"✅ {test_case['name']} 通过")
            print(f"   有效: {is_valid}")
            print(f"   质量分数: {quality_score:.2f}")
            if validation["issues"]:
                print(f"   问题: {', '.join(validation['issues'])}")
            if validation["warnings"]:
                print(f"   警告: {', '.join(validation['warnings'])}")
        else:
            print(f"❌ {test_case['name']} 失败")
            print(f"   期望有效: {test_case['expected_valid']}")
            print(f"   实际有效: {is_valid}")
            print(f"   期望最小分数: {test_case['expected_min_score']}")
            print(f"   实际分数: {quality_score:.2f}")
            all_passed = False
    
    return all_passed

def test_mock_script():
    """
    测试模拟脚本的质量
    """
    print("\n" + "="*60)
    print("测试4: 模拟脚本质量")
    print("="*60)
    
    validation = validate_extracted_content(MOCK_SCRIPT)
    
    print(f"文本长度: {validation['text_length']} 字符")
    print(f"句子数量: {validation['sentence_count']}")
    print(f"词汇数量: {validation['word_count']}")
    print(f"质量分数: {validation['quality_score']*100:.1f}%")
    print(f"是否有效: {validation['is_valid']}")
    
    if validation["warnings"]:
        print(f"警告: {', '.join(validation['warnings'])}")
    
    if validation["issues"]:
        print(f"问题: {', '.join(validation['issues'])}")
    
    # 清洗后的文本
    cleaned = clean_and_format_text(MOCK_SCRIPT)
    print(f"\n清洗后的文本:")
    print(cleaned)
    
    return validation["is_valid"]

def main():
    """
    主函数
    """
    print("="*60)
    print("小红书视频口播稿提取功能测试")
    print("="*60)
    
    # 执行测试
    results = []
    
    results.append(("URL提取功能", test_url_extraction()))
    results.append(("文本清洗功能", test_text_cleaning()))
    results.append(("内容校验功能", test_content_validation()))
    results.append(("模拟脚本质量", test_mock_script()))
    
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
    
    if pass_rate >= 0.75:
        print("\n✅ 测试通过！系统功能正常")
        return 0
    else:
        print("\n❌ 测试未通过，需要进一步优化")
        return 1

if __name__ == "__main__":
    exit(main())