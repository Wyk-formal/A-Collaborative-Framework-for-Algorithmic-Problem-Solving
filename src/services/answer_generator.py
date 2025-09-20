# -*- coding: utf-8 -*-
"""
答案生成服务 - 完全保持原有功能
从main.py中提取的答案生成相关函数，功能完全不变
"""

import re
import time
import threading
from zai import ZhipuAiClient
from ..config.settings import settings

# 保持原有的全局变量初始化
zhipu = ZhipuAiClient(api_key=settings.ai.zhipu_api_key)

def debug_print(*args, **kwargs):
    """受控的调试输出函数 - 保持原有功能"""
    if settings.system.show_debug_info:
        print(*args, **kwargs)

def build_enhanced_context(results, question: str):
    """构建增强的上下文 - 保持原有功能"""
    if not results:
        # 如果没有检索结果，提供基础上下文
        from ..core.search_engine import extract_algorithm_keywords
        keywords = extract_algorithm_keywords(question)
        basic_context = f"""【算法概览】
根据问题分析，这可能涉及以下算法领域：

检测到的关键词：{', '.join(keywords) if keywords else '暂无特定关键词'}

【基础分析】
请根据题目描述和要求，分析可能需要的算法类型：
- 如果涉及查找、排序：可能需要二分查找、排序算法
- 如果涉及图论：可能需要最短路径、最小生成树等
- 如果涉及动态规划：需要分析状态转移
- 如果涉及数据结构：可能需要线段树、并查集等

【实现建议】
1. 仔细分析题目的输入输出格式
2. 确定时间复杂度要求
3. 选择合适的算法和数据结构
4. 注意边界条件处理
5. 编写完整的测试用例"""
        return basic_context
    
    question_lower = question.lower()
    is_code_request = any(word in question_lower for word in ["代码", "实现", "怎么写", "如何实现", "c++", "cpp"])
    is_explanation_request = any(word in question_lower for word in ["原理", "思路", "为什么", "怎么想", "分析"])
    is_comparison_request = any(word in question_lower for word in ["区别", "比较", "哪个", "选择", "优劣"])
    
    context_parts = []
    
    # 1. 算法概览
    context_parts.append("【算法概览】")
    for i, r in enumerate(results[:3], 1):
        context_parts.append(
            f"{i}. {r['title']}\n"
            f"   简介：{r.get('intro', '')[:200]}...\n"
            f"   复杂度：时间 {r.get('time', 'N/A')}，空间 {r.get('space', 'N/A')}\n"
            f"   关键词：{', '.join(r.get('keywords', [])[:5])}\n"
            f"   别名：{', '.join(r.get('aliases', [])[:3])}"
        )
    
    # 2. 详细原理
    context_parts.append("\n【核心原理】")
    for r in results[:2]:
        if r.get('principle'):
            context_parts.append(f"{r['title']}：{r['principle'][:500]}...")
    
    # 3. 前置知识和应用场景
    context_parts.append("\n【前置知识】")
    prereq_set = set()
    for r in results:
        prereq_set.update(r.get('prereq', []))
    context_parts.append(", ".join(list(prereq_set)[:10]))
    
    context_parts.append("\n【应用场景】")
    app_set = set()
    for r in results:
        app_set.update(r.get('apps', []))
    context_parts.append(", ".join(list(app_set)[:10]))
    
    # 4. 常见坑点
    context_parts.append("\n【常见坑点】")
    pitfall_set = set()
    for r in results:
        pitfall_set.update(r.get('pitfalls', []))
    context_parts.append(", ".join(list(pitfall_set)[:8]))
    
    # 5. 详细代码示例（增强版）
    context_parts.append("\n【详细代码示例】")
    example_count = 0
    
    for r in results[:3]:  # 检查前3个结果
        detailed_examples = r.get('detailed_examples', [])
        if detailed_examples and example_count < 5:  # 最多收集5个示例
            algorithm_name = r['title']  # 获取算法名称
            context_parts.append(f"\n=== {algorithm_name} 的实现示例 ===")
            
            for ex in detailed_examples[:2]:  # 每个算法最多2个示例
                if example_count >= 5:
                    break
                    
                # 检查是否有代码内容
                if ex.get('code') and len(ex['code'].strip()) > 20:
                    example_count += 1
                    
                    # 添加示例标题和描述，明确标出所属算法
                    ex_title = ex.get('title', f'示例代码 {example_count}')
                    ex_description = ex.get('description', '')
                    ex_language = ex.get('language', 'cpp')
                    ex_difficulty = ex.get('difficulty', '')
                    ex_time_complexity = ex.get('time_complexity', '')
                    ex_space_complexity = ex.get('space_complexity', '')
                    
                    # 明确标出算法归属
                    context_parts.append(f"\n【示例 {example_count}】{ex_title} (来自算法: {algorithm_name})")
                    
                    if ex_description:
                        context_parts.append(f"描述：{ex_description[:300]}")
                    
                    if ex_difficulty:
                        context_parts.append(f"难度：{ex_difficulty}")
                    
                    if ex_time_complexity or ex_space_complexity:
                        complexity_info = []
                        if ex_time_complexity:
                            complexity_info.append(f"时间复杂度: {ex_time_complexity}")
                        if ex_space_complexity:
                            complexity_info.append(f"空间复杂度: {ex_space_complexity}")
                        context_parts.append(f"复杂度：{', '.join(complexity_info)}")
                    
                    # 添加代码，前面标明算法归属
                    context_parts.append(f"实现代码（{ex_language}）：")
                    context_parts.append("```" + ex_language)
                    # 在代码开头添加注释说明算法归属
                    if ex_language.lower() in ['cpp', 'c++', 'c']:
                        context_parts.append(f"// {algorithm_name} - {ex_title}")
                        context_parts.append(f"// 算法来源: {algorithm_name}")
                    elif ex_language.lower() == 'python':
                        context_parts.append(f"# {algorithm_name} - {ex_title}")
                        context_parts.append(f"# 算法来源: {algorithm_name}")
                    
                    context_parts.append(ex['code'])
                    context_parts.append("```")
                    
                    # 添加解题思路（如果有）
                    if ex.get('solution'):
                        context_parts.append(f"解题思路：{ex['solution'][:400]}")
                    
                    context_parts.append("")  # 空行分隔
    
    # 如果没有找到详细代码示例，使用传统方式
    if example_count == 0 and is_code_request and results:
        context_parts.append("\n【基础代码参考】")
        for r in results[:2]:
            algorithm_name = r['title']  # 获取算法名称
            examples = r.get('examples', [])  # 兼容旧格式
            if examples:
                for ex in examples[:1]:
                    if isinstance(ex, dict) and ex.get('code'):
                        # 明确标出算法归属
                        context_parts.append(f"【{algorithm_name}】{ex.get('title', '示例')}：")
                        context_parts.append("```cpp")
                        # 在代码开头添加注释说明算法归属
                        context_parts.append(f"// 算法来源: {algorithm_name}")
                        context_parts.append(ex['code'])
                        context_parts.append("```")
                        break
    
    # 6. 相关片段
    context_parts.append("\n【相关技术片段】")
    for r in results[:2]:
        snippets = r.get('snippets', [])
        if snippets:
            context_parts.append(f"{r['title']}：{snippets[0][:300]}...")
    
    # 7. 实现提示（新增）
    if is_code_request:
        context_parts.append("\n【实现提示】")
        context_parts.append("基于以上代码示例，请注意：")
        context_parts.append("1. 优先参考相同或相似算法的实现模式")
        context_parts.append("2. 注意复杂度要求，选择合适的算法")
        context_parts.append("3. 仔细处理输入输出格式")
        context_parts.append("4. 考虑边界情况和数据范围")
        context_parts.append("5. 使用竞赛常用的代码风格和优化技巧")
        context_parts.append("6. 严格控制时间复杂度和空间复杂度，确保满足题目限制")
        context_parts.append("7. 在空间紧张时考虑滚动数组、状态压缩等优化技巧")
    
    return "\n".join(context_parts)

