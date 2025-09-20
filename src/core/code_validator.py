# -*- coding: utf-8 -*-
"""
代码验证器 - 完全保持原有功能
从main.py中提取的CodeValidator类，功能完全不变
"""

import hashlib
import os
import time
import subprocess
import threading
import psutil
from ..config.settings import settings

class CodeValidator:
    """代码验证器，用于编译和运行C++代码 - 保持原有功能完全不变"""
    
    def __init__(self, time_limit=None, memory_limit=None):
        # 使用配置中的默认值，保持原有接口
        self.time_limit = time_limit or settings.validation.time_limit
        self.memory_limit = memory_limit or settings.validation.memory_limit
    
    def compile_cpp_code(self, code: str):
        """编译C++代码 - 保持原有功能完全不变"""
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
        """运行可执行文件并提供输入 - 保持原有功能完全不变"""
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
        """验证单个样例 - 保持原有功能完全不变"""
        import hashlib
        
        # 为调试添加代码哈希
        code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        if settings.system.show_debug_info:
            print(f"   🔍 验证代码哈希: {code_hash}")
            print(f"   📝 代码长度: {len(code)} 字符")
            print(f"   📥 输入数据: {repr(sample_input)}")
        
        # 编译代码
        if settings.system.show_debug_info:
            print(f"   🔨 开始编译代码...")
        compile_result = self.compile_cpp_code(code)
        if not compile_result['success']:
            if settings.system.show_debug_info:
                print(f"   ❌ 编译失败: {compile_result.get('error_message')}")
            self.cleanup_files(compile_result.get('cpp_file'))
            return compile_result
        
        if settings.system.show_debug_info:
            print(f"   ✅ 编译成功: {compile_result['exe_file']}")
        
        # 运行代码
        if settings.system.show_debug_info:
            print(f"   🚀 运行程序...")
        run_result = self.run_code_with_input(compile_result['exe_file'], sample_input)
        
        # 清理文件
        if settings.system.show_debug_info:
            print(f"   🗑️ 清理临时文件...")
        self.cleanup_files(compile_result['cpp_file'], compile_result['exe_file'])
        
        if not run_result['success']:
            if settings.system.show_debug_info:
                print(f"   ❌ 运行失败: {run_result.get('error_message')}")
            return run_result
        
        # 比较输出
        actual_output = run_result['output'].strip()
        expected_output = expected_output.strip()
        
        if settings.system.show_debug_info:
            print(f"   📤 程序输出: {repr(actual_output)}")
            print(f"   🎯 期望输出: {repr(expected_output)}")
        
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
        """清理临时文件 - 保持原有功能完全不变"""
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
                                if settings.system.show_debug_info:
                                    print(f"警告: 无法删除临时文件 {file}: {e}")
                except Exception as e:
                    if settings.system.show_debug_info:
                        print(f"清理文件 {file} 时出错: {e}")

