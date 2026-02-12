/**
 * Custom JavaScript for FEM Admin System
 */

// Global variables
let loadingOverlay = null;

// Document ready
$(document).ready(function() {
    // Initialize loading overlay
    initLoadingOverlay();
    
    // Setup AJAX defaults with Authorization header
    setupAjaxDefaults();
    
    // Setup AJAX error handler
    setupAjaxErrorHandler();
    
    // Setup automatic token refresh
    setupTokenRefresh();
    
    // Store token in localStorage if exists in session
    const apiToken = $('meta[name="api-token"]').attr('content');
    const refreshToken = $('meta[name="refresh-token"]').attr('content');
    
    if (apiToken) {
        localStorage.setItem('token', apiToken);
        console.log('API Token stored in localStorage');
    } else {
        console.warn('No API token found in meta tag');
    }
    
    if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
        console.log('Refresh Token stored in localStorage');
    } else {
        console.warn('No Refresh token found in meta tag');
    }
    
    // Log current token for debugging
    const currentToken = localStorage.getItem('token');
    if (currentToken) {
        console.log('Current token available:', currentToken.substring(0, 20) + '...');
    } else {
        console.warn('No token in localStorage - API calls may fail');
    }
    
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-toggle="popover"]').popover();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
});

/**
 * Setup AJAX defaults to include Authorization header
 */
function setupAjaxDefaults() {
    $.ajaxSetup({
        beforeSend: function(xhr) {
            const token = localStorage.getItem('token');
            if (token) {
                xhr.setRequestHeader('Authorization', 'Bearer ' + token);
            }
        }
    });
}

/**
 * Setup automatic token refresh
 * Refreshes token 5 minutes before expiry
 */
function setupTokenRefresh() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
        console.warn('No refresh token found - automatic refresh disabled');
        return;
    }
    // 讀取登入時儲存的 token lifespan (秒)
    let expiresIn = parseInt(localStorage.getItem('access_token_expires_in'), 10);
    if (isNaN(expiresIn) || expiresIn <= 0) {
        // 預設使用 8 小時 (28800 秒) 開發環境，或 3600 秒作為安全回退
        expiresIn = 28800; // fallback
    }

    // 提前百分比 (例如 95%) 刷新
    const refreshRatio = 0.95;
    const refreshDelayMs = Math.floor(expiresIn * refreshRatio * 1000);

    console.log('[TokenRefresh] lifespan(s)=', expiresIn, 'scheduled refresh in', Math.round(refreshDelayMs/1000), '秒');

    // 使用 setTimeout 而不是 setInterval 以便下一次刷新可根據新的 expires_in 動態調整
    setTimeout(function scheduleRefresh() {
        refreshAccessToken(function onRefreshed(newExpiresIn) {
            // 若回傳新的 expires_in，重新排程
            if (newExpiresIn && !isNaN(newExpiresIn)) {
                localStorage.setItem('access_token_expires_in', newExpiresIn);
            }
            setupTokenRefresh(); // 重新排程下一次
        });
    }, refreshDelayMs);
}

/**
 * Refresh access token using refresh token
 */
function refreshAccessToken(callback) {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        console.error('No refresh token available');
        return;
    }
    
    console.log('Attempting to refresh access token...');
    
    $.ajax({
        url: '/api/v1/auth/refresh',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            refresh_token: refreshToken
        }),
        success: function(response) {
            if (response.status === 'success' && response.data.token) {
                localStorage.setItem('token', response.data.token);
                const newExpires = response.data.expires_in;
                if (newExpires) {
                    localStorage.setItem('access_token_expires_in', newExpires);
                }
                console.log('Access token refreshed successfully at', new Date().toLocaleTimeString(), 'expires_in=', newExpires);
                toastr.success('登入憑證已自動更新', '', { 
                    timeOut: 2000,
                    preventDuplicates: true
                });
                if (typeof callback === 'function') {
                    callback(newExpires);
                }
            } else {
                if (typeof callback === 'function') {
                    callback();
                }
            }
        },
        error: function(jqxhr) {
            console.error('Failed to refresh token:', jqxhr.status, jqxhr.responseText);
            
            // 只有在 401 錯誤時才清除 token 並重新導向
            if (jqxhr.status === 401) {
                console.log('Refresh token expired or invalid, redirecting to login...');
                toastr.error('登入已過期，請重新登入');
                localStorage.removeItem('token');
                localStorage.removeItem('refresh_token');
                setTimeout(function() {
                    window.location.href = '/login';
                }, 2000);
            } else {
                // 其他錯誤（如網路問題）只記錄，不導向登入頁
                console.warn('Token refresh failed, will retry on next interval');
                if (typeof callback === 'function') {
                    callback();
                }
            }
        }
    });
}

