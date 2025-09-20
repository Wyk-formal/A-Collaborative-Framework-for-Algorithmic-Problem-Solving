# -*- coding: utf-8 -*-
"""
验证服务 - 完全保持原有功能
从main.py中提取的验证相关函数，功能完全不变
"""

import time
from ..core.code_validator import CodeValidator
from ..core.ai_client import request_code_fix_enhanced, request_code_fix
from ..config.settings import settings

def debug_print(*args, **kwargs):
    """受控的调试输出函数 - 保持原有功能"""
    if settings.system.show_debug_info:
        print(*args, **kwargs)

def generate_error_report(validation_results):
    """生成详细的错误报告 - 保持原有功能"""
    report = "## 代码验证错误报告\n\n"
    
    failed_samples = [r for r in validation_results if not r['result']['success'] or r['result'].get('status') != 'AC']
    
    if not failed_samples:
        return "所有样例都通过了验证。"
    
    report += f"共有 {len(failed_samples)} 个样例未通过:\n\n"
    
    for sample in failed_samples:
        sample_id = sample['sample_id']
        result = sample['result']
        error_type = result.get('error_type', 'Unknown')
        
        report += f"### 样例 {sample_id} - {error_type}\n"
        report += f"**输入:**\n```\n{sample['input']}\n```\n"
        report += f"**期望输出:**\n```\n{sample['expected']}\n```\n"
        
        if error_type == 'WA':
            report += f"**实际输出:**\n```\n{result.get('actual', 'N/A')}\n```\n"
        elif error_type in ['CE', 'RE', 'TLE', 'MLE']:
            report += f"**错误信息:** {result.get('error_message', 'N/A')}\n"
        
        if result.get('time_used'):
            report += f"**运行时间:** {result['time_used']:.3f}s\n"
        if result.get('memory_used'):
            report += f"**内存使用:** {result['memory_used']:.2f}MB\n"
        
        report += "\n"
    
    # 添加常见错误类型的解决建议
    report += "## 错误类型说明\n"
    error_types = set(r['result'].get('error_type') for r in failed_samples)
    
    suggestions = {
        'WA': '答案错误 - 检查算法逻辑、边界条件处理、输出格式',
        'TLE': '时间超限 - 优化算法复杂度、减少不必要的计算',
        'MLE': '内存超限 - 优化数据结构、减少内存使用',
        'RE': '运行时错误 - 检查数组越界、空指针、除零等问题',
        'CE': '编译错误 - 检查语法错误、头文件包含、变量声明'
    }
    
    for error_type in error_types:
        if error_type in suggestions:
            report += f"- **{error_type}**: {suggestions[error_type]}\n"
    
    return report

def validate_and_improve_solution(code: str, samples: list, max_iterations: int = 5):
    """
    自动验证样例并迭代改进代码 - 保持原有功能
    """
    print("🔍 开始代码验证...")
    validator = CodeValidator()
    
    for iteration in range(max_iterations):
        print(f"\n📝 第 {iteration + 1} 次验证...")
        
        # 验证所有样例
        all_passed = True
        validation_results = []
        
        for i, sample in enumerate(samples):
            sample_input = sample['input'].strip()
            sample_output = sample['output'].strip()
            
            print(f"   验证样例 {i + 1}...")
            result = validator.validate_sample(code, sample_input, sample_output)
            
            validation_results.append({
                'sample_id': i + 1,
                'result': result,
                'input': sample_input,
                'expected': sample_output
            })
            
            if not result['success'] or result.get('status') != 'AC':
                all_passed = False
                # 打印错误信息
                error_type = result.get('error_type', 'Unknown')
                error_msg = result.get('error_message', '未知错误')
                print(f"   ❌ 样例 {i + 1} 失败: {error_type} - {error_msg}")
                
                if error_type == 'WA':
                    print(f"      期望输出: {result.get('expected', 'N/A')}")
                    print(f"      实际输出: {result.get('actual', 'N/A')}")
            else:
                time_used = result.get('time_used', 0)
                memory_used = result.get('memory_used', 0)
                print(f"   ✅ 样例 {i + 1} 通过 (时间: {time_used:.3f}s, 内存: {memory_used:.2f}MB)")
        
        # 如果所有样例都通过，返回成功
        if all_passed:
            print(f"\n🎉 所有样例验证通过! (第 {iteration + 1} 次尝试)")
            return {
                'success': True,
                'code': code,
                'iterations': iteration + 1,
                'results': validation_results
            }
        
        # 如果还有迭代机会，尝试修复代码
        if iteration < max_iterations - 1:
            print(f"\n🔧 尝试修复代码...")
            error_report = generate_error_report(validation_results)
            
            # 添加延迟避免API速率限制
            import time
            time.sleep(2)  # 等待2秒再调用API
            
            fixed_code = request_code_fix(code, error_report)
            
            if fixed_code and fixed_code != code:
                code = fixed_code
                print("   代码已更新，继续验证...")
            else:
                print(f"   ⚠️ 代码修复失败，将在第 {iteration + 2} 次尝试中重新修复...")
                # 不要break，继续下一次迭代
    
    # 计算实际的尝试次数
    actual_iterations = iteration + 1
    print(f"\n❌ 验证失败，已尝试 {actual_iterations} 次")
    return {
        'success': False,
        'code': code,
        'iterations': actual_iterations,
        'results': validation_results
    }

