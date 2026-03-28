// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
let chatHistory = [];

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, historyList;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    historyList = document.getElementById('historyList');

    document.getElementById('newChatButton').addEventListener('click', createNewSession);

    setupEventListeners();
    createNewSession();
    loadCourseStats();
    loadChatHistory();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });


    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
            loadChatHistory();
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        const bookIcon = `<svg class="source-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`;
        const sourceCards = sources.map(s => {
            const parts = s.label.match(/^(.+?)\s*-\s*(Lesson \d+)$/);
            const courseName = parts ? escapeHtml(parts[1]) : escapeHtml(s.label);
            const lessonNum = parts ? escapeHtml(parts[2]) : '';
            return `<a href="${s.url}" target="_blank" class="source-card">
                <span class="source-card-icon">${bookIcon}</span>
                <span class="source-card-text">
                    <span class="source-card-course">${courseName}</span>
                    ${lessonNum ? `<span class="source-card-lesson">${lessonNum}</span>` : ''}
                </span>
            </a>`;
        }).join('');
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content sources-list">${sourceCards}</div>
            </details>
        `;
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
    await loadChatHistory();
}

// Chat History Functions

async function loadChatHistory() {
    try {
        const response = await fetch(`${API_URL}/sessions`);
        if (!response.ok) return;
        const data = await response.json();
        chatHistory = data.sessions;
        renderChatHistory();
    } catch (e) {
        console.error('Failed to load chat history:', e);
    }
}

function renderChatHistory() {
    if (!historyList) return;
    if (chatHistory.length === 0) {
        historyList.innerHTML = '<span class="no-history">No previous chats</span>';
        return;
    }
    historyList.innerHTML = chatHistory.map(session => {
        const isActive = session.session_id === currentSessionId;
        const exchanges = Math.floor(session.message_count / 2);
        return `<button
            class="history-item${isActive ? ' active' : ''}"
            data-session-id="${session.session_id}">
            <span class="history-title">${escapeHtml(session.title)}</span>
            <span class="history-meta">${exchanges} exchange${exchanges !== 1 ? 's' : ''}</span>
        </button>`;
    }).join('');

    historyList.querySelectorAll('.history-item').forEach(btn => {
        btn.addEventListener('click', () => loadSession(btn.dataset.sessionId));
    });
}

async function loadSession(sessionId) {
    if (sessionId === currentSessionId) return;
    try {
        const response = await fetch(`${API_URL}/sessions/${sessionId}`);
        if (!response.ok) return;
        const data = await response.json();

        currentSessionId = sessionId;
        chatMessages.innerHTML = '';

        data.messages.forEach(msg => {
            addMessage(msg.content, msg.role);
        });

        renderChatHistory();
    } catch (e) {
        console.error('Failed to load session:', e);
    }
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');

        const data = await response.json();
        console.log('Course data received:', data);

        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }

        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }

    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}
