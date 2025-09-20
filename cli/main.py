# -*- coding: utf-8 -*-
"""
Command line interface main program - Maintains original functionality, adds new CLI options
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.rag_engine import rag_engine
from src.config.settings import settings

def main():
    """Main function - Supports original functionality and new CLI options"""
    parser = argparse.ArgumentParser(
        description='Algorithm Competition RAG Assistant - Intelligent algorithm problem analysis and code generation system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python cli/main.py                    # Interactive mode (original functionality)
  python cli/main.py --web              # Start web interface
  python cli/main.py --solve "problem content"  # Solve problem directly
  python cli/main.py --file input.md    # Read problem from file
  python cli/main.py --validate code.cpp samples.txt  # Validate code
        """
    )
    
    # 添加参数
    parser.add_argument('--web', action='store_true', 
                       help='启动Web界面')
    parser.add_argument('--solve', type=str, 
                       help='直接解决指定的题目')
    parser.add_argument('--file', type=str, 
                       help='从指定文件读取题目')
    parser.add_argument('--validate', nargs=2, metavar=('CODE_FILE', 'SAMPLES_FILE'),
                       help='验证代码文件')
    parser.add_argument('--output', type=str, 
                       help='指定输出文件')
    parser.add_argument('--no-validation', action='store_true',
                       help='禁用代码验证')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    parser.add_argument('--version', action='version', version='算法竞赛RAG助手 v2.0.0')
    
    args = parser.parse_args()
    
    # 设置调试模式
    if args.debug:
        settings.system.show_debug_info = True
        print("🐛 调试模式已启用")
    
    # 根据参数执行相应功能
    if args.web:
        start_web_interface()
    elif args.solve:
        solve_problem_direct(args.solve, args.output, not args.no_validation)
    elif args.file:
        solve_problem_from_file(args.file, args.output, not args.no_validation)
    elif args.validate:
        validate_code_from_files(args.validate[0], args.validate[1])
    else:
        # 默认进入交互式模式（原有功能）
        start_interactive_mode()

def start_web_interface():
    """启动Web界面"""
    import os
    port = int(os.environ.get('FLASK_PORT', 8080))
    print("🌐 启动Web界面...")
    print(f"📱 访问地址: http://localhost:{port}")
    print("=" * 50)
    
    try:
        from web.app import app, socketio
        socketio.run(app, debug=settings.system.show_debug_info, host='0.0.0.0', port=port)
    except ImportError as e:
        print(f"❌ 无法启动Web界面: {e}")
        print("💡 请确保已安装Flask和Flask-SocketIO")
        sys.exit(1)

def solve_problem_direct(problem_content: str, output_file: str = None, enable_validation: bool = True):
    """直接解决指定题目"""
    print("🔍 开始解决题目...")
    print(f"📝 题目: {problem_content[:100]}{'...' if len(problem_content) > 100 else ''}")
    
    try:
        # 使用RAG引擎解决题目
        result = rag_engine.solve_problem(problem_content, enable_validation)
        
        if result['success']:
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"问题：{problem_content}\n\n")
                    f.write(f"回答：{result['answer']}")
                print(f"💾 结果已保存到 {output_file}")
            else:
                print("\n" + "="*50)
                print("📋 解答结果:")
                print("="*50)
                print(result['answer'])
            
            print("✅ 解题完成！")
        else:
            print(f"❌ 解题失败: {result.get('error', '未知错误')}")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ 解题失败: {e}")
        sys.exit(1)

def solve_problem_from_file(input_file: str, output_file: str = None, enable_validation: bool = True):
    """从文件读取题目并解决"""
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        sys.exit(1)
    
    print(f"📖 从文件读取题目: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            print("❌ 文件为空")
            sys.exit(1)
        
        # 使用RAG引擎处理文件
        result = rag_engine.process_file(input_file, output_file or 'output.md', enable_validation)
        
        if result['success']:
            print("✅ 文件处理完成！")
            if output_file:
                print(f"💾 结果已保存到 {output_file}")
            else:
                print("💾 结果已保存到 output.md")
        else:
            print(f"❌ 文件处理失败: {result.get('error', '未知错误')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 处理文件失败: {e}")
        sys.exit(1)

def validate_code_from_files(code_file: str, samples_file: str):
    """验证代码文件"""
    if not os.path.exists(code_file):
        print(f"❌ 代码文件不存在: {code_file}")
        sys.exit(1)
    
    if not os.path.exists(samples_file):
        print(f"❌ 样例文件不存在: {samples_file}")
        sys.exit(1)
    
    print(f"🔍 验证代码: {code_file}")
    print(f"📋 使用样例: {samples_file}")
    
    try:
        # 读取代码
        with open(code_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 读取样例（假设是JSON格式）
        import json
        with open(samples_file, 'r', encoding='utf-8') as f:
            samples_data = json.load(f)
        
        samples = samples_data.get('samples', [])
        if not samples:
            print("❌ 样例文件格式错误或为空")
            sys.exit(1)
        
        # 进行验证
        validation_result = rag_engine.validate_code_with_samples(code, samples)
        
        if validation_result['success']:
            print("✅ 验证成功！所有样例都通过了测试。")
        else:
            print("❌ 验证失败，部分样例未通过测试。")
            for result in validation_result['results']:
                if not result['result']['success']:
                    error_type = result['result'].get('error_type', 'Unknown')
                    error_msg = result['result'].get('error_message', '未知错误')
                    print(f"   样例 {result['sample_id']}: {error_type} - {error_msg}")
        
        print(f"📊 验证统计: 尝试了 {validation_result['iterations']} 次")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        sys.exit(1)

def start_interactive_mode():
    """启动交互式模式（原有功能）"""
    print("🤖 算法竞赛RAG助手 ")
    print("=" * 50)
    print("支持模式：")
    print("1. 直接在终端输入问题")
    print("2. 从MD文档读取问题并输出到MD文档")
    print("3. 启动Web界面")
    print("=" * 50)
    
    while True:
        try:
            print("\n请选择使用模式：")
            print("1. 直接在终端输入问题")
            print("2. 从input.md读取问题，输出到output.md")
            print("3. 启动Web界面")
            print("4. 退出")
            
            mode = input("\n请输入选择 (1-4)：").strip()
            
            if mode == "1":
                # 模式1：直接终端输入 - 保持原有功能
                question = input("\n请输入你的算法问题：").strip()
                if not question:
                    print("❌ 请输入有效问题")
                    continue
                
                result = rag_engine.solve_problem(question, True)
                if result['success']:
                    print("\n" + "="*50)
                    print("📋 解答结果:")
                    print("="*50)
                    print(result['answer'])
                else:
                    print(f"❌ 解题失败: {result.get('error', '未知错误')}")
                
            elif mode == "2":
                # 模式2：从MD文档读取 - 保持原有功能
                result = rag_engine.process_file('input.md', 'output.md', True)
                if result['success']:
                    print("✅ 文件处理完成！结果已保存到 output.md")
                else:
                    print(f"❌ 文件处理失败: {result.get('error', '未知错误')}")
                
            elif mode == "3":
                # 启动Web界面
                start_web_interface()
                break
                
            elif mode == "4":
                print("\n👋 再见！")
                break
                
            else:
                print("❌ 无效选择，请输入1-4")
                
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误：{e}")
            continue

if __name__ == "__main__":
    main()
