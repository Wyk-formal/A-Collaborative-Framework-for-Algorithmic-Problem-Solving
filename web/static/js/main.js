// 算法竞赛RAG助手 - 主要JavaScript功能

// 全局变量
let socket = null;
let currentTaskId = null;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeEventListeners();
});

// 初始化WebSocket连接
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket连接已建立');
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket连接已断开');
    });
    
    socket.on('task_started', function(data) {
        handleTaskStarted(data);
    });
    
    socket.on('task_progress', function(data) {
        handleTaskProgress(data);
    });
    
    socket.on('task_completed', function(data) {
        handleTaskComplete(data);
    });
    
    socket.on('task_error', function(data) {
        handleTaskError(data);
    });
}

// 初始化事件监听器
function initializeEventListeners() {
    // 表单提交
    const form = document.getElementById('problemForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // 清空按钮
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearForm);
    }
    
    // 重试按钮
    const retryBtn = document.getElementById('retryBtn');
    if (retryBtn) {
        retryBtn.addEventListener('click', retryTask);
    }
    
    // 示例按钮
    const exampleBtns = document.querySelectorAll('.example-btn');
    exampleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            loadExample(this.dataset.example);
        });
    });
}

// 处理表单提交
function handleFormSubmit(event) {
    console.log('🔍 表单提交事件触发');
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const problemContent = document.getElementById('problemContent').value.trim();
    const enableValidation = document.getElementById('enableValidation').checked;
    
    console.log('📝 表单数据:', {
        contentLength: problemContent.length,
        enableValidation: enableValidation
    });
    
    if (!problemContent) {
        console.log('❌ 题目内容为空');
        showError('请输入题目内容');
        return;
    }
    
    console.log('✅ 开始显示处理状态');
    // 显示处理状态
    showProcessingStatus();
    
    console.log('🚀 发送请求到 /solve');
    // 发送请求
    fetch('/solve', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            problem_content: problemContent,
            enable_validation: enableValidation
        })
    })
    .then(response => {
        console.log('📡 收到响应:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('📋 响应数据:', data);
        if (data.error) {
            console.log('❌ 服务器返回错误:', data.error);
            showError(data.error);
        } else {
            currentTaskId = data.task_id;
            console.log('✅ 任务已提交:', data.task_id);
        }
    })
    .catch(error => {
        console.error('❌ 请求失败:', error);
        showError('网络请求失败，请重试');
    });
}

// 显示处理状态
function showProcessingStatus() {
    hideAllCards();
    document.getElementById('statusCard').style.display = 'block';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('statusMessage').textContent = '准备中...';
    
    // 重置状态指示器
    const indicators = document.querySelectorAll('.stage-indicator');
    indicators.forEach(indicator => {
        indicator.classList.remove('active', 'completed');
    });
}

// 处理任务开始
function handleTaskStarted(data) {
    if (data.task_id !== currentTaskId) return;
    
    console.log('任务开始:', data.message);
    showProcessingStatus();
    
    const statusMessage = document.getElementById('statusMessage');
    if (statusMessage) {
        statusMessage.textContent = data.message;
    }
    
    // 更新阶段指示器
    updateStageIndicator(data.stage);
}

// 处理任务进度
function handleTaskProgress(data) {
    if (data.task_id !== currentTaskId) return;
    
    const progressBar = document.getElementById('progressBar');
    const statusMessage = document.getElementById('statusMessage');
    
    if (progressBar) {
        progressBar.style.width = data.progress + '%';
    }
    
    if (statusMessage) {
        statusMessage.textContent = data.message;
    }
    
    // 更新状态指示器
    if (data.stage) {
        updateStageIndicator(data.stage);
    }
}

// 更新阶段指示器
function updateStageIndicator(stage) {
    const indicators = document.querySelectorAll('.stage-indicator');
    
    indicators.forEach(indicator => {
        const indicatorStage = indicator.dataset.stage;
        indicator.classList.remove('active', 'completed');
        
        if (indicatorStage === stage) {
            indicator.classList.add('active');
        } else if (isStageCompleted(indicatorStage, stage)) {
            indicator.classList.add('completed');
        }
    });
}

// 判断阶段是否已完成
function isStageCompleted(indicatorStage, currentStage) {
    const stageOrder = ['analyzing', 'searching', 'generating', 'validating'];
    const currentIndex = stageOrder.indexOf(currentStage);
    const indicatorIndex = stageOrder.indexOf(indicatorStage);
    
    return indicatorIndex >= 0 && indicatorIndex < currentIndex;
}


// 处理任务完成
function handleTaskComplete(data) {
    if (data.task_id !== currentTaskId) return;
    
    hideAllCards();
    document.getElementById('resultCard').style.display = 'block';
    
    const resultContent = document.getElementById('resultContent');
    if (resultContent) {
        displayResult(data.result);
    }
}

// 处理任务错误
function handleTaskError(data) {
    if (data.task_id !== currentTaskId) return;
    
    hideAllCards();
    document.getElementById('errorCard').style.display = 'block';
    
    const errorContent = document.getElementById('errorContent');
    if (errorContent) {
        errorContent.textContent = data.error;
    }
}

