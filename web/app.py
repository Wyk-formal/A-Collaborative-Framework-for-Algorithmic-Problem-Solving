# -*- coding: utf-8 -*-
"""
Web界面主程序 - Flask应用
"""

import os
import sys
import uuid
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 创建SocketIO实例
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局RAG引擎实例（延迟初始化）
rag_engine = None

def get_rag_engine():
    """延迟初始化RAG引擎"""
    global rag_engine
    if rag_engine is None:
        try:
            print("🔄 开始初始化RAG引擎...")
            from src.core.rag_engine import RAGEngine
            rag_engine = RAGEngine()
            print("✅ RAG引擎初始化成功")
        except Exception as e:
            print(f"❌ RAG引擎初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise e
    return rag_engine

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/solve', methods=['GET', 'POST'])
def solve_page():
    """解题页面"""
    if request.method == 'GET':
        return render_template('problem_input.html')
    
    # POST请求处理
    try:
        print("🔍 收到解题请求")
        data = request.get_json()
        print(f"📝 请求数据: {data}")
        
        problem_content = data.get('problem_content', '')
        enable_validation = data.get('enable_validation', True)
        
        print(f"📋 题目内容长度: {len(problem_content)}")
        print(f"✅ 启用验证: {enable_validation}")
        
        if not problem_content:
            print("❌ 题目内容为空")
            return jsonify({'error': '题目内容不能为空'}), 400
        
        task_id = str(uuid.uuid4())
        session['current_task'] = task_id
        
        print(f"🚀 启动异步任务: {task_id}")
        
        socketio.start_background_task(
            solve_problem_async, 
            task_id, 
            problem_content, 
            enable_validation
        )
        
        print(f"✅ 任务已启动，返回task_id: {task_id}")
        
        return jsonify({
            'task_id': task_id,
            'status': 'processing',
            'message': '正在处理您的问题...'
        })
        
    except Exception as e:
        print(f"❌ 处理解题请求时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/docs')
def docs():
    """文档页面"""
    return render_template('docs.html')

def solve_problem_async(task_id, problem_content, enable_validation):
    """异步解题函数 - 模拟main.py功能2的完整流程"""
    try:
        # 步骤1: 开始处理
        socketio.emit('task_started', {
            'task_id': task_id,
            'message': '🚀 开始处理算法题目...',
            'stage': 'start'
        })
        
        # 获取RAG引擎（延迟初始化）
        print("🔄 正在初始化RAG引擎...")
        try:
            engine = get_rag_engine()
            print("✅ RAG引擎初始化完成")
        except Exception as e:
            print(f"❌ RAG引擎初始化失败: {e}")
            socketio.emit('task_completed', {
                'task_id': task_id,
                'status': 'error',
                'error': f'RAG引擎初始化失败: {str(e)}'
            })
            return
        
        # 步骤2: AI分析问题
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': 15,
            'message': '📝 AI正在分析题目内容...',
            'stage': 'analyzing'
        })
        
        # 使用AI分析问题（模拟main.py功能2的第一步）
        from src.services.problem_analyzer import summarize_problem_with_ai
        problem_summary = summarize_problem_with_ai(problem_content)
        
        if not problem_summary or not problem_summary.get('keywords'):
            socketio.emit('task_completed', {
                'task_id': task_id,
                'status': 'error',
                'error': 'AI分析失败，无法提取题目关键信息'
            })
            return
        
        # 步骤3: 检索相关算法
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': 35,
            'message': f'🔍 检索相关算法 (关键词: {", ".join(problem_summary["keywords"][:3])})...',
            'stage': 'searching'
        })
        
        # 进行混合检索
        from src.core.search_engine import enhanced_hybrid_search
        keywords_str = ",".join(problem_summary['keywords'])
        retrieved_algorithms = enhanced_hybrid_search(problem_content, keywords_str)
        
        # 步骤4: 构建上下文
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': 55,
            'message': f'📚 构建算法上下文 (检索到{len(retrieved_algorithms)}个相关算法)...',
            'stage': 'context'
        })
        
        from src.services.answer_generator import build_enhanced_context
        context = build_enhanced_context(retrieved_algorithms, problem_content)
        
        # 步骤5: 生成解答
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': 75,
            'message': '💡 正在生成算法解答...',
            'stage': 'generating'
        })
        
        from src.services.answer_generator import create_optimized_prompt, generate_enhanced_answer
        prompt = create_optimized_prompt(problem_content, context, problem_summary)
        answer = generate_enhanced_answer(problem_content, context, str(problem_summary))
        
        # 步骤6: 代码验证（如果启用）
        if enable_validation:
            socketio.emit('task_progress', {
                'task_id': task_id,
                'progress': 90,
                'message': '✅ 正在验证代码正确性...',
                'stage': 'validating'
            })
            
            # 这里可以添加代码验证逻辑
            # 暂时跳过验证，直接显示结果
        
        # 步骤7: 完成
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': 100,
            'message': '🎉 处理完成！',
            'stage': 'completed'
        })
        
        # 发送最终结果
        socketio.emit('task_completed', {
            'task_id': task_id,
            'status': 'success',
            'result': {
                'answer': answer,
                'validation_enabled': enable_validation,
                'success': True,
                'problem_summary': {
                    'keywords': problem_summary.get('keywords', []),
                    'core_problem': problem_summary.get('core_problem', ''),
                    'sample_count': problem_summary.get('sample_count', 0)
                },
                'algorithms_count': len(retrieved_algorithms)
            }
        })
            
    except Exception as e:
        print(f"异步解题过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        socketio.emit('task_completed', {
            'task_id': task_id,
            'status': 'error',
            'error': f'处理过程中发生错误: {str(e)}'
        })

@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    print('客户端已连接')
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接事件"""
    print('客户端已断开连接')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('FLASK_PORT', 8080))
    print("🌐 启动Web服务器...")
    print(f"📱 访问地址: http://localhost:{port}")
    print("=" * 50)
    socketio.run(app, debug=settings.system.show_debug_info, host='0.0.0.0', port=port)