def validate_and_improve_solution_enhanced(code: str, samples: list, problem_analysis: dict, 
                                         problem_summary: dict = None, context: str = "", 
                                         max_iterations: int = 8):
    """
    增强版代码验证，针对复杂算法问题提供更深入的分析 - 保持原有功能
    """
    print("🔍 开始增强代码验证...")
    validator = CodeValidator()
    
    for iteration in range(max_iterations):
        print(f"\n📝 第 {iteration + 1} 次验证...")
        
        # 验证所有样例
        all_passed = True
        validation_results = []
        
        for i, sample in enumerate(samples):
            sample_input = sample['input'].strip()
            sample_output = sample['output'].strip()
            
            print(f"   验证样例 {i + 1}...")
            result = validator.validate_sample(code, sample_input, sample_output)
            
            validation_results.append({
                'sample_id': i + 1,
                'result': result,
                'input': sample_input,
                'expected': sample_output
            })
            
            if not result['success'] or result.get('status') != 'AC':
                all_passed = False
                # 打印错误信息
                error_type = result.get('error_type', 'Unknown')
                error_msg = result.get('error_message', '未知错误')
                print(f"   ❌ 样例 {i + 1} 失败: {error_type} - {error_msg}")
                
                if error_type == 'WA':
                    print(f"      期望输出: {result.get('expected', 'N/A')}")
                    print(f"      实际输出: {result.get('actual', 'N/A')}")
            else:
                time_used = result.get('time_used', 0)
                memory_used = result.get('memory_used', 0)
                print(f"   ✅ 样例 {i + 1} 通过 (时间: {time_used:.3f}s, 内存: {memory_used:.2f}MB)")
        
        # 如果所有样例都通过，返回成功
        if all_passed:
            print(f"\n🎉 所有样例验证通过! (第 {iteration + 1} 次尝试)")
            return {
                'success': True,
                'code': code,
                'iterations': iteration + 1,
                'results': validation_results
            }
        
        # 如果还有迭代机会，尝试修复代码
        if iteration < max_iterations - 1:
            print(f"\n🔧 尝试修复代码...")
            
            # 生成错误报告
            error_report = generate_error_report(validation_results)
            
            # 添加延迟避免API速率限制
            import time
            time.sleep(2)  # 等待2秒再调用API
            
            # 传递完整的题目信息和上下文进行修复
            fixed_code = request_code_fix_enhanced(
                code, error_report, problem_analysis, 
                problem_summary, context, iteration + 1  # 传递完整上下文和尝试次数
            )
            
            if fixed_code and fixed_code != code:
                code = fixed_code  # 更新代码用于下一次验证
                print("   代码已更新，继续验证...")
            else:
                print(f"   ⚠️ 代码修复失败,将在第 {iteration + 2} 次尝试中继续修复...")

    # 计算实际的尝试次数
    actual_iterations = iteration + 1
    print(f"\n❌ 验证失败，已尝试 {actual_iterations} 次")
    return {
        'success': False,
        'code': code,
        'iterations': actual_iterations,
        'results': validation_results
    }