def create_optimized_prompt(question: str, context: str, problem_info: dict = None):
    """创建优化的Prompt结构 - 保持原有功能"""
    question_lower = question.lower()
    is_code_request = any(word in question_lower for word in ["代码", "实现", "怎么写", "如何实现", "c++", "cpp"])
    is_explanation_request = any(word in question_lower for word in ["原理", "思路", "为什么", "怎么想", "分析"])
    is_comparison_request = any(word in question_lower for word in ["区别", "比较", "哪个", "选择", "优劣"])
    
    system_prompt = """你是一位专业的算法竞赛教练，拥有丰富的OI/ACM竞赛经验。你的任务是：

1. **准确理解问题**：仔细分析用户的问题，识别其真正需求
2. **基于知识库回答**：严格基于提供的算法知识库内容回答，不编造信息
3. **充分利用代码示例**：知识库中提供了详细的代码示例，请：
   - 分析示例代码的实现模式和技巧
   - 参考相似算法的代码结构
   - 借鉴示例中的最佳实践
   - 根据示例调整你的实现方案
4. **提供完整解决方案**：包括算法思路、复杂度分析、实现要点和完整代码
5. **代码质量保证**：提供的C++代码必须：
   - 语法正确，可直接编译运行
   - 包含必要的头文件和命名空间
   - 有清晰的变量命名和注释
   - 处理边界情况和异常输入
   - 符合竞赛编程规范
   - 严格按照给定的输入输出格式
   - 参考提供的代码示例的优秀实现模式
   - **严格保证时间复杂度满足题目要求**：根据数据范围分析，选择时间复杂度符合要求的算法
   - **严格保证空间复杂度满足题目要求**：考虑内存限制，选择空间复杂度合适的数据结构和算法

回答结构：
1. **题目分析**：理解题意、分析约束条件、确定数据范围、分析内存限制
2. **算法选择**：核心思路、适用场景、复杂度分析、参考示例说明、时间复杂度验证、空间复杂度验证
3. **实现要点**：关键步骤、注意事项、优化技巧、借鉴示例的精华
4. **完整代码**：可直接使用的C++实现，严格按照输入输出格式，融合示例的优秀实现
5. **复杂度说明**：时间/空间复杂度及推导，验证是否满足题目要求
6. **测试验证**：使用给定样例验证代码正确性
7. **代码说明**：解释代码的关键部分，说明借鉴了哪些示例的实现思路

【代码示例使用原则】：
- 如果知识库提供了相关算法的代码示例，请仔细研究其实现方式
- 优先采用示例中验证过的数据结构和算法模式
- 学习示例中的代码风格、变量命名和注释方式
- 借鉴示例中的边界处理和优化技巧
- 如果题目与示例类似，可以在示例基础上进行适当修改
- 即使题目不完全相同，也要学习示例的实现思路和代码结构

【重要】：如果提供了输入输出格式和样例，代码必须严格按照格式实现，确保样例能通过。

记住：代码必须完整可运行，包含main函数和必要的输入输出处理，并充分借鉴知识库中的优秀代码示例。

【关键要求：时间复杂度严格匹配】
- 必须根据题目的数据范围（如n≤10^5, n≤10^6等）选择合适的算法
- 绝对不能提供超时的算法实现（如n≤10^6时使用O(n²)算法）
- 在算法选择时优先考虑时间复杂度是否满足要求
- 如果有多种算法可选，优先选择时间复杂度更优且满足要求的方案
- 在代码实现中要注意常数优化，避免不必要的计算开销
- 复杂度分析部分必须明确说明为什么该算法能在给定时间限制内通过

【关键要求：空间复杂度严格匹配】
- 必须根据题目的内存限制（如128MB, 256MB等）选择合适的数据结构
- 绝对不能提供内存超限的算法实现（如内存限制256MB时使用超过该限制的数组或数据结构）
- 在算法选择时必须考虑空间复杂度是否满足要求
- 优先选择空间效率高的数据结构和算法实现方式
- 避免不必要的内存占用，如过大的辅助数组、重复存储等
- 在空间紧张时考虑使用滚动数组、状态压缩等优化技巧
- 复杂度分析部分必须明确说明内存使用情况和为什么不会超限"""

    if is_code_request:
        system_prompt += "\n\n【重点要求】用户明确要求代码实现，请：\n1. 仔细分析知识库提供的代码示例\n2. 参考示例的实现模式和代码结构\n3. 借鉴示例的优化技巧和边界处理\n4. 提供完整、可直接编译运行的C++代码\n5. 在代码注释中说明借鉴了哪些示例的思路\n6. **特别重要**：严格分析数据范围和内存限制，确保算法时间复杂度和空间复杂度都满足题目要求，绝不提供会超时或超内存的解法"
    elif is_explanation_request:
        system_prompt += "\n\n【重点要求】用户关注算法原理和思路分析，请：\n1. 详细解释算法的核心思想和实现逻辑\n2. 结合代码示例说明具体实现方式\n3. 分析示例代码的关键技巧和优化点"
    elif is_comparison_request:
        system_prompt += "\n\n【重点要求】用户需要比较不同算法，请：\n1. 从多个维度进行对比分析，包括复杂度、适用场景、实现难度等\n2. 结合代码示例对比不同实现方式的优劣\n3. 分析各种算法的代码实现特点"
    
    user_prompt = f"""【问题】{question}

【参考知识库内容】
{context}"""

    # 添加结构化的题目信息
    if problem_info and isinstance(problem_info, dict):
        if problem_info.get('problem_description'):
            user_prompt += f"""

【题目描述】
{problem_info['problem_description']}"""
        
        if problem_info.get('input_format'):
            user_prompt += f"""

【输入格式】
{problem_info['input_format']}"""
        
        if problem_info.get('output_format'):
            user_prompt += f"""

【输出格式】
{problem_info['output_format']}"""
        
        # 处理多组样例
        samples = problem_info.get('samples', [])
        if samples:
            user_prompt += f"""

【样例数据】"""
            for i, sample in enumerate(samples, 1):
                user_prompt += f"""

样例{i}：
输入：
{sample['input']}

输出：
{sample['output']}"""
            
            # 添加样例要求
            user_prompt += f"""

【重要】代码必须能够正确处理以上所有{len(samples)}组样例数据。"""
        
        # 兼容旧版本的单组样例格式
        elif problem_info.get('input_sample') and problem_info.get('output_sample'):
            user_prompt += f"""

【输入样例】
{problem_info['input_sample']}

【输出样例】
{problem_info['output_sample']}"""
    
    elif problem_info and isinstance(problem_info, str):
        # 兼容旧版本的字符串格式
        user_prompt += f"""

【题目信息】
{problem_info}"""

    user_prompt += """

请基于以上知识库内容，提供专业、准确的回答。如果知识库中没有相关信息，请明确说明，不要编造内容。

【特别注意：充分利用提供的代码示例】
知识库中包含了丰富的算法代码示例，请务必：
1. 仔细研究相关算法的详细代码示例
2. 分析示例的实现模式、数据结构选择和算法逻辑
3. 借鉴示例中的代码风格、变量命名和注释方式
4. 学习示例的边界处理、优化技巧和最佳实践
5. 在你的实现中融入示例的优秀设计思路

【回答要求】
1. 如果涉及代码实现，必须提供完整可运行的C++代码，并充分参考知识库中的代码示例
2. 代码要包含必要的头文件、命名空间和main函数
3. 要有清晰的注释和变量命名，学习示例的注释风格
4. 严格按照给定的输入输出格式实现
5. 使用提供的所有样例验证代码正确性（如果有多组样例，每组都要验证）
6. 考虑边界情况和异常输入处理，参考示例的处理方式
7. 符合算法竞赛的编程规范，采用示例的编程风格
8. 如果提供了多组样例，请在代码注释中说明每组样例的验证过程
9. 在代码实现后，简要说明借鉴了哪些示例的设计思路和技巧
10. 如果示例代码与题目需求高度相关，优先基于示例进行适当修改而非从零编写
11. **时间复杂度强制要求**：根据题目数据范围严格选择算法，确保时间复杂度满足要求，在回答中明确说明为什么选择该算法及其时间复杂度分析
12. **空间复杂度强制要求**：根据题目内存限制严格选择数据结构和算法实现，确保空间复杂度满足要求，在回答中明确说明内存使用情况和空间复杂度分析"""

    return system_prompt, user_prompt

