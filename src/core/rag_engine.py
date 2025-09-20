"""
RAG引擎核心模块
整合所有功能模块，提供统一的RAG系统接口
"""

import os
import sys
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config.settings import settings
from src.core.ai_client import get_zhipu_client, get_embedding
from src.core.search_engine import enhanced_hybrid_search
from src.core.code_validator import CodeValidator
from src.services.problem_analyzer import summarize_problem_with_ai
from src.services.answer_generator import (
    build_enhanced_context, 
    create_optimized_prompt, 
    generate_enhanced_answer,
    save_final_prompt
)
from src.services.validation_service import (
    validate_and_improve_solution_enhanced,
    extract_samples_from_problem,
    extract_code_from_response,
    update_code_in_response
)
from src.utils.file_manager import read_input_md, write_output_md


class RAGEngine:
    """RAG引擎主类，整合所有功能模块"""
    
    def __init__(self):
        """初始化RAG引擎"""
        self.zhipu_client = None
        self.code_validator = None
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化各个组件"""
        try:
            # 初始化AI客户端
            self.zhipu_client = get_zhipu_client()
            print("✅ AI客户端初始化成功")
            
            # 初始化代码验证器
            self.code_validator = CodeValidator()
            print("✅ 代码验证器初始化成功")
            
        except Exception as e:
            print(f"❌ 组件初始化失败: {e}")
            raise e
    
    def solve_problem(self, problem_content: str, enable_validation: bool = True) -> Dict[str, Any]:
        """
        解决算法问题的主入口
        
        Args:
            problem_content: 问题内容
            enable_validation: 是否启用代码验证
            
        Returns:
            包含解答结果的字典
        """
        try:
            print("🚀 开始处理问题...")
            
            # 1. AI分析问题
            print("📝 分析问题...")
            problem_summary = summarize_problem_with_ai(problem_content)
            
            # 2. 检索相关算法
            print("🔍 检索相关算法...")
            keywords = problem_summary.get('keywords', [])
            keywords_str = ",".join(keywords) if keywords else ""
            retrieved_algorithms = enhanced_hybrid_search(problem_content, keywords_str)
            
            # 3. 构建上下文
            print("📚 构建上下文...")
            context = build_enhanced_context(retrieved_algorithms, problem_content)
            
            # 4. 生成解答
            print("💡 生成解答...")
            if enable_validation:
                # 使用带验证的解答生成
                # 首先生成初始代码
                prompt = create_optimized_prompt(problem_content, context, problem_summary)
                initial_answer = generate_enhanced_answer(problem_content, context, str(problem_summary))
                
                # 提取代码和样例进行验证
                code = extract_code_from_response(initial_answer)
                samples = extract_samples_from_problem(problem_summary)
                
                if code and samples:
                    result = validate_and_improve_solution_enhanced(
                        code, 
                        samples, 
                        problem_summary,
                        problem_summary,
                        context
                    )
                else:
                    result = {
                        'success': True,
                        'answer': initial_answer,
                        'validation_enabled': False
                    }
            else:
                # 使用简单解答生成
                prompt = create_optimized_prompt(problem_content, context, problem_summary)
                answer = generate_enhanced_answer(problem_content, context, str(problem_summary))
                result = {
                    'success': True,
                    'answer': answer,
                    'validation_enabled': False
                }
            
            print("✅ 问题处理完成")
            return result
            
        except Exception as e:
            print(f"❌ 处理问题时发生错误: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'PROCESSING_ERROR'
            }
    
    def process_file(self, input_file: str, output_file: str, enable_validation: bool = True) -> Dict[str, Any]:
        """
        处理文件中的问题
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            enable_validation: 是否启用代码验证
            
        Returns:
            处理结果
        """
        try:
            # 读取输入文件
            problem_content = read_input_md(input_file)
            
            # 解决问题
            result = self.solve_problem(problem_content, enable_validation)
            
            if result['success']:
                # 写入输出文件
                write_output_md(output_file, problem_content, result['answer'])
                result['output_file'] = output_file
            
            return result
            
        except Exception as e:
            print(f"❌ 处理文件时发生错误: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'FILE_PROCESSING_ERROR'
            }


# 创建全局RAG引擎实例
rag_engine = RAGEngine()
