# -*- coding: utf-8 -*-
"""
题目分析服务 - 完全保持原有功能
从main.py中提取的题目分析相关函数，功能完全不变
"""

import re
from zai import ZhipuAiClient
from ..config.settings import settings

# 保持原有的全局变量初始化
zhipu = ZhipuAiClient(api_key=settings.ai.zhipu_api_key)

def debug_print(*args, **kwargs):
    """受控的调试输出函数 - 保持原有功能"""
    if settings.system.show_debug_info:
        print(*args, **kwargs)

def summarize_problem_with_ai(content: str):
    """使用AI总结题目内容，提取核心算法需求和关键词 - 保持原有功能"""
    print("🤖 正在使用AI分析题目内容...")
    
    system_prompt = """你是一个专业的算法竞赛分析师。请分析给定的题目内容，结构化地提取题目的各个组成部分。

任务：
1. 分析题目需要的算法类型，提取算法关键词并评估每个关键词的重要性权重（0.1-1.0）
2. 解析题目的标准结构：题目描述、输入格式、输出格式、样例（支持多组）
3. 生成简洁的核心问题描述

输出格式严格按照以下模式：
关键词权重：[关键词1:权重1,关键词2:权重2,关键词3:权重3,...]（权重范围0.1-1.0，1.0为最重要）
题目描述：[核心问题描述]
输入格式：[输入的格式要求]
输出格式：[输出的格式要求]
样例组数：[样例的组数，如1、2、3等]
样例1输入：[第一组输入样例]
样例1输出：[第一组输出样例]
样例2输入：[第二组输入样例，如果有的话]
样例2输出：[第二组输出样例，如果有的话]
样例3输入：[第三组输入样例，如果有的话]
样例3输出：[第三组输出样例，如果有的话]
核心问题：[一句话概括核心算法问题]

权重评估标准：
- 1.0：问题的核心算法，直接决定解法
- 0.8-0.9：重要的算法技术，解题必需
- 0.6-0.7：辅助算法，有助于优化
- 0.3-0.5：相关算法，可能用到
- 0.1-0.2：边缘相关，了解即可

示例：
关键词权重：动态规划:1.0,背包问题:0.9,01背包:0.8,优化:0.4
题目描述：有N个物品和一个容量为V的背包，每个物品有重量和价值，求最大价值
输入格式：第一行包含两个整数N和V，接下来N行每行两个整数表示重量和价值
输出格式：一个整数，表示能够获得的最大价值
样例组数：2
样例1输入：4 5\n1 2\n2 4\n3 4\n4 5
样例1输出：8
样例2输入：3 10\n5 10\n4 40\n6 30
样例2输出：70
核心问题：01背包问题求最大价值"""

    user_prompt = f"""请分析以下算法竞赛题目：

{content}

请严格按照要求格式输出分析结果。"""

    try:
        resp = zhipu.chat.completions.create(
            model=settings.ai.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False,
            max_tokens=10000,
            temperature=0.1,
            timeout=180,
            thinking={
                "type":"disabled"
            }
        )
        
        summary = resp.choices[0].message.content
        debug_print("✅ AI分析完成")
        print(f"📋 分析结果：\n{summary}")
        
        # 解析AI输出，返回标准格式
        result = {
            'keywords': [],
            'keyword_weights': {},  # 新增：存储关键词权重
            'problem_description': '',
            'input_format': '',
            'output_format': '',
            'sample_count': 0,
            'samples': [],  # 存储多组样例 [{'input': '...', 'output': '...'}, ...]
            'core_problem': '',
            'original_content': content
        }
        
        # 提取基本信息
        basic_patterns = {
            'keywords_weights': r'关键词权重：([^\n]+)',  # 新增权重解析
            'problem_description': r'题目描述：(.+?)(?=输入格式：|输出格式：|样例组数：|样例\d+输入：|核心问题：|$)',
            'input_format': r'输入格式：(.+?)(?=输出格式：|样例组数：|样例\d+输入：|核心问题：|$)',
            'output_format': r'输出格式：(.+?)(?=样例组数：|样例\d+输入：|核心问题：|$)',
            'core_problem': r'核心问题：([^\n]+)(?=\n|$)'
        }
        
        for key, pattern in basic_patterns.items():
            match = re.search(pattern, summary, re.DOTALL)
            if match:
                value = match.group(1).strip()
                if key == 'keywords_weights':
                    # 解析关键词和权重，并按权重排序
                    keyword_weight_pairs = []
                    try:
                        # 分割关键词:权重对
                        pairs = value.split(',')
                        for pair in pairs:
                            if ':' in pair:
                                keyword, weight_str = pair.split(':', 1)
                                keyword = keyword.strip()
                                try:
                                    weight = float(weight_str.strip())
                                    keyword_weight_pairs.append((keyword, weight))
                                except ValueError:
                                    # 如果权重解析失败，给默认权重0.5
                                    keyword_weight_pairs.append((keyword, 0.5))
                            else:
                                # 如果没有权重，给默认权重0.5
                                keyword = pair.strip()
                                if keyword:
                                    keyword_weight_pairs.append((keyword, 0.5))
                        
                        # 按权重降序排序
                        keyword_weight_pairs.sort(key=lambda x: x[1], reverse=True)
                        
                        # 选取前8个关键词
                        top_keywords = keyword_weight_pairs[:8]
                        result['keywords'] = [kw for kw, weight in top_keywords]
                        result['keyword_weights'] = dict(top_keywords)
                        
                        debug_print(f"🔍 关键词权重分析：")
                        for kw, weight in top_keywords:
                            debug_print(f"   {kw}: {weight:.2f}")
                        debug_print(f"📊 选取前8个高权重关键词：{result['keywords']}")
                        
                    except Exception as e:
                        debug_print(f"⚠️ 权重解析失败：{e}，使用传统关键词提取")
                        # 降级到传统格式
                        keywords = [kw.strip() for kw in value.replace(':', ' ').split(',') if kw.strip()]
                        result['keywords'] = keywords[:8]  # 限制为前8个
                        result['keyword_weights'] = {}
                        
                else:
                    result[key] = value
                    debug_print(f"📝 {key}: {value[:50]}...")
        
        # 兼容旧格式的关键词提取（如果新格式失败）
        if not result.get('keywords'):
            old_keywords_match = re.search(r'关键词：([^\n]+)', summary)
            if old_keywords_match:
                keywords = [kw.strip() for kw in old_keywords_match.group(1).split(',') if kw.strip()]
                result['keywords'] = keywords[:8]  # 限制为前8个
                result['keyword_weights'] = {}
                debug_print(f"🔄 使用兼容格式，提取关键词：{result['keywords']}")
        
        # 提取样例组数
        sample_count_match = re.search(r'样例组数：(\d+)', summary)
        if sample_count_match:
            result['sample_count'] = int(sample_count_match.group(1))
            debug_print(f"📊 样例组数：{result['sample_count']}")
        
        # 提取多组样例
        samples = []
        for i in range(1, 6):  # 最多支持5组样例
            input_pattern = f'样例{i}输入：(.+?)(?=样例{i}输出：|样例{i+1}输入：|核心问题：|$)'
            output_pattern = f'样例{i}输出：(.+?)(?=样例{i+1}输入：|样例{i+1}输出：|核心问题：|$)'
            
            input_match = re.search(input_pattern, summary, re.DOTALL)
            output_match = re.search(output_pattern, summary, re.DOTALL)
            
            if input_match and output_match:
                sample = {
                    'input': input_match.group(1).strip(),
                    'output': output_match.group(1).strip()
                }
                samples.append(sample)
                print(f"📋 样例{i}: 输入({len(sample['input'])}字符) 输出({len(sample['output'])}字符)")
            else:
                break  # 没有更多样例
        
        result['samples'] = samples
        if not result['sample_count']:
            result['sample_count'] = len(samples)
        
        # 兼容性处理：如果没有提取到新格式，尝试提取旧格式
        if not result['core_problem']:
            clean_match = re.search(r'纯净题目：(.+)', summary, re.DOTALL)
            if clean_match:
                result['core_problem'] = clean_match.group(1).strip()
                debug_print("📝 兼容旧格式：纯净题目已提取")
            else:
                result['core_problem'] = content
                debug_print("⚠️ 未找到结构化信息，使用原内容")
        
        # 如果没有提取到多组样例，尝试提取旧格式的单组样例
        if not samples:
            old_input_match = re.search(r'输入样例：(.+?)(?=输出样例：|核心问题：|$)', summary, re.DOTALL)
            old_output_match = re.search(r'输出样例：(.+?)(?=核心问题：|$)', summary, re.DOTALL)
            
            if old_input_match and old_output_match:
                samples.append({
                    'input': old_input_match.group(1).strip(),
                    'output': old_output_match.group(1).strip()
                })
                result['samples'] = samples
                result['sample_count'] = 1
                debug_print("📝 兼容旧格式：单组样例已提取")
        
        return result
            
    except Exception as e:
        print(f"❌ AI分析失败：{e}")
        print("🔄 使用原始内容继续...")
        return {
            'keywords': [],
            'keyword_weights': {},  # 确保包含权重字段
            'problem_description': '',
            'input_format': '',
            'output_format': '',
            'sample_count': 0,
            'samples': [],
            'core_problem': content,
            'original_content': content
        }

