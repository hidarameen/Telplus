// Main JavaScript functionality for the Telegram Bot Dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Auto-hide alerts
    autoHideAlerts();
    
    // Form validation
    setupFormValidation();
    
    // Chat input helpers
    setupChatInputHelpers();
    
    // Confirmation dialogs
    setupConfirmationDialogs();
    
    // Real-time task status
    setupTaskStatusUpdates();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Auto-hide alert messages after 5 seconds
 */
function autoHideAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        // Don't auto-hide error messages
        if (!alert.classList.contains('alert-danger')) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            } else {
                // Show loading state
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري المعالجة...';
                    submitBtn.disabled = true;
                    
                    // Re-enable after 3 seconds in case of errors
                    setTimeout(function() {
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                    }, 3000);
                }
            }
            
            form.classList.add('was-validated');
        });
        
        // Real-time validation for textarea inputs
        const textareas = form.querySelectorAll('textarea');
        textareas.forEach(function(textarea) {
            textarea.addEventListener('input', function() {
                validateChatInput(textarea);
            });
        });
    });
}

/**
 * Setup chat input helpers and validation
 */
function setupChatInputHelpers() {
    const chatInputs = document.querySelectorAll('textarea[name="source_chats"], textarea[name="target_chats"]');
    
    chatInputs.forEach(function(textarea) {
        // Add input event listener for real-time feedback
        textarea.addEventListener('input', function() {
            validateChatInput(textarea);
        });
        
        // Add paste event listener to clean up pasted content
        textarea.addEventListener('paste', function(e) {
            setTimeout(function() {
                cleanChatInput(textarea);
                validateChatInput(textarea);
            }, 10);
        });
    });
}

/**
 * Validate chat input format
 */
function validateChatInput(textarea) {
    const lines = textarea.value.split('\n').filter(line => line.trim());
    const validPatterns = [
        /^@[a-zA-Z][a-zA-Z0-9_]{4,31}$/, // Username
        /^[+]\d{10,15}$/, // Phone number
        /^-?\d+$/, // Chat ID
        /^https?:\/\/t\.me\/[a-zA-Z0-9_]+$/ // Telegram URL
    ];
    
    let invalidLines = [];
    
    lines.forEach(function(line, index) {
        const trimmedLine = line.trim();
        if (trimmedLine && !validPatterns.some(pattern => pattern.test(trimmedLine))) {
            invalidLines.push(index + 1);
        }
    });
    
    // Update validation feedback
    const feedbackElement = textarea.parentElement.querySelector('.invalid-feedback') || 
                           createFeedbackElement(textarea);
    
    if (invalidLines.length > 0) {
        textarea.classList.add('is-invalid');
        textarea.classList.remove('is-valid');
        feedbackElement.textContent = `أسطر غير صحيحة: ${invalidLines.join(', ')}`;
    } else if (lines.length > 0) {
        textarea.classList.remove('is-invalid');
        textarea.classList.add('is-valid');
        feedbackElement.textContent = `تم التحقق من ${lines.length} محادثة`;
    } else {
        textarea.classList.remove('is-invalid', 'is-valid');
        feedbackElement.textContent = '';
    }
}

/**
 * Clean chat input by removing duplicates and empty lines
 */
function cleanChatInput(textarea) {
    const lines = textarea.value.split('\n');
    const cleanedLines = [];
    const seen = new Set();
    
    lines.forEach(function(line) {
        const trimmed = line.trim();
        if (trimmed && !seen.has(trimmed.toLowerCase())) {
            seen.add(trimmed.toLowerCase());
            cleanedLines.push(trimmed);
        }
    });
    
    textarea.value = cleanedLines.join('\n');
}

/**
 * Create feedback element for validation
 */
function createFeedbackElement(textarea) {
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    textarea.parentElement.appendChild(feedback);
    return feedback;
}

/**
 * Setup confirmation dialogs for destructive actions
 */
function setupConfirmationDialogs() {
    const deleteLinks = document.querySelectorAll('a[onclick*="confirm"]');
    
    deleteLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const confirmDialog = confirm('هل أنت متأكد من هذا الإجراء؟ لا يمكن التراجع عنه.');
            if (confirmDialog) {
                window.location.href = link.href;
            }
        });
        
        // Remove the onclick attribute to prevent double confirmation
        link.removeAttribute('onclick');
    });
}