def extract_samples_from_problem(problem_info):
    """从题目信息中提取样例数据 - 保持原有功能"""
    if not problem_info or not isinstance(problem_info, dict):
        return []
    
    samples = problem_info.get('samples', [])
    if samples:
        return samples
    
    # 兼容旧格式
    if problem_info.get('input_sample') and problem_info.get('output_sample'):
        return [{
            'input': problem_info['input_sample'],
            'output': problem_info['output_sample']
        }]
    
    return []

def extract_code_from_response(response: str):
    """从回答中提取C++代码 - 保持原有功能"""
    import re
    code_pattern = r'```cpp\s*\n(.*?)\n```'
    match = re.search(code_pattern, response, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # 如果没找到，尝试其他模式
    code_pattern2 = r'```c\+\+\s*\n(.*?)\n```'
    match2 = re.search(code_pattern2, response, re.DOTALL)
    
    if match2:
        return match2.group(1).strip()
    
    return None

def update_code_in_response(response: str, new_code: str):
    """更新回答中的代码 - 保持原有功能"""
    import re
    
    # 尝试替换第一个C++代码块
    code_pattern = r'```cpp\s*\n(.*?)\n```'
    match = re.search(code_pattern, response, re.DOTALL)
    
    if match:
        new_code_block = f"```cpp\n{new_code}\n```"
        updated_response = response.replace(match.group(0), new_code_block, 1)
        return updated_response
    
    # 如果没找到，在末尾添加新代码
    return response + f"\n\n## 修正后的代码\n\n```cpp\n{new_code}\n```"

def generate_enhanced_answer_with_validation(question: str, context: str, problem_info=None):
    """生成答案并进行代码验证 - 传递完整上下文 - 保持原有功能"""
    
    print("🔍 开始自动验证流程...")
    
    # 首先生成初始答案
    from .answer_generator import generate_enhanced_answer
    initial_answer = generate_enhanced_answer(question, context, problem_info)
    
    # 从problem_info中提取样例数据
    samples = extract_samples_from_problem(problem_info)
    
    if not samples:
        print("\n⚠️ 未找到样例数据，跳过代码验证")
        return initial_answer
    
    # 从答案中提取代码
    code = extract_code_from_response(initial_answer)
    
    if not code:
        print("\n⚠️ 未找到C++代码，跳过代码验证")
        return initial_answer
    
    print(f"\n🔍 找到 {len(samples)} 组样例，开始自动验证...")
    
    # 统一设置验证次数为8次
    max_iterations = 8
    
    # 创建简化的问题分析信息（保持函数接口兼容）
    problem_analysis = {
        'types': [],
        'scale': 'medium',
        'is_complex': False
    }
    
    # 进行代码验证和迭代改进
    validation_result = validate_and_improve_solution_enhanced(
        code, samples, problem_analysis, 
        problem_info, context,  # 传递完整的题目信息和上下文
        max_iterations
    )
    
    if validation_result['success']:
        print(f"\n🎉 代码验证成功! (第 {validation_result['iterations']} 次尝试)")
        
        # 如果代码有改进，更新答案中的代码
        if validation_result['code'] != code:
            print("📝 使用改进后的代码更新答案...")
            updated_answer = update_code_in_response(initial_answer, validation_result['code'])
            return updated_answer
        else:
            return initial_answer
    else:
        print(f"\n❌ 代码验证失败 (尝试了 {validation_result['iterations']} 次)")
        print("⚠️ 返回原始答案，建议人工检查代码")
        
        # 在答案末尾添加验证失败的说明
        validation_note = f"""

## ⚠️ 代码验证结果

代码在样例测试中未完全通过，建议人工检查：

"""
        for result in validation_result['results']:
            if not result['result']['success'] or result['result'].get('status') != 'AC':
                error_type = result['result'].get('error_type', 'Unknown')
                error_msg = result['result'].get('error_message', '未知错误')
                validation_note += f"- 样例 {result['sample_id']}: {error_type} - {error_msg}\n"
        
        return initial_answer + validation_note