/**
 * Initialize loading overlay
 */
function initLoadingOverlay() {
    loadingOverlay = $('<div class="loading-overlay" style="display:none;">')
        .append('<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i></div>');
    $('body').append(loadingOverlay);
}

/**
 * Show loading overlay
 */
function showLoading() {
    if (loadingOverlay) {
        loadingOverlay.fadeIn();
    }
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    if (loadingOverlay) {
        loadingOverlay.fadeOut();
    }
}

/**
 * Setup AJAX error handler
 */
function setupAjaxErrorHandler() {
    let isRefreshing = false; // 防止同時多次刷新
    
    $(document).ajaxError(function(event, jqxhr, settings, thrownError) {
        hideLoading();
        
        console.error('AJAX Error:', {
            status: jqxhr.status,
            url: settings.url,
            error: thrownError,
            response: jqxhr.responseText
        });
        
        if (jqxhr.status === 401) {
            // 如果是 refresh API 本身失敗，直接導向登入頁
            if (settings.url.includes('/auth/refresh')) {
                toastr.error('登入已過期，請重新登入');
                localStorage.removeItem('token');
                localStorage.removeItem('refresh_token');
                setTimeout(function() {
                    window.location.href = '/login';
                }, 2000);
                return;
            }
            
            // 如果已經在刷新中，不要重複刷新
            if (isRefreshing) {
                console.log('Token refresh already in progress, skipping...');
                return;
            }
            
            // 嘗試自動刷新 token
            const refreshToken = localStorage.getItem('refresh_token');
            
            if (refreshToken) {
                isRefreshing = true;
                console.log('Token expired, attempting automatic refresh...');
                
                $.ajax({
                    url: '/api/v1/auth/refresh',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        refresh_token: refreshToken
                    }),
                    success: function(response) {
                        if (response.status === 'success' && response.data.token) {
                            localStorage.setItem('token', response.data.token);
                            console.log('Token refreshed successfully');
                            // toastr.info('登入憑證已更新，請重新載入頁面', '', { 
                            //     timeOut: 3000,
                            //     closeButton: true
                            // });
                            isRefreshing = false;
                            
                            // 不要自動重新載入頁面，讓使用者手動重試
                        }
                    },
                    error: function() {
                        isRefreshing = false;
                        toastr.error('登入已過期，請重新登入');
                        localStorage.removeItem('token');
                        localStorage.removeItem('refresh_token');
                        setTimeout(function() {
                            window.location.href = '/login';
                        }, 2000);
                    }
                });
            } else {
                toastr.error('登入已過期或未授權，請重新登入');
                localStorage.removeItem('token');
                localStorage.removeItem('refresh_token');
                setTimeout(function() {
                    window.location.href = '/login';
                }, 2000);
            }
        } else if (jqxhr.status === 403) {
            toastr.error('權限不足');
        } else if (jqxhr.status === 404) {
            toastr.error('找不到資源');
        } else if (jqxhr.status === 500) {
            toastr.error('伺服器錯誤');
        } else if (jqxhr.status === 0) {
            toastr.error('網路連線失敗');
        }
    });
    
    $(document).ajaxStart(function() {
        showLoading();
    });
    
    $(document).ajaxStop(function() {
        hideLoading();
    });
}

/**
 * Format date to Chinese locale
 * @param {string|Date} date - Date string or Date object
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    if (!date) return '-';
    const d = new Date(date);
    return d.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

/**
 * Format datetime to Chinese locale
 * @param {string|Date} datetime - Datetime string or Date object
 * @returns {string} Formatted datetime string
 */