// 显示结果
function displayResult(result) {
    const resultContent = document.getElementById('resultContent');
    
    let html = '';
    
    // 如果是简单的答案字符串
    if (typeof result === 'string') {
        html = `<div class="result-answer">${formatAnswerSimple(result)}</div>`;
    } else if (result.answer) {
        // 如果是包含answer字段的对象
        html = `<div class="result-answer">${formatAnswerSimple(result.answer)}</div>`;
        
        // 显示验证信息
        if (result.validation_enabled) {
            html += `<div class="alert alert-success mt-3">
                <i class="fas fa-check-circle"></i>
                代码已通过自动验证
            </div>`;
        }
    } else {
        // 显示基本信息
        if (result.algorithms_count) {
            html += `<div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                检索到 ${result.algorithms_count} 个相关算法
            </div>`;
        }
    
    // 显示题目分析信息
    if (result.problem_summary) {
        const summary = result.problem_summary;
        if (summary.keywords && summary.keywords.length > 0) {
            html += `<div class="result-section">
                <h4><i class="fas fa-tags"></i> 关键词分析</h4>
                <div class="mb-3">
                    ${summary.keywords.map(kw => `<span class="badge bg-primary me-1">${kw}</span>`).join('')}
                </div>
            </div>`;
        }
        
        if (summary.samples && summary.samples.length > 0) {
            html += `<div class="result-section">
                <h4><i class="fas fa-list"></i> 样例数据</h4>
                <p class="text-muted">共 ${summary.samples.length} 组样例</p>
            </div>`;
        }
    }
    
    // 显示答案
    if (result.answer) {
        html += `<div class="result-section">
            <h4><i class="fas fa-lightbulb"></i> 解答</h4>
            <div class="answer-content">${formatAnswer(result.answer)}</div>
        </div>`;
    }
    
    // 显示验证结果
    if (result.validation_result) {
        html += `<div class="result-section">
            <h4><i class="fas fa-check-circle"></i> 验证结果</h4>
            ${formatValidationResult(result.validation_result)}
        </div>`;
    }
    
    resultContent.innerHTML = html;
    
    // 高亮代码
    if (typeof Prism !== 'undefined') {
        Prism.highlightAll();
    }
}

// 格式化答案
function formatAnswer(answer) {
    // 将Markdown格式转换为HTML
    let html = answer
        .replace(/```cpp\n([\s\S]*?)\n```/g, '<pre><code class="language-cpp">$1</code></pre>')
        .replace(/```c\+\+\n([\s\S]*?)\n```/g, '<pre><code class="language-cpp">$1</code></pre>')
        .replace(/```\n([\s\S]*?)\n```/g, '<pre><code>$1</code></pre>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^(.*)$/gm, '<p>$1</p>');
    
    return html;
}

// 格式化验证结果
function formatValidationResult(validationResult) {
    if (!validationResult) return '<p class="text-muted">未进行验证</p>';
    
    let html = '';
    
    if (validationResult.success) {
        html += `<div class="validation-result success">
            <i class="fas fa-check-circle"></i>
            验证成功！所有样例都通过了测试。
        </div>`;
    } else {
        html += `<div class="validation-result error">
            <i class="fas fa-exclamation-triangle"></i>
            验证失败，部分样例未通过测试。
        </div>`;
    }
    
    if (validationResult.results) {
        html += '<div class="mt-3"><h5>详细结果：</h5>';
        validationResult.results.forEach((result, index) => {
            const status = result.success ? 'success' : 'error';
            const icon = result.success ? 'check-circle' : 'times-circle';
            html += `<div class="validation-result ${status}">
                <i class="fas fa-${icon}"></i>
                样例 ${index + 1}: ${result.success ? '通过' : '失败'}
            </div>`;
        });
        html += '</div>';
    }
    
    return html;
}

// 显示错误
function showError(message) {
    hideAllCards();
    document.getElementById('errorCard').style.display = 'block';
    document.getElementById('errorContent').textContent = message;
}

// 隐藏所有卡片
function hideAllCards() {
    const cards = ['statusCard', 'resultCard', 'errorCard'];
    cards.forEach(cardId => {
        const card = document.getElementById(cardId);
        if (card) {
            card.style.display = 'none';
        }
    });
}

// 清空表单
function clearForm() {
    document.getElementById('problemContent').value = '';
    hideAllCards();
}

// 重试任务
function retryTask() {
    const form = document.getElementById('problemForm');
    if (form) {
        form.dispatchEvent(new Event('submit'));
    }
}

// 加载示例
function loadExample(exampleType) {
    fetch('/api/examples')
        .then(response => response.json())
        .then(examples => {
            if (examples[exampleType]) {
                document.getElementById('problemContent').value = examples[exampleType].content;
            }
        })
        .catch(error => {
            console.error('加载示例失败:', error);
        });
}

// 工具函数
function showLoading(element) {
    element.innerHTML = '<div class="loading"></div>';
}

function hideLoading(element, content) {
    element.innerHTML = content;
}

// 格式化答案显示（简化版本）
function formatAnswerSimple(answer) {
    if (!answer) return '<p class="text-muted">暂无答案</p>';
    
    // 将换行符转换为HTML
    let formatted = answer.replace(/\n/g, '<br>');
    
    // 检测代码块并添加语法高亮
    formatted = formatted.replace(/```cpp\s*\n([\s\S]*?)\n```/g, '<pre><code class="language-cpp">$1</code></pre>');
    formatted = formatted.replace(/```c\+\+\s*\n([\s\S]*?)\n```/g, '<pre><code class="language-cpp">$1</code></pre>');
    formatted = formatted.replace(/```\s*\n([\s\S]*?)\n```/g, '<pre><code>$1</code></pre>');
    
    // 检测标题并添加样式
    formatted = formatted.replace(/^# (.*$)/gm, '<h1>$1</h1>');
    formatted = formatted.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    
    // 检测粗体和斜体
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    return formatted;
}

// 导出函数供其他脚本使用
window.RAGApp = {
    showError,
    showLoading,
    hideLoading,
    loadExample,
    formatAnswerSimple
};