def save_final_prompt(system_prompt: str, user_prompt: str):
    """将最终的prompt保存到final_prompt.md文件 - 保持原有功能"""
    final_prompt_file = "final_prompt.md"
    try:
        prompt_content = f"""# 最终Prompt文档

## System Prompt (系统提示)

```
{system_prompt}
```

## User Prompt (用户提示)

```
{user_prompt}
```

---
*此文件由算法竞赛RAG助手自动生成，用于调试和优化prompt*
*生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(final_prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        debug_print(f"📝 最终prompt已保存到 {final_prompt_file}")
        
    except Exception as e:
        debug_print(f"❌ 保存prompt文件失败：{e}")

def generate_enhanced_answer(question: str, context: str, problem_info: str = ""):
    """生成增强答案 - 保持原有功能"""
    system_prompt, user_prompt = create_optimized_prompt(question, context, problem_info)
    
    # 保存最终prompt到文件
    save_final_prompt(system_prompt, user_prompt)
    
    print("【正在生成回答...】")
    print("💭 复杂题目可能需要较长思考时间，请耐心等待...")
    print("=" * 50)
    
    import time
    import threading
    
    # 加载动画线程
    thinking_active = threading.Event()
    thinking_active.set()
    
    
    try:
        # 首先尝试流式模式，给予充足的等待时间
        debug_print("🔄 尝试连接...")
        
        
        start_time = time.time()
        resp = zhipu.chat.completions.create(
            model=settings.ai.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=True,
            thinking={
                "type": "disabled"
            },
            max_tokens=20000,
            temperature=0.6,
            timeout=600 ,
            top_p=0.95
        )
        
        debug_print(f"\r✅ 连接成功，开始接收数据... (耗时: {time.time() - start_time:.1f}s)")
        
        full_response = ""
        chunk_count = 0
        total_chars = 0
        finish_reason = None
        for chunk in resp:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                print(delta, end="", flush=True)
                full_response += delta
                chunk_count += 1
                total_chars += len(delta)
                
            if hasattr(chunk.choices[0], 'finish_reason'):
                finish_reason = chunk.choices[0].finish_reason
        # 如果流式模式成功返回了足够内容，直接使用
        debug_print(f"<完成信息： {finish_reason}>")
        if full_response :  
            debug_print(f"\n✅ 输出成功完成")
            debug_print(f"📈 统计: {chunk_count} chunks, {len(full_response)} chars, 用时: {time.time() - start_time:.1f}s")
            debug_print("\n" + "=" * 50)
            return full_response
        else:
            print(f"\n❌ 返回内容不足（{len(full_response)} chars < {100}）")
            return ""
    except Exception as err:
        
        print(f"\n❌ API调用错误：{err}")
        debug_print("🔧 分析错误类型...")
        # —— 再细分具体类型 —— #
        if isinstance(err, zai.core.APITimeoutError):
            debug_print(f"⏰ 请求超时：{err}")
        elif isinstance(err, zai.core.APIStatusError):
            debug_print(f"🚫 API状态错误：{err}")
        else:
            debug_print(f"❌ 其他错误：{err}")
        
        # 最后的备用回答
        backup_response = f"""## 算法分析

