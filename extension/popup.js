// DOM Elements
const userInput = document.getElementById('userInput');
const keyword = document.getElementById('keyword');
const limit = document.getElementById('limit');
const analyzeBtn = document.getElementById('analyzeBtn');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const errorText = document.getElementById('errorText');
const errorClose = document.getElementById('errorClose');
const results = document.getElementById('results');
const resultPrompt = document.getElementById('resultPrompt');
const resultAnalysis = document.getElementById('resultAnalysis');
const resultDatasets = document.getElementById('resultDatasets');
const resultMeta = document.getElementById('resultMeta');
const copyResults = document.getElementById('copyResults');
const viewHistory = document.getElementById('viewHistory');
const clearResults = document.getElementById('clearResults');
const history = document.getElementById('history');
const historyList = document.getElementById('historyList');
const closeHistory = document.getElementById('closeHistory');
const clearHistory = document.getElementById('clearHistory');
const userId = document.getElementById('userId');
const apiUrl = document.getElementById('apiUrl');

// State
let currentAnalysis = null;
let analysisHistory = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    loadHistory();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    analyzeBtn.addEventListener('click', handleAnalyze);
    errorClose.addEventListener('click', hideError);
    clearResults.addEventListener('click', hideResults);
    viewHistory.addEventListener('click', showHistory);
    closeHistory.addEventListener('click', hideHistory);
    clearHistory.addEventListener('click', handleClearHistory);
    copyResults.addEventListener('click', copyToClipboard);
    
    userId.addEventListener('change', saveSettings);
    apiUrl.addEventListener('change', saveSettings);
    
    // Allow Enter key to submit
    userInput.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            handleAnalyze();
        }
    });
}

// Main Analyze Handler
async function handleAnalyze() {
    // Validation
    if (!userInput.value.trim()) {
        showError('Please enter a question');
        return;
    }
    
    if (!userId.value.trim()) {
        showError('Please enter a User ID');
        return;
    }
    
    if (!apiUrl.value.trim()) {
        showError('Please enter API URL');
        return;
    }
    
    // Prepare request
    const prompt = userInput.value.trim();
    const keywordValue = keyword.value.trim() || prompt;
    const limitValue = parseInt(limit.value) || 3;
    const userIdValue = userId.value.trim();
    const apiUrlValue = apiUrl.value.trim().replace(/\/$/, '');
    
    // Show loading
    showLoading();
    hideResults();
    hideError();
    
    try {
        // Call API
        const response = await fetch(`${apiUrlValue}/api/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userIdValue,
                prompt: prompt,
                keyword: keywordValue,
                limit: limitValue
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Analysis failed');
        }
        
        // Store current analysis
        currentAnalysis = data;
        
        // Add to history
        analysisHistory.unshift({
            id: data.id,
            prompt: data.prompt,
            analysis: data.analysis,
            keyword: data.keyword,
            datasets_used: data.datasets_used,
            created_at: new Date().toISOString()
        });
        
        // Save history
        saveHistory();
        
        // Display results
        displayResults(data);
        
    } catch (err) {
        console.error('Error:', err);
        showError(err.message);
    } finally {
        hideLoading();
    }
}

// Display Results
function displayResults(data) {
    resultPrompt.textContent = data.prompt;
    resultAnalysis.textContent = data.analysis;
    
    // Display datasets
    resultDatasets.innerHTML = '';
    if (data.datasets_used && data.datasets_used.length > 0) {
        data.datasets_used.forEach(ds => {
            const item = document.createElement('div');
            item.className = 'dataset-item';
            item.innerHTML = `
                <div class="name">${ds.title || 'Untitled Dataset'}</div>
                <div class="org">${ds.organization || 'Unknown Organization'}</div>
            `;
            resultDatasets.appendChild(item);
        });
    } else {
        resultDatasets.innerHTML = '<p style="font-size: 12px; color: #6B7280;">No datasets found</p>';
    }
    
    // Metadata
    const date = new Date(data.created_at || new Date()).toLocaleString();
    const recordId = data.id ? data.id.substring(0, 8) : 'N/A';
    resultMeta.textContent = `Analysis ID: ${recordId} | Saved: ${date} | Datasets: ${data.datasets_used?.length || 0}`;
    
    showResults();
}

// Show/Hide Functions
function showLoading() {
    loading.classList.remove('hidden');
    analyzeBtn.disabled = true;
}

function hideLoading() {
    loading.classList.add('hidden');
    analyzeBtn.disabled = false;
}

function showError(message) {
    errorText.textContent = message;
    error.classList.remove('hidden');
}

function hideError() {
    error.classList.add('hidden');
}

function showResults() {
    results.classList.remove('hidden');
}

function hideResults() {
    results.classList.add('hidden');
    currentAnalysis = null;
}

function showHistory() {
    if (analysisHistory.length === 0) {
        showError('No analysis history yet');
        return;
    }
    displayHistory();
    history.classList.remove('hidden');
    results.classList.add('hidden');
}

function hideHistory() {
    history.classList.add('hidden');
}

// Display History
function displayHistory() {
    historyList.innerHTML = '';
    
    analysisHistory.forEach((item, index) => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        
        const date = new Date(item.created_at).toLocaleString();
        const preview = item.prompt.substring(0, 50) + (item.prompt.length > 50 ? '...' : '');
        
        historyItem.innerHTML = `
            <div class="prompt">${preview}</div>
            <div class="time">${date}</div>
        `;
        
        historyItem.addEventListener('click', () => {
            currentAnalysis = item;
            displayResults(item);
            hideHistory();
        });
        
        historyList.appendChild(historyItem);
    });
}

// Clear History
function handleClearHistory() {
    if (confirm('Are you sure you want to clear all history? This cannot be undone.')) {
        analysisHistory = [];
        saveHistory();
        hideHistory();
        showError('History cleared');
    }
}

// Copy to Clipboard
function copyToClipboard() {
    if (!currentAnalysis) return;
    
    const text = `Question: ${currentAnalysis.prompt}\n\nAnalysis:\n${currentAnalysis.analysis}`;
    
    navigator.clipboard.writeText(text).then(() => {
        const btn = copyResults;
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        showError('Failed to copy to clipboard');
    });
}

// Storage Functions
function saveSettings() {
    const settings = {
        userId: userId.value,
        apiUrl: apiUrl.value
    };
    chrome.storage.sync.set({ settings }, () => {
        console.log('Settings saved');
    });
}

function loadSettings() {
    chrome.storage.sync.get(['settings'], (result) => {
        if (result.settings) {
            userId.value = result.settings.userId || '';
            apiUrl.value = result.settings.apiUrl || 'http://localhost:5000';
        } else {
            apiUrl.value = 'http://localhost:5000';
        }
    });
}

function saveHistory() {
    chrome.storage.sync.set({ analysisHistory }, () => {
        console.log('History saved');
    });
}

function loadHistory() {
    chrome.storage.sync.get(['analysisHistory'], (result) => {
        if (result.analysisHistory) {
            analysisHistory = result.analysisHistory;
        }
    });
}