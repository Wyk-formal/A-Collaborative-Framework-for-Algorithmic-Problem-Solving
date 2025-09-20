// 题目输入页面专用JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初始化代码编辑器
    initializeCodeEditor();
    
    // 初始化示例加载
    initializeExamples();
    
    // 初始化表单验证
    initializeFormValidation();
});

// 初始化代码编辑器
function initializeCodeEditor() {
    const textarea = document.getElementById('problemContent');
    if (!textarea) return;
    
    // 添加自动调整高度功能
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
    
    // 添加Tab键支持
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = this.selectionStart;
            const end = this.selectionEnd;
            
            // 插入Tab字符
            this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
            
            // 设置光标位置
            this.selectionStart = this.selectionEnd = start + 4;
        }
    });
}

// 初始化示例加载
function initializeExamples() {
    const exampleBtns = document.querySelectorAll('.example-btn');
    
    exampleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const exampleType = this.dataset.example;
            loadExampleContent(exampleType);
        });
    });
}

// 加载示例内容
function loadExampleContent(exampleType) {
    const textarea = document.getElementById('problemContent');
    if (!textarea) return;
    
    // 显示加载状态
    const originalText = this.textContent;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 加载中...';
    this.disabled = true;
    
    fetch('/api/examples')
        .then(response => response.json())
        .then(examples => {
            if (examples[exampleType]) {
                textarea.value = examples[exampleType].content;
                // 触发高度调整
                textarea.dispatchEvent(new Event('input'));
                
                // 显示成功提示
                showToast('示例已加载', 'success');
            } else {
                showToast('示例不存在', 'error');
            }
        })
        .catch(error => {
            console.error('加载示例失败:', error);
            showToast('加载示例失败', 'error');
        })
        .finally(() => {
            // 恢复按钮状态
            this.textContent = originalText;
            this.disabled = false;
        });
}

// 初始化表单验证
function initializeFormValidation() {
    const form = document.getElementById('problemForm');
    const textarea = document.getElementById('problemContent');
    
    if (!form || !textarea) return;
    
    // 实时字符计数
    textarea.addEventListener('input', function() {
        const charCount = this.value.length;
        updateCharCount(charCount);
        
        // 验证内容长度
        if (charCount < 10) {
            showFieldError('题目内容至少需要10个字符');
        } else if (charCount > 10000) {
            showFieldError('题目内容不能超过10000个字符');
        } else {
            clearFieldError();
        }
    });
    
    // 表单提交验证
    form.addEventListener('submit', function(e) {
        const content = textarea.value.trim();
        
        if (!content) {
            e.preventDefault();
            showToast('请输入题目内容', 'error');
            textarea.focus();
            return;
        }
        
        if (content.length < 10) {
            e.preventDefault();
            showToast('题目内容至少需要10个字符', 'error');
            textarea.focus();
            return;
        }
        
        if (content.length > 10000) {
            e.preventDefault();
            showToast('题目内容不能超过10000个字符', 'error');
            textarea.focus();
            return;
        }
    });
}

// 更新字符计数
function updateCharCount(count) {
    let counter = document.getElementById('charCounter');
    if (!counter) {
        counter = document.createElement('div');
        counter.id = 'charCounter';
        counter.className = 'form-text text-muted';
        document.getElementById('problemContent').parentNode.appendChild(counter);
    }
    
    counter.textContent = `${count} 字符`;
    
    if (count > 10000) {
        counter.className = 'form-text text-danger';
    } else if (count > 8000) {
        counter.className = 'form-text text-warning';
    } else {
        counter.className = 'form-text text-muted';
    }
}

// 显示字段错误
function showFieldError(message) {
    let errorDiv = document.getElementById('fieldError');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'fieldError';
        errorDiv.className = 'invalid-feedback';
        document.getElementById('problemContent').parentNode.appendChild(errorDiv);
    }
    
    errorDiv.textContent = message;
    document.getElementById('problemContent').classList.add('is-invalid');
}

// 清除字段错误
function clearFieldError() {
    const errorDiv = document.getElementById('fieldError');
    if (errorDiv) {
        errorDiv.remove();
    }
    document.getElementById('problemContent').classList.remove('is-invalid');
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 创建提示元素
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // 添加到页面
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    // 显示提示
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    bsToast.show();
    
    // 自动移除
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    // Ctrl+Enter 提交表单
    if (e.ctrlKey && e.key === 'Enter') {
        const form = document.getElementById('problemForm');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    }
    
    // Ctrl+L 清空内容
    if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        const clearBtn = document.getElementById('clearBtn');
        if (clearBtn) {
            clearBtn.click();
        }
    }
});

// 自动保存功能
let autoSaveTimer = null;

function startAutoSave() {
    const textarea = document.getElementById('problemContent');
    if (!textarea) return;
    
    textarea.addEventListener('input', function() {
        // 清除之前的定时器
        if (autoSaveTimer) {
            clearTimeout(autoSaveTimer);
        }
        
        // 设置新的定时器
        autoSaveTimer = setTimeout(() => {
            saveToLocalStorage();
        }, 2000); // 2秒后自动保存
    });
}

function saveToLocalStorage() {
    const content = document.getElementById('problemContent').value;
    if (content.trim()) {
        localStorage.setItem('rag_problem_draft', content);
        console.log('内容已自动保存');
    }
}

function loadFromLocalStorage() {
    const saved = localStorage.getItem('rag_problem_draft');
    if (saved) {
        const textarea = document.getElementById('problemContent');
        if (textarea && !textarea.value.trim()) {
            textarea.value = saved;
            textarea.dispatchEvent(new Event('input'));
        }
    }
}

// 页面加载时恢复保存的内容
document.addEventListener('DOMContentLoaded', function() {
    loadFromLocalStorage();
    startAutoSave();
});

// 页面卸载时保存内容
window.addEventListener('beforeunload', function() {
    saveToLocalStorage();
});

// 导出函数
window.ProblemInput = {
    showToast,
    loadExampleContent,
    saveToLocalStorage,
    loadFromLocalStorage
};

