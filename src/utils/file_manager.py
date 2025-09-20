# -*- coding: utf-8 -*-
"""
文件管理工具 - 完全保持原有功能
从main.py中提取的文件处理相关函数，功能完全不变
"""

import os
import re
from ..config.settings import settings

def debug_print(*args, **kwargs):
    """受控的调试输出函数 - 保持原有功能"""
    if settings.system.show_debug_info:
        print(*args, **kwargs)

def read_input_md():
    """从input.md文件读取问题 - 保持原有功能"""
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

def write_output_md(question, answer, meta_info=None):
    """将结果写入output.md文件 - 保持原有功能"""
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