**注意：由于API调用出现问题，以下是基础分析**

### 问题分析
{question[:300]}{'...' if len(question) > 300 else ''}

### 通用解题思路
1. **输入分析**：理解题目的输入输出格式和数据范围
2. **算法选择**：根据数据规模选择合适的时间复杂度
3. **边界处理**：考虑特殊情况和边界条件
4. **代码实现**：编写清晰、可维护的代码

### 代码框架

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cstring>
using namespace std;

int main() {{
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // 读取输入数据
    
    // 算法核心逻辑
    
    // 输出结果
    
    return 0;
}}
```

### 建议
- 请稍后重试以获得完整的AI分析
- 可以尝试简化问题描述
- 或者检查网络连接后重新运行

**错误详情**: {str(err)[:200]}"""
        
        print(backup_response)
        print("\n" + "=" * 50)
        return backup_response
    
    finally:
        # 确保动画线程停止
        thinking_active.clear()
    
    # 如果所有方法都失败
    print("❌ 所有生成方法都失败，返回基础分析")
    return "由于技术问题，无法生成完整回答。请检查网络连接和API配置后重试。"

def post_process_code(response: str):
    """代码后处理 - 保持原有功能"""
    code_pattern = r'```cpp\s*\n(.*?)\n```'
    code_blocks = re.findall(code_pattern, response, re.DOTALL)
    
    if code_blocks:
        for i, code in enumerate(code_blocks):
            if '#include' not in code:
                code_blocks[i] = """#include <iostream>
#include <vector>
#include <algorithm>
#include <string>
#include <map>
#include <set>
#include <queue>
#include <stack>
#include <cmath>
#include <cstring>
#include <climits>
#include <unordered_map>
#include <unordered_set>

using namespace std;

""" + code
            
            if 'int main()' not in code:
                code_blocks[i] += """

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // 在这里添加你的代码逻辑
    
    return 0;
}"""
        
        for i, code in enumerate(code_blocks):
            response = response.replace(
                f'```cpp\n{code_blocks[i]}\n```',
                f'```cpp\n{code}\n```'
            )
    
    return response

