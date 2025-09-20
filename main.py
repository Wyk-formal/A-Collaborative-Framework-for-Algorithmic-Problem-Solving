# -*- coding: utf-8 -*-
"""
算法竞赛RAG助手 
支持两种模式：
1. 直接在终端输入问题
2. 从MD文档读取问题并输出到MD文档
"""

from zai import ZhipuAiClient
import zai
from neo4j import GraphDatabase
import numpy as np
import json
import re
import os
import warnings
import subprocess
import tempfile
import time
import threading
import psutil

# ========= Configuration =========
ZHIPU_API_KEY = "your_zhipu_api_key_here"  # Replace with your actual API key
EMBEDDING_MODEL = "embedding-2"
CHAT_MODEL = "glm-4.5"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "passcode123"
NEO4J_DATABASE = "neo4j"

VECTOR_DIM = 1024

# Debug output control
SHOW_DEBUG_INFO = False  # Set to False to hide detailed debug information
SHOW_QUERY_WARNINGS = False  # Set to False to hide database query warnings

# ========= Initialization =========

zhipu = ZhipuAiClient(api_key=ZHIPU_API_KEY)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Filter warnings if not desired
if not SHOW_QUERY_WARNINGS:
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="neo4j")

# ========= Utility Functions =========
def debug_print(*args, **kwargs):
    """Controlled debug output function"""
    if SHOW_DEBUG_INFO:
        print(*args, **kwargs)