/**
 * Setup task status updates
 */
function setupTaskStatusUpdates() {
    // Check if we're on the dashboard page
    if (!document.querySelector('.table')) {
        return;
    }
    
    // Update task status every 30 seconds
    setInterval(function() {
        updateTaskStatuses();
    }, 30000);
}

/**
 * Update task statuses via AJAX
 */
function updateTaskStatuses() {
    fetch('/api/tasks')
        .then(response => response.json())
        .then(data => {
            data.forEach(function(task) {
                updateTaskRow(task);
            });
        })
        .catch(error => {
            console.error('Error updating task statuses:', error);
        });
}

/**
 * Update individual task row
 */
function updateTaskRow(task) {
    const row = document.querySelector(`tr[data-task-id="${task.id}"]`);
    if (!row) return;
    
    const statusBadge = row.querySelector('.badge');
    if (statusBadge) {
        if (task.is_active) {
            statusBadge.className = 'badge bg-success';
            statusBadge.innerHTML = '<i class="fas fa-play"></i> نشط';
        } else {
            statusBadge.className = 'badge bg-danger';
            statusBadge.innerHTML = '<i class="fas fa-pause"></i> معطل';
        }
    }
    
    // Update toggle button
    const toggleBtn = row.querySelector('a[href*="toggle_task"]');
    if (toggleBtn) {
        if (task.is_active) {
            toggleBtn.className = 'btn btn-sm btn-secondary';
            toggleBtn.title = 'تعطيل';
            toggleBtn.innerHTML = '<i class="fas fa-pause"></i>';
        } else {
            toggleBtn.className = 'btn btn-sm btn-success';
            toggleBtn.title = 'تفعيل';
            toggleBtn.innerHTML = '<i class="fas fa-play"></i>';
        }
    }
}

/**
 * Add chat suggestion functionality
 */
function addChatSuggestions(textarea) {
    const suggestions = [
        { text: '@channel_name', description: 'قناة عامة' },
        { text: '+966501234567', description: 'رقم هاتف' },
        { text: '-1001234567890', description: 'معرف مجموعة' }
    ];
    
    // Create suggestions dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'chat-suggestions';
    dropdown.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #ccc;
        border-radius: 4px;
        max-height: 200px;
        overflow-y: auto;
        z-index: 1000;
        display: none;
    `;
    
    textarea.parentElement.style.position = 'relative';
    textarea.parentElement.appendChild(dropdown);
    
    // Show suggestions on focus
    textarea.addEventListener('focus', function() {
        if (textarea.value.trim() === '') {
            showSuggestions(dropdown, suggestions, textarea);
        }
    });
    
    // Hide suggestions on blur
    textarea.addEventListener('blur', function() {
        setTimeout(() => dropdown.style.display = 'none', 200);
    });
}

/**
 * Show chat suggestions
 */
function showSuggestions(dropdown, suggestions, textarea) {
    dropdown.innerHTML = '';
    
    suggestions.forEach(function(suggestion) {
        const item = document.createElement('div');
        item.style.cssText = `
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
        `;
        item.innerHTML = `
            <strong>${suggestion.text}</strong>
            <small style="color: #666; display: block;">${suggestion.description}</small>
        `;
        
        item.addEventListener('click', function() {
            const currentValue = textarea.value;
            const newValue = currentValue ? currentValue + '\n' + suggestion.text : suggestion.text;
            textarea.value = newValue;
            dropdown.style.display = 'none';
            textarea.focus();
        });
        
        dropdown.appendChild(item);
    });
    
    dropdown.style.display = 'block';
}

/**
 * Copy to clipboard functionality
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('تم النسخ إلى الحافظة', 'success');
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
        showToast('فشل في النسخ', 'error');
    });
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} toast-notification`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        animation: slideIn 0.3s ease-out;
    `;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 3000);
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .toast-notification {
        animation: slideIn 0.3s ease-out;
    }
    
    .chat-suggestions {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .chat-suggestions div:hover {
        background-color: #f8f9fa;
    }
    
    .chat-suggestions div:last-child {
        border-bottom: none;
    }
`;
document.head.appendChild(style);
