# -*- coding: utf-8 -*-
"""
AI客户端 - 完全保持原有功能
从main.py中提取的AI相关函数，功能完全不变
"""

import re
import time
from zai import ZhipuAiClient
from ..config.settings import settings

# 保持原有的全局变量初始化
zhipu = ZhipuAiClient(api_key=settings.ai.zhipu_api_key)

def get_zhipu_client():
    """获取ZhipuAI客户端实例"""
    return zhipu

def get_embedding(text: str):
    """获取文本的嵌入向量"""
    try:
        response = zhipu.embeddings.create(
            model=settings.ai.embedding_model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ 获取嵌入向量失败: {e}")
        return None

def debug_print(*args, **kwargs):
    """受控的调试输出函数 - 保持原有功能"""
    if settings.system.show_debug_info:
        print(*args, **kwargs)

def request_code_fix_with_retry(fix_prompt: str, max_retries: int = 3):
    """带重试机制的API调用 - 保持原有功能"""
    for attempt in range(max_retries):
        try:
            response = zhipu.chat.completions.create(
                model=settings.ai.chat_model,
                messages=[{"role": "user", "content": fix_prompt}],
                temperature=0.3,
                timeout=600,
                max_tokens=4000,  # 限制最大输出长度
                thinking={
                    "type": "disabled"
                }
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            print(f"   🔄 API调用尝试 {attempt + 1}/{max_retries} 失败: {error_msg}")
            
            if attempt < max_retries - 1:
                # 指数退避重试
                wait_time = (2 ** attempt) + 1
                print(f"   ⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                # 最后一次尝试失败，提供详细错误信息
                if "Connection" in error_msg or "timeout" in error_msg.lower():
                    print("   🌐 网络连接问题，建议检查网络状态或稍后重试")
                elif "API" in error_msg or "rate" in error_msg.lower():
                    print("   🔑 API配额或限制问题，建议检查API状态")
                elif "model" in error_msg.lower():
                    print("   🤖 模型相关问题，建议检查模型配置")
                else:
                    print("   💡 建议检查API配置和网络连接")
                
                raise e

def extract_code_from_ai_response(response_text: str):
    """从AI响应中提取代码，支持多种格式 - 保持原有功能"""
    # 尝试多种代码提取模式
    patterns = [
        r'```cpp\s*\n(.*?)\n```',           # 标准cpp格式
        r'```c\+\+\s*\n(.*?)\n```',         # c++格式
        r'```C\+\+\s*\n(.*?)\n```',         # 大写C++格式
        r'```\s*cpp\s*\n(.*?)\n```',        # 带空格的cpp
        r'```\s*c\+\+\s*\n(.*?)\n```',      # 带空格的c++
        r'```\s*\n(.*?)\n```',              # 无语言标识的代码块
        r'修复后的代码：\s*\n```[^`]*\n(.*?)\n```',  # 带说明的代码
        r'完整代码[：:]\s*\n```[^`]*\n(.*?)\n```',   # 完整代码标题
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            # 验证代码是否看起来像C++代码
            if is_valid_cpp_code(code):
                return code
    
    return None

def is_valid_cpp_code(code: str) -> bool:
    """简单验证是否为有效的C++代码 - 保持原有功能"""
    if not code or len(code) < 10:
        return False
    
    # 检查是否包含C++关键字和结构
    cpp_indicators = [
        '#include', 'int main', 'using namespace', 'std::', 'cout', 'cin',
        'vector', 'string', 'for', 'while', 'if', 'return', '{', '}', ';'
    ]
    
    indicators_found = sum(1 for indicator in cpp_indicators if indicator in code)
    return indicators_found >= 3  # 至少包含3个C++特征

def request_code_fix(code: str, error_report: str):
    """请求AI修复代码 - 保持原有功能"""
    print("   🤖 正在请求AI修复代码...")
    
    # 使用简洁明确的提示词
    fix_prompt = f"""请修复以下C++代码错误。

代码:
```cpp
{code}
```

错误:
{error_report}

要求:
1. 分析错误原因
2. 修复代码逻辑
3. 直接返回完整的修复后代码
4. 用```cpp开始，```结束
5. 不要过多解释，重点是代码

修复后的代码:"""
    
    try:
        response_text = request_code_fix_with_retry(fix_prompt)
        
        # 调试：打印AI响应的前300字符以便分析
        print(f"   🔍 AI响应预览: {response_text[:300]}...")
        
        # 检查响应是否存在无限循环的思考
        if len(response_text) > 20000:  # 如果响应超过20000字符，可能有问题
            print("   ⚠️ AI响应过长，可能存在无限循环思考，尝试截断...")
            # 查找第一个代码块的位置
            code_start = response_text.find("```cpp")
            if code_start == -1:
                code_start = response_text.find("```c++")
            if code_start == -1:
                code_start = response_text.find("```")
            
            if code_start != -1:
                # 从代码块开始截断，保留一定长度
                response_text = response_text[code_start:code_start+5000]
                print("   ✂️ 已截断响应，保留代码部分")
        
        # 使用增强的代码提取逻辑
        fixed_code = extract_code_from_ai_response(response_text)
        
        if fixed_code:
            print("   ✅ AI修复完成")
            return fixed_code
        else:
            print("   ❌ 无法从AI响应中提取代码")
            print(f"   📝 响应长度: {len(response_text)} 字符")
            # 检查是否有代码块标记但不完整
            if "```cpp" in response_text or "```c++" in response_text:
                print("   🔍 检测到代码块标记，但提取失败，可能是响应不完整")
            else:
                print("   🔍 未检测到标准代码块标记")
            return None
            
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ AI修复失败: {error_msg}")
        return None

def request_code_fix_enhanced(code: str, error_report: str, problem_analysis: dict, 
                             problem_summary: dict = None, context: str = "", attempt_num: int = 1):
    """增强的代码修复 - 包含完整题目信息 - 保持原有功能"""
    print(f"   🧠 正在请求AI分析(第{attempt_num}次)...")
    
    # 构建包含题目信息的修复提示
    fix_prompt = f"""请修复以下C++代码的错误。这是第{attempt_num}次修复尝试。

## 题目信息
"""
    
    # 添加完整的题目信息
    if problem_summary:
        if problem_summary.get('description'):
            fix_prompt += f"**题目描述：**\n{problem_summary['description']}\n\n"
        elif problem_summary.get('core_problem'):
            fix_prompt += f"**核心问题：**\n{problem_summary['core_problem']}\n\n"
        
        if problem_summary.get('input_format'):
            fix_prompt += f"**输入格式：**\n{problem_summary['input_format']}\n\n"
        
        if problem_summary.get('output_format'):
            fix_prompt += f"**输出格式：**\n{problem_summary['output_format']}\n\n"
        
        # 添加样例数据
        samples = problem_summary.get('samples', [])
        if samples:
            fix_prompt += f"**样例数据：**\n"
            for i, sample in enumerate(samples[:2], 1):  # 最多显示2个样例
                fix_prompt += f"样例{i}：\n"
                fix_prompt += f"输入：{sample['input']}\n"
                fix_prompt += f"输出：{sample['output']}\n\n"
        
        # 添加关键算法信息
        if problem_summary.get('keywords'):
            keywords = problem_summary['keywords'][:3]  # 取前3个关键词
            fix_prompt += f"**相关算法：** {', '.join(keywords)}\n\n"
    
    # 添加简化的算法知识（避免prompt过长）
    if context:
        # 提取核心算法信息，避免全部context
        simplified_context = context[:800] + "..."  # 限制长度
        fix_prompt += f"**算法提示：**\n{simplified_context}\n\n"
    
    fix_prompt += f"""## 当前代码
```cpp
{code}
```

## 错误信息
{error_report}

## 修复要求
1. 基于完整的题目信息理解问题需求
2. 分析当前代码与题目要求的差距
3. 确保修复后的代码能正确处理所有样例
4. 严格按照输入输出格式实现
5. 考虑算法复杂度要求
6. 直接返回修复后的完整C++代码，用```cpp开始，```结束

请立即返回修复后的代码:"""
    
    try:
        response_text = request_code_fix_with_retry(fix_prompt)
        
        # 调试：打印AI响应的前500字符以便分析
        print(f"   🔍 AI响应预览: {response_text[:500]}...")
        
        # 检查响应是否存在无限循环的思考
        if len(response_text) > 20000:  # 如果响应超过20000字符，可能有问题
            print("   ⚠️ AI响应过长，可能存在无限循环思考，尝试截断...")
            # 查找第一个代码块的位置
            code_start = response_text.find("```cpp")
            if code_start == -1:
                code_start = response_text.find("```c++")
            if code_start == -1:
                code_start = response_text.find("```")
            
            if code_start != -1:
                # 从代码块开始截断，保留一定长度
                response_text = response_text[code_start:code_start+5000]
                print("   ✂️ 已截断响应，保留代码部分")
        
        # 提取代码 - 使用多种模式
        fixed_code = extract_code_from_ai_response(response_text)
        
        if fixed_code:
            print("   ✅ 深度AI分析完成")
            print(f"   📏 修复后代码长度: {len(fixed_code)} 字符")
            return fixed_code
        else:
            print("   ❌ 无法从AI响应中提取代码")
            print(f"   📝 响应长度: {len(response_text)} 字符")
            
            # 更详细的调试信息
            if "```" in response_text:
                code_blocks = response_text.count("```")
                print(f"   🔍 检测到 {code_blocks} 个代码块标记")
                if code_blocks % 2 != 0:
                    print("   ⚠️ 代码块标记不匹配（奇数个），可能响应被截断")
            else:
                print("   🔍 未检测到任何代码块标记")
            
            # 检查常见问题
            if len(response_text) < 50:
                print("   ⚠️ 响应过短，可能是API错误或网络问题")
            elif "抱歉" in response_text or "无法" in response_text:
                print("   ⚠️ AI拒绝了修复请求")
            elif response_text.count("思考") > 3:
                print("   ⚠️ AI陷入了过度思考循环")
                
            print("   💡 尝试使用更明确的提示重新请求...")
            
            # 尝试使用更简单的请求
            simple_prompt = f"""
请修复以下C++代码的错误。直接返回修复后的完整代码，用```cpp开始，用```结束。

错误代码：
```cpp
{code}
```

错误信息：{error_report}

修复后的代码：
"""
            try:
                retry_text = request_code_fix_with_retry(simple_prompt)
                print(f"   🔄 重试响应预览: {retry_text[:200]}...")
                
                retry_code = extract_code_from_ai_response(retry_text)
                if retry_code:
                    print("   ✅ 重试成功")
                    return retry_code
                else:
                    print("   ❌ 重试仍然失败")
                    return None
                    
            except Exception as retry_e:
                print(f"   ❌ 重试请求失败: {retry_e}")
                return None
            
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ AI分析失败: {error_msg}")
        
        # 检查是否是连接错误，提供更好的错误信息
        if "Connection" in error_msg or "timeout" in error_msg.lower() or "network" in error_msg.lower():
            print("   🌐 网络连接问题，建议检查网络状态或稍后重试")
        elif "API" in error_msg or "rate" in error_msg.lower():
            print("   🔑 API配额或限制问题，建议检查API状态")
        elif "model" in error_msg.lower():
            print("   🤖 模型相关问题，建议检查模型配置")
        
        return None