# ========= Code Validation Functionality =========
class CodeValidator:
    """代码验证器，用于编译和运行C++代码"""
    
    def __init__(self, time_limit=5, memory_limit=256):
        self.time_limit = time_limit  # 时间限制（秒）
        self.memory_limit = memory_limit  # 内存限制（MB）
    
    def compile_cpp_code(self, code: str):
        """编译C++代码"""
        import hashlib
        import os
        import time
        
        try:
            # 生成唯一的文件名，避免冲突
            code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
            timestamp = int(time.time() * 1000000)  # 微秒级时间戳
            cpp_file = f"temp_code_{timestamp}_{code_hash}.cpp"
            exe_file = f"temp_exe_{timestamp}_{code_hash}"
            
            # 写入代码文件
            with open(cpp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # 确保文件写入完成
            if hasattr(os, 'sync'):
                os.sync()
            time.sleep(0.01)  # 短暂等待确保文件系统写入完成
            
            # 验证文件确实包含新代码
            with open(cpp_file, 'r', encoding='utf-8') as f:
                written_code = f.read()
            
            if written_code != code:
                return {
                    'success': False,
                    'error_type': 'CE',
                    'error_message': '文件写入验证失败',
                    'cpp_file': cpp_file
                }
            
            # 编译命令
            compile_cmd = ['g++', '-o', exe_file, cpp_file, '-std=c++17', '-O2']
            
            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True, 
                text=True, 
                timeout=30,
                encoding='utf-8'
            )
            
            if compile_result.returncode == 0:
                # 确保可执行文件确实存在
                if not os.path.exists(exe_file):
                    return {
                        'success': False,
                        'error_type': 'CE',
                        'error_message': '编译后可执行文件不存在',
                        'cpp_file': cpp_file
                    }
                return {
                    'success': True,
                    'exe_file': exe_file,
                    'cpp_file': cpp_file
                }
            else:
                return {
                    'success': False,
                    'error_type': 'CE',  # Compilation Error
                    'error_message': compile_result.stderr,
                    'cpp_file': cpp_file
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error_type': 'CE',
                'error_message': '编译超时',
                'cpp_file': cpp_file if 'cpp_file' in locals() else None
            }
        except Exception as e:
            return {
                'success': False,
                'error_type': 'CE',
                'error_message': f'编译异常: {str(e)}',
                'cpp_file': cpp_file if 'cpp_file' in locals() else None
            }
    
    def run_code_with_input(self, exe_file: str, input_data: str):
        """运行可执行文件并提供输入"""
        import os
        import time
        
        try:
            # 确保可执行文件存在且可执行
            if not os.path.exists(exe_file):
                return {
                    'success': False,
                    'error_type': 'RE',
                    'error_message': f'可执行文件不存在: {exe_file}',
                    'time_used': 0,
                    'memory_used': 0
                }
            
            # 设置可执行权限
            try:
                os.chmod(exe_file, 0o755)
            except:
                pass
            
            start_time = time.time()
            
            # 创建进程 - 使用绝对路径确保运行正确的文件
            abs_exe_file = os.path.abspath(exe_file)
            process = subprocess.Popen(
                [abs_exe_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                cwd=os.getcwd()  # 明确设置工作目录
            )
            
            # 监控内存使用
            max_memory = 0
            def monitor_memory():
                nonlocal max_memory
                try:
                    import psutil
                    p = psutil.Process(process.pid)
                    while process.poll() is None:
                        try:
                            mem_info = p.memory_info()
                            current_memory = mem_info.rss / 1024 / 1024  # MB
                            max_memory = max(max_memory, current_memory)
                            if max_memory > self.memory_limit:
                                process.kill()
                                return
                            time.sleep(0.01)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            break
                except ImportError:
                    # 如果没有psutil，跳过内存监控
                    pass
            
            # 启动内存监控线程
            try:
                import psutil
                import threading
                monitor_thread = threading.Thread(target=monitor_memory)
                monitor_thread.daemon = True
                monitor_thread.start()
            except ImportError:
                pass
            
            # 运行程序
            try:
                stdout, stderr = process.communicate(input=input_data, timeout=self.time_limit)
                execution_time = time.time() - start_time
                
                if max_memory > self.memory_limit:
                    return {
                        'success': False,
                        'error_type': 'MLE',  # Memory Limit Exceeded
                        'error_message': f'内存超限: {max_memory:.2f}MB > {self.memory_limit}MB',
                        'memory_used': max_memory,
                        'time_used': execution_time
                    }
                
                if process.returncode == 0:
                    return {
                        'success': True,
                        'output': stdout,
                        'stderr': stderr,
                        'time_used': execution_time,
                        'memory_used': max_memory
                    }
                else:
                    return {
                        'success': False,
                        'error_type': 'RE',  # Runtime Error
                        'error_message': f'运行时错误 (返回码: {process.returncode})',
                        'stderr': stderr,
                        'time_used': execution_time,
                        'memory_used': max_memory
                    }
                    
            except subprocess.TimeoutExpired:
                process.kill()
                execution_time = time.time() - start_time
                return {
                    'success': False,
                    'error_type': 'TLE',  # Time Limit Exceeded
                    'error_message': f'时间超限: {execution_time:.2f}s > {self.time_limit}s',
                    'time_used': execution_time,
                    'memory_used': max_memory
                }
                
        except Exception as e:
            return {
                'success': False,
                'error_type': 'RE',
                'error_message': f'运行异常: {str(e)}',
                'time_used': 0,
                'memory_used': 0
            }
    
    def validate_sample(self, code: str, sample_input: str, expected_output: str):
        """验证单个样例"""
        import hashlib
        
        # 为调试添加代码哈希
        code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        debug_print(f"   🔍 验证代码哈希: {code_hash}")
        debug_print(f"   📝 代码长度: {len(code)} 字符")
        debug_print(f"   📥 输入数据: {repr(sample_input)}")
        
        # 编译代码
        debug_print(f"   🔨 开始编译代码...")
        compile_result = self.compile_cpp_code(code)
        if not compile_result['success']:
            debug_print(f"   ❌ 编译失败: {compile_result.get('error_message')}")
            self.cleanup_files(compile_result.get('cpp_file'))
            return compile_result
        
        debug_print(f"   ✅ 编译成功: {compile_result['exe_file']}")
        
        # 运行代码
        debug_print(f"   🚀 运行程序...")
        run_result = self.run_code_with_input(compile_result['exe_file'], sample_input)
        
        # 清理文件
        debug_print(f"   🗑️ 清理临时文件...")
        self.cleanup_files(compile_result['cpp_file'], compile_result['exe_file'])
        
        if not run_result['success']:
            debug_print(f"   ❌ 运行失败: {run_result.get('error_message')}")
            return run_result
        
        # 比较输出
        actual_output = run_result['output'].strip()
        expected_output = expected_output.strip()
        
        debug_print(f"   📤 程序输出: {repr(actual_output)}")
        debug_print(f"   🎯 期望输出: {repr(expected_output)}")
        
        # 调试输出比较信息
        print(f"\n=== 输出比较调试信息 ===")
        print(f"期望输出长度: {len(expected_output)}")
        print(f"实际输出长度: {len(actual_output)}")
        print(f"期望输出repr: {repr(expected_output)}")
        print(f"实际输出repr: {repr(actual_output)}")
        print(f"字符串相等: {actual_output == expected_output}")
        
        # 标准化输出格式进行比较
        def normalize_output(output):
            """标准化输出格式"""
            # 统一换行符为\n
            output = output.replace('\r\n', '\n').replace('\r', '\n')
            # 去除每行末尾空格
            lines = [line.rstrip() for line in output.split('\n')]
            # 去除空行
            lines = [line for line in lines if line.strip()]
            return '\n'.join(lines)
        
        normalized_actual = normalize_output(actual_output)
        normalized_expected = normalize_output(expected_output)
        
        print(f"标准化后期望输出: {repr(normalized_expected)}")
        print(f"标准化后实际输出: {repr(normalized_actual)}")
        print(f"标准化后相等: {normalized_actual == normalized_expected}")
        print(f"=========================\n")
        
        if normalized_actual == normalized_expected:
            return {
                'success': True,
                'status': 'AC',  # Accepted
                'time_used': run_result['time_used'],
                'memory_used': run_result['memory_used']
            }
        else:
            return {
                'success': False,
                'error_type': 'WA',  # Wrong Answer
                'error_message': f'答案错误',
                'expected': expected_output,
                'actual': actual_output,
                'time_used': run_result['time_used'],
                'memory_used': run_result['memory_used']
            }
    
    def cleanup_files(self, *files):
        """清理临时文件"""
        import os
        import time
        
        for file in files:
            if file and os.path.exists(file):
                try:
                    # 强制删除文件，重试机制
                    for attempt in range(3):
                        try:
                            os.unlink(file)
                            break
                        except OSError as e:
                            if attempt < 2:
                                time.sleep(0.1)  # 等待文件系统释放
                            else:
                                debug_print(f"警告: 无法删除临时文件 {file}: {e}")
                except Exception as e:
                    debug_print(f"清理文件 {file} 时出错: {e}")



def validate_and_improve_solution(code: str, samples: list, max_iterations: int = 5):
    """
    自动验证样例并迭代改进代码
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
    增强版代码验证，针对复杂算法问题提供更深入的分析
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



def request_code_fix_enhanced(code: str, error_report: str, problem_analysis: dict, 
                             problem_summary: dict = None, context: str = "", attempt_num: int = 1):
    """增强的代码修复 - 包含完整题目信息"""
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
        import re
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

def extract_code_from_ai_response(response_text: str):
    """从AI响应中提取代码，支持多种格式"""
    import re
    
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
    """简单验证是否为有效的C++代码"""
    if not code or len(code) < 10:
        return False
    
    # 检查是否包含C++关键字和结构
    cpp_indicators = [
        '#include', 'int main', 'using namespace', 'std::', 'cout', 'cin',
        'vector', 'string', 'for', 'while', 'if', 'return', '{', '}', ';'
    ]
    
    indicators_found = sum(1 for indicator in cpp_indicators if indicator in code)
    return indicators_found >= 3  # 至少包含3个C++特征

def generate_error_report(validation_results):
    """生成详细的错误报告"""
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

def request_code_fix_with_retry(fix_prompt: str, max_retries: int = 3):
    """带重试机制的API调用"""
    import time
    
    for attempt in range(max_retries):
        try:
            response = zhipu.chat.completions.create(
                model=CHAT_MODEL,
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

def request_code_fix(code: str, error_report: str):
    """请求AI修复代码"""
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

def l2_normalize(vec):
    v = np.array(vec, dtype=np.float32)
    n = np.linalg.norm(v) + 1e-12
    return (v / n).tolist()

def embed_query_with_zhipu(text: str):
    resp = zhipu.embeddings.create(model=EMBEDDING_MODEL, input=text)
    vec = resp.data[0].embedding
    return l2_normalize(vec)

def extract_algorithm_keywords(question: str):
    algorithm_keywords = [
        "动态规划", "dp", "贪心", "分治", "二分", "双指针", "滑动窗口", "前缀和", "差分",
        "线段树", "树状数组", "并查集", "最短路", "最小生成树", "拓扑排序", "强连通分量",
        "网络流", "最大流", "最小割", "二分图", "匹配", "匈牙利", "KM算法", "费用流",
        "莫队", "分块", "主席树", "可持久化", "平衡树", "红黑树", "AVL", "Treap",
        "哈希", "KMP", "AC自动机", "后缀数组", "后缀自动机", "回文树", "Manacher",
        "FFT", "NTT", "快速幂", "矩阵快速幂", "高斯消元", "线性基", "容斥原理",
        "组合数学", "数论", "欧拉函数", "莫比乌斯", "杜教筛", "min25筛", "洲阁筛",
        "几何", "凸包", "旋转卡壳", "半平面交", "圆", "多边形", "扫描线", "CDQ分治",
        "整体二分", "离线", "在线", "强制在线", "可持久化", "回滚", "撤销"
    ]
    
    found_keywords = []
    question_lower = question.lower()
    for keyword in algorithm_keywords:
        if keyword.lower() in question_lower:
            found_keywords.append(keyword)
    
    return found_keywords

def clean_query_text(text: str):
    """清理查询文本，移除可能导致Lucene解析错误的特殊字符"""
    if not text or not text.strip():
        return "算法 题目"
    
    # 移除或替换Lucene特殊字符和可能导致问题的符号
    special_chars = [
        '[', ']', '(', ')', '{', '}', '~', '^', '"', '*', '?', '\\', 
        ':', '+', '-', '!', '/', '|', '&', '<', '>', '=', '@', '#',
        '$', '%', '。', '，', '；', '：', '！', '？', '、', '《', '》',
        '"', '"', ''', ''', '【', '】', '（', '）', '·', '…', '—',
        '`', "'", '\n', '\r', '\t'  # 新增一些可能导致问题的字符
    ]
    
    cleaned = text
    for char in special_chars:
        cleaned = cleaned.replace(char, ' ')
    
    # 移除连续的空格，保留单个空格
    cleaned = ' '.join(cleaned.split())
    
    # 移除前后空格
    cleaned = cleaned.strip()
    
    # 如果清理后的文本太短或为空，使用默认搜索词
    if len(cleaned) < 2:
        cleaned = "算法 题目"
    
    # 限制查询长度，避免过长的查询导致问题
    if len(cleaned) > 200:
        cleaned = cleaned[:200].strip()
    
    # 确保不以特殊字符结尾，这可能导致Lucene解析问题
    while cleaned and cleaned[-1] in '+-&|!(){}[]^"~*?:\\':
        cleaned = cleaned[:-1].strip()
    
    # 如果清理后为空，返回默认值
    if not cleaned:
        cleaned = "算法 题目"
    
    return cleaned

# ========= 增强的混合检索 =========
CYPHER_ENHANCED_HYBRID = """
// 参数：$q (string), $qvec (list<float>), $keywords (list<string>)

// A. 全文候选（加权 0.3）
CALL ($q) {
  WITH $q AS q
  CALL db.index.fulltext.queryNodes('alg_fulltext', q) YIELD node, score
  RETURN collect({a: node, s: score * 0.3, route:'fulltext'}) AS T
}

// B. 向量候选（加权 0.5）
CALL ($qvec) {
  WITH $qvec AS qv
  CALL db.index.vector.queryNodes('chunk_vec_idx', 15, qv) YIELD node, score
  MATCH (node)<-[:HAS_CHUNK]-(alg:Algorithm)
  RETURN collect({a: alg, s: score * 0.5, route:'vector'}) AS V
}

// C. 关键词匹配候选（加权 0.2）
CALL ($keywords) {
  WITH $keywords AS kw
  UNWIND kw AS keyword
  MATCH (a:Algorithm)
  WHERE any(alias IN a.aliases WHERE toLower(alias) CONTAINS toLower(keyword))
     OR any(k IN a.keywords WHERE toLower(k) CONTAINS toLower(keyword))
     OR toLower(a.title) CONTAINS toLower(keyword)
  RETURN collect({a: a, s: 0.2, route:'keyword'}) AS K
}

// 合并三路候选并按算法聚合分数
WITH T + V + K AS R
UNWIND R AS r
WITH r.a AS a, collect(r) AS contribs
WITH a, reduce(s=0.0, x IN contribs | s + x.s) AS fused, contribs
ORDER BY fused DESC
LIMIT 8

// 图扩展 + 完整信息（增强示例代码获取）
OPTIONAL MATCH (a)-[:PREREQUISITE]->(p:Concept)
OPTIONAL MATCH (a)-[:APPLICATION]->(u:Concept)
OPTIONAL MATCH (a)-[:PITFALL]->(f:Concept)
OPTIONAL MATCH (a)-[:HAS_EXAMPLE]->(e:Example)
OPTIONAL MATCH (a)-[:HAS_CHUNK]->(c:Chunk)

// 获取详细的示例代码信息
WITH a, fused, contribs,
     collect(DISTINCT p.name)[0..8] AS prereq,
     collect(DISTINCT u.name)[0..8] AS apps,
     collect(DISTINCT f.name)[0..8] AS pitfalls,
     collect(DISTINCT e)[0..8] AS all_examples,
     [c IN collect(DISTINCT c)[0..5] | c.content] AS snippets

// 构建详细的示例信息，只包含确实存在的属性
WITH a, fused, contribs, prereq, apps, pitfalls, snippets,
     [ex IN all_examples | {
         id: ex.id,
         title: ex.title,
         description: ex.description,
         code: ex.code,
         solution: ex.solution
     }] AS detailed_examples

RETURN a.uid AS uid, a.title AS title,
       a.principle AS principle, a.cpx_time AS time, a.cpx_space AS space,
       a.intro AS intro, a.keywords AS keywords, a.aliases AS aliases,
       prereq, apps, pitfalls, detailed_examples, snippets, fused, contribs;
"""

def enhanced_hybrid_search(question: str, keywords_hint: str = ""):
    """增强的混合检索，支持AI提取的关键词提示"""
    # 使用AI总结的内容进行查询，避免特殊字符问题
    if keywords_hint:
        # 如果有AI提取的关键词，优先使用这些关键词
        search_text = keywords_hint
        debug_print(f"【使用AI提取的关键词】{keywords_hint}")
    else:
        # 如果没有关键词提示，使用原来的清理方法
        search_text = clean_query_text(question)
        debug_print(f"【原始查询】{question[:50]}...")
        debug_print(f"【清理后查询】{search_text}")
    
    qvec = embed_query_with_zhipu(question)
    # 结合原始关键词提取和AI提取的关键词
    extracted_keywords = extract_algorithm_keywords(question)
    if keywords_hint:
        # 添加AI提取的关键词（保持权重顺序）
        ai_keywords = [kw.strip() for kw in keywords_hint.split(',') if kw.strip()]
        # 使用有序去重，保持AI关键词的权重顺序在前
        seen = set()
        merged_keywords = []
        # 首先添加AI关键词（按权重排序）
        for kw in ai_keywords:
            if kw not in seen:
                merged_keywords.append(kw)
                seen.add(kw)
        # 然后添加原始关键词
        for kw in extracted_keywords:
            if kw not in seen:
                merged_keywords.append(kw)
                seen.add(kw)
        extracted_keywords = merged_keywords
    
    debug_print(f"【合并关键词】{extracted_keywords}")
    
    # 验证查询字符串，避免空查询或有问题的查询
    if not search_text or search_text.strip() == "" or len(search_text.strip()) < 2:
        search_text = "算法 题目"
        debug_print(f"【查询修正】使用默认查询: {search_text}")
    
    # 额外检查：如果查询字符串包含可能导致Lucene问题的字符，直接使用备用查询
    lucene_problem_chars = ['[', ']', '(', ')', '{', '}', '<', '>', '"', "'"]
    has_lucene_issues = any(char in search_text for char in lucene_problem_chars)
    
    if has_lucene_issues:
        debug_print(f"【查询策略】检测到特殊字符，直接使用备用查询")
        use_backup_directly = True
    else:
        use_backup_directly = False
    
    # 如果没有Lucene问题，尝试主查询
    rows = []
    if not use_backup_directly:
        try:
            with driver.session(database=NEO4J_DATABASE) as sess:
                recs = sess.run(CYPHER_ENHANCED_HYBRID, {
                    "q": search_text,  # 使用处理后的搜索文本
                    "qvec": qvec,
                    "keywords": extracted_keywords
                })
                rows = [r.data() for r in recs]
                if rows:
                    debug_print("✅ 主查询成功")
        except Exception as e:
            debug_print(f"⚠️ 数据库查询失败：{e}")
            debug_print("🔄 尝试使用备用查询策略...")
            use_backup_directly = True
    
    # 使用备用查询
    if use_backup_directly or not rows:
        try:
            with driver.session(database=NEO4J_DATABASE) as sess:
                backup_query = """
                MATCH (a:Algorithm)
                WITH a, 
                     CASE 
                       WHEN size($keywords) = 0 THEN 0.1
                       WHEN any(keyword IN $keywords WHERE toLower(a.title) CONTAINS toLower(keyword)) THEN 0.8
                       WHEN any(keyword IN $keywords WHERE any(alias IN a.aliases WHERE toLower(alias) CONTAINS toLower(keyword))) THEN 0.6
                       WHEN any(keyword IN $keywords WHERE any(k IN a.keywords WHERE toLower(k) CONTAINS toLower(keyword))) THEN 0.4
                       ELSE 0.1
                     END AS score
                WHERE score > 0.1
                WITH a, score
                ORDER BY score DESC
                LIMIT 5
                
                OPTIONAL MATCH (a)-[:PREREQUISITE]->(p:Concept)
                OPTIONAL MATCH (a)-[:APPLICATION]->(u:Concept)
                OPTIONAL MATCH (a)-[:PITFALL]->(f:Concept)
                OPTIONAL MATCH (a)-[:HAS_EXAMPLE]->(e:Example)
                OPTIONAL MATCH (a)-[:HAS_CHUNK]->(c:Chunk)
                
                // 获取详细的示例代码信息（备用查询）
                WITH a, score,
                     collect(DISTINCT p.name)[0..8] AS prereq,
                     collect(DISTINCT u.name)[0..8] AS apps,
                     collect(DISTINCT f.name)[0..8] AS pitfalls,
                     collect(DISTINCT e)[0..8] AS all_examples,
                     [c IN collect(DISTINCT c)[0..5] | c.content] AS snippets

                // 构建详细的示例信息，只包含确实存在的属性（备用查询）
                WITH a, score, prereq, apps, pitfalls, snippets,
                     [ex IN all_examples | {
                         id: ex.id,
                         title: ex.title,
                         description: ex.description,
                         code: ex.code,
                         solution: ex.solution
                     }] AS detailed_examples
                
                RETURN a.uid AS uid, a.title AS title,
                       a.principle AS principle, a.cpx_time AS time, a.cpx_space AS space,
                       a.intro AS intro, a.keywords AS keywords, a.aliases AS aliases,
                       prereq, apps, pitfalls, detailed_examples, snippets, score AS fused, 
                       [{route: 'keyword', s: score}] AS contribs
                """
                
                recs = sess.run(backup_query, {"keywords": extracted_keywords})
                rows = [r.data() for r in recs]
                
                if rows:
                    debug_print("✅ 备用查询成功")
                else:
                    debug_print("⚠️ 备用查询也未找到结果，使用默认算法信息")
                    
        except Exception as backup_error:
            debug_print(f"❌ 备用查询也失败：{backup_error}")
            rows = []
    
    # 如果所有查询都失败，创建一个空的结果但让系统继续运行
    if not rows:
        debug_print("🔧 所有查询都失败，将使用基础上下文生成回答")
    
    debug_print(f"【检索结果】找到 {len(rows)} 个相关算法")
    for r in rows:
        routes = [c["route"] for c in (r.get("contribs") or [])]
        debug_print(f"[候选] {r['title']} | fused={r['fused']:.4f} | routes={routes}")
    
    return rows

# ========= 智能上下文构建 =========
def build_enhanced_context(results, question: str):
    if not results:
        # 如果没有检索结果，提供基础上下文
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

# ========= 优化的Prompt结构 =========
def create_optimized_prompt(question: str, context: str, problem_info: dict = None):
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
    """将最终的prompt保存到final_prompt.md文件"""
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

# ========= 智能回答生成 =========
def generate_enhanced_answer_with_validation(question: str, context: str, problem_info=None):
    """生成答案并进行代码验证 - 传递完整上下文"""
    
    print("� 开始自动验证流程...")
    
    # 首先生成初始答案
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

def extract_samples_from_problem(problem_info):
    """从题目信息中提取样例数据"""
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
    """从回答中提取C++代码"""
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
    """更新回答中的代码"""
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

def generate_enhanced_answer(question: str, context: str, problem_info: str = ""):
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
            model=CHAT_MODEL,
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

# ========= 代码后处理 =========
def post_process_code(response: str):
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

# ========= MD文档处理函数 =========
def read_input_md():
    """从input.md文件读取问题"""
    input_file = "input.md"
    if not os.path.exists(input_file):
        print(f"❌ 未找到 {input_file} 文件")
        return None
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 检查是否有内容
        if not content:
            print(f"❌ {input_file} 文件为空")
            return None
        
        # 优先查找"## 当前问题"部分
        problem_match = re.search(r'## 当前问题\s*\n(.*?)(?=\n## |$)', content, re.DOTALL)
        if problem_match:
            problem_text = problem_match.group(1).strip()
            # 移除示例部分
            problem_text = re.sub(r'例如：.*', '', problem_text, flags=re.DOTALL).strip()
            if problem_text and not problem_text.startswith('请在这里输入'):
                return problem_text
        
        # 如果没有找到"当前问题"部分，则返回整个文件内容（可能是完整题目）
        if content and not content.startswith('# 算法问题输入'):
            print("📖 检测到完整题目内容，将通过AI总结提取核心信息")
            return content
        
        print(f"❌ 请在 {input_file} 文件中输入具体问题")
        return None
        
    except Exception as e:
        print(f"❌ 读取 {input_file} 文件失败：{e}")
        return None

def summarize_problem_with_ai(content: str):
    """使用AI总结题目内容，提取核心算法需求和关键词"""
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
            model=CHAT_MODEL,
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

def write_output_md(question, answer, meta_info=None):
    """将结果写入output.md文件"""
    output_file = "output.md"
    try:
        # 构建基础内容
        output_content = f"""# 算法问题解答

## 问题
{question}

## 解答
{answer}
"""
        
        # 如果有元信息，添加到输出中
        if meta_info:
            output_content += "\n## 分析信息\n"
            for key, value in meta_info.items():
                if value:  # 只添加非空值
                    output_content += f"- **{key}**: {value}\n"
        
        output_content += "\n---\n*此文件由算法竞赛RAG助手自动生成*"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"✅ 结果已保存到 {output_file}")
        
    except Exception as e:
        print(f"❌ 写入 {output_file} 文件失败：{e}")

# ========= 主函数 =========
def main():
    print("🤖 算法竞赛RAG助手 ")
    print("=" * 50)
    print("支持模式：")
    print("1. 直接在终端输入问题")
    print("2. 从MD文档读取问题并输出到MD文档")
    print("=" * 50)
    
    while True:
        try:
            print("\n请选择使用模式：")
            print("1. 直接在终端输入问题")
            print("2. 从input.md读取问题，输出到output.md")
            print("3. 退出")
            
            mode = input("\n请输入选择 (1-3)：").strip()
            
            if mode == "1":
                # 模式1：直接终端输入
                question = input("\n请输入你的算法问题：").strip()
                if not question:
                    print("❌ 请输入有效问题")
                    continue
                
                print(f"\n🔍 正在检索相关算法信息...")
                results = enhanced_hybrid_search(question)
                
                # 即使没有检索结果也继续生成回答
                context = build_enhanced_context(results, question)
                response = generate_enhanced_answer_with_validation(question, context)
                processed_response = post_process_code(response)
                
                # 保存到txt文件
                with open(f"answer_{len(question)}.txt", "w", encoding="utf-8") as f:
                    f.write(f"问题：{question}\n\n")
                    f.write(f"回答：{processed_response}")
                
                print(f"\n💾 结果已保存到 answer_{len(question)}.txt")
                
            elif mode == "2":
                # 模式2：从MD文档读取
                md_content = read_input_md()
                if not md_content:
                    continue
                
                print(f"📖 从input.md读取到内容：{md_content[:100]}...")
                
                # 使用AI分析和总结问题
                problem_summary = summarize_problem_with_ai(md_content)
                
                if problem_summary and problem_summary.get('keywords'):
                    print("✅ AI分析完成！")
                    debug_print(f"🔍 提取的关键词：{problem_summary['keywords']}")
                    print(f"📝 核心问题：{problem_summary['core_problem'][:100]}...")
                    
                    # 显示多组样例信息
                    sample_count = problem_summary.get('sample_count', 0)
                    samples = problem_summary.get('samples', [])
                    if samples:
                        print(f"📊 包含 {sample_count} 组样例：")
                        for i, sample in enumerate(samples, 1):
                            input_preview = sample['input'][:30].replace('\n', '\\n')
                            output_preview = sample['output'][:20].replace('\n', '\\n')
                            print(f"   样例{i}: 输入='{input_preview}...' 输出='{output_preview}...'")
                    
                    # 使用AI分析的结果进行检索
                    question_for_search = problem_summary['core_problem']
                    keywords_for_search = ",".join(problem_summary['keywords'])
                    
                    # 显示关键词权重信息
                    keyword_weights = problem_summary.get('keyword_weights', {})
                    if keyword_weights:
                        debug_print(f"🎯 关键词权重分布：")
                        for kw in problem_summary['keywords']:
                            weight = keyword_weights.get(kw, 0.5)
                            print(f"   {kw}: {weight:.2f}")
                    
                    print(f"\n🔍 正在检索相关算法信息...")
                    # 增强的混合检索，使用AI提取的关键词
                    results = enhanced_hybrid_search(question_for_search, keywords_for_search)
                    
                    # 构建上下文并生成答案，包含原题
                    context = build_enhanced_context(results, question_for_search)
                    
                    # 在生成答案时，使用结构化的题目信息
                    response = generate_enhanced_answer_with_validation(problem_summary['core_problem'], context, problem_summary)
                    processed_response = post_process_code(response)
                    
                    # 将结果写入输出文件，包含AI分析的元信息
                    keyword_weights_info = ""
                    if problem_summary.get('keyword_weights'):
                        weights_list = [f"{kw}({weight:.2f})" for kw, weight in 
                                      [(k, problem_summary['keyword_weights'].get(k, 0.5)) 
                                       for k in problem_summary['keywords']]]
                        keyword_weights_info = ", ".join(weights_list)
                    
                    write_output_md(problem_summary['original_content'], processed_response, {
                        "AI提取的关键词": ", ".join(problem_summary['keywords']),
                        "关键词权重": keyword_weights_info if keyword_weights_info else "未分析",
                        "检索到的算法": len(results) if results else 0,
                        "样例组数": sample_count,
                        "题目结构化程度": "完整" if samples else "部分",
                        "分析方式": "AI智能分析(含权重排序)"
                    })
                    
                else:
                    print("❌ AI分析失败，使用传统方法处理...")
                    # 降级到传统方法
                    question = md_content[:200]  # 取前200个字符作为问题
                    print(f"\n🔍 正在检索相关算法信息...")
                    results = enhanced_hybrid_search(question)
                    
                    context = build_enhanced_context(results, question)
                    response = generate_enhanced_answer_with_validation(md_content, context)  # 使用完整内容
                    processed_response = post_process_code(response)
                    
                    write_output_md(md_content, processed_response, {"处理方式": "传统方法（AI分析失败）"})
                
            elif mode == "3":
                print("\n👋 再见！")
                break
                
            else:
                print("❌ 无效选择，请输入1-3")
                
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误：{e}")
            continue
    
    driver.close()

if __name__ == "__main__":
    main()
