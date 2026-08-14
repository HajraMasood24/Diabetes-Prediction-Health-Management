// ui/js/main.js

// API Configuration
const API_BASE_URL = 'http://127.0.0.1:5000/api';

// Auth Functions
function getAuthToken() {
    return localStorage.getItem('authToken');
}

function setAuthToken(token) {
    localStorage.setItem('authToken', token);
}

function getUsername() {
    return localStorage.getItem('username');
}

function setUsername(name) {
    localStorage.setItem('username', name);
}

function clearAuth() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
}

function isAuthenticated() {
    return !!getAuthToken();
}

// API Calls
async function apiLogin(username, password) {
    const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    return await response.json();
}

async function apiPredict(formData, token) {
    const response = await fetch(`${API_BASE_URL}/predict`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
    });
    return await response.json();
}

async function apiGetStatistics(token) {
    const response = await fetch(`${API_BASE_URL}/statistics`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return await response.json();
}

// UI Helpers
function showLoading(button, text = 'Processing...') {
    const originalText = button.innerText;
    button.innerText = text;
    button.disabled = true;
    return originalText;
}

function hideLoading(button, originalText) {
    button.innerText = originalText;
    button.disabled = false;
}

function showToast(message, type = 'success') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${type === 'success' ? '#2e7d32' : '#c62828'};
        color: white;
        padding: 12px 24px;
        border-radius: 12px;
        font-family: 'Poppins', sans-serif;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    toast.innerText = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Redirect helper
function redirectTo(page) {
    window.location.href = page;
}

// Export functions for use in pages
window.app = {
    getAuthToken,
    setAuthToken,
    getUsername,
    setUsername,
    clearAuth,
    isAuthenticated,
    apiLogin,
    apiPredict,
    apiGetStatistics,
    showLoading,
    hideLoading,
    showToast,
    redirectTo,
    API_BASE_URL
};