function formatDateTime(datetime) {
    if (!datetime) return '-';
    const d = new Date(datetime);
    return d.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Get status badge HTML
 * @param {string} status - Status text
 * @returns {string} Badge HTML
 */
function getStatusBadge(status) {
    const badges = {
        '未派工': 'badge-secondary',
        '執行中': 'badge-info',
        '已完成': 'badge-success',
        '未結案': 'badge-danger',
        '已結案': 'badge-success'
    };
    const badgeClass = badges[status] || 'badge-secondary';
    return `<span class="badge ${badgeClass}">${status}</span>`;
}

/**
 * Confirm dialog
 * @param {string} message - Confirmation message
 * @param {function} callback - Callback function if confirmed
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Show success message
 * @param {string} message - Message to display
 */
function showSuccess(message) {
    toastr.success(message);
}

/**
 * Show error message
 * @param {string} message - Message to display
 */
function showError(message) {
    toastr.error(message);
}

/**
 * Show info message
 * @param {string} message - Message to display
 */
function showInfo(message) {
    toastr.info(message);
}

/**
 * Show warning message
 * @param {string} message - Message to display
 */
function showWarning(message) {
    toastr.warning(message);
}

/**
 * API request helper
 * @param {string} url - API endpoint
 * @param {string} method - HTTP method
 * @param {object} data - Request data
 * @param {function} successCallback - Success callback
 * @param {function} errorCallback - Error callback
 */
function apiRequest(url, method, data, successCallback, errorCallback) {
    const token = localStorage.getItem('token');
    
    $.ajax({
        url: url,
        method: method,
        data: method === 'GET' ? data : JSON.stringify(data),
        contentType: method === 'GET' ? undefined : 'application/json',
        headers: {
            'Authorization': 'Bearer ' + token
        },
        success: function(response) {
            if (successCallback) {
                successCallback(response);
            }
        },
        error: function(xhr, status, error) {
            if (errorCallback) {
                errorCallback(xhr, status, error);
            }
        }
    });
}

/**
 * Export table to CSV
 * @param {string} tableId - Table element ID
 * @param {string} filename - Export filename
 */
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) {
        showError('找不到表格');
        return;
    }
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const row = [];
        const cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            // Remove HTML tags and get text content
            let text = cols[j].innerText;
            // Escape quotes
            text = text.replace(/"/g, '""');
            row.push('"' + text + '"');
        }
        
        csv.push(row.join(','));
    }
    
    // Download CSV file
    const csvFile = new Blob(['\ufeff' + csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const downloadLink = document.createElement('a');
    downloadLink.download = filename + '.csv';
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    
    showSuccess('匯出成功');
}

/**
 * Refresh current page data
 */
function refreshPage() {
    location.reload();
}

/**
 * Go back to previous page
 */
function goBack() {
    window.history.back();
}

/**
 * Print current page
 */
function printPage() {
    window.print();
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
function copyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    
    try {
        document.execCommand('copy');
        showSuccess('已複製到剪貼簿');
    } catch (err) {
        showError('複製失敗');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Initialize DataTable with Chinese language
 * @param {string} tableId - Table element ID
 * @param {object} options - DataTable options
 * @returns {object} DataTable instance
 */
function initDataTable(tableId, options) {
    const defaultOptions = {
        language: {
            url: '/static/datatable_zh-Hant.json'
        },
        responsive: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "全部"]]
    };
    
    const mergedOptions = $.extend({}, defaultOptions, options);
    return $('#' + tableId).DataTable(mergedOptions);
}

/**
 * Update notification count
 * @param {number} count - Notification count
 */
function updateNotificationCount(count) {
    $('#notification-count').text(count);
    if (count > 0) {
        $('#notification-count').removeClass('badge-secondary').addClass('badge-warning');
    } else {
        $('#notification-count').removeClass('badge-warning').addClass('badge-secondary');
    }
}

// Export functions to global scope
window.FEM = {
    showLoading,
    hideLoading,
    formatDate,
    formatDateTime,
    getStatusBadge,
    confirmAction,
    showSuccess,
    showError,
    showInfo,
    showWarning,
    apiRequest,
    exportTableToCSV,
    refreshPage,
    goBack,
    printPage,
    copyToClipboard,
    initDataTable,
    updateNotificationCount
};
