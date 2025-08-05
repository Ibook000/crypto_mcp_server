// DOM elements
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const resetBtn = document.getElementById('reset-btn');
const loading = document.getElementById('loading');

// Add message to chat
function addMessage(text, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    // Add message header
    const messageHeader = document.createElement('div');
    messageHeader.className = 'message-header';
    messageHeader.textContent = isUser ? '👤 您' : '🤖 助手';
    
    // Add message content
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    // Handle markdown content
    if (!isUser) {
        // For AI responses, we'll render markdown
        messageContent.innerHTML = renderMarkdown(text);
    } else {
        // For user messages, just display as plain text
        messageContent.textContent = text;
    }
    
    messageDiv.appendChild(messageHeader);
    messageDiv.appendChild(messageContent);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Send message to backend
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, true);
    userInput.value = '';
    
    // Show loading indicator
    loading.style.display = 'block';
    
    try {
        // Send message to backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `query=${encodeURIComponent(message)}`
        });
        
        const data = await response.json();
        
        if (data.error) {
            addMessage(`❌ 错误: ${data.error}`, false);
        } else {
            addMessage(data.response, false);
        }
    } catch (error) {
        addMessage(`❌ 请求失败: ${error.message}`, false);
    } finally {
        // Hide loading indicator
        loading.style.display = 'none';
    }
}

// Reset conversation
async function resetConversation() {
    try {
        const response = await fetch('/reset', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.error) {
            addMessage(`❌ 错误: ${data.error}`, false);
        } else {
            addMessage(`🔄 ${data.status}`, false);
        }
    } catch (error) {
        addMessage(`❌ 重置失败: ${error.message}`, false);
    }
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        // Prevent form submission on Enter
        e.preventDefault();
        sendMessage();
    }
});

resetBtn.addEventListener('click', resetConversation);

// Focus input on load
userInput.focus();

// Simple markdown rendering function
function renderMarkdown(text) {
    // Convert code blocks
    text = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Convert inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Convert bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic text
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert headers
    text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gm, '<h1>$1</h1>');
    
    // Convert unordered lists
    text = text.replace(/^\* (.*$)/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)+/gs, '<ul>$&</ul>');
    
    // Convert paragraphs
    text = text.replace(/^(?!<[\/]?[h|u|l|p|b|i|e|c|s])/gm, '<p>')
              .replace(/(<[\/](h[1-6]|ul|li|p|b|i|e|c|s|strong|em|pre|code)>)\s*(?=<)/g, '$1')
              .replace(/(<[\/](h[1-6]|ul|li|p|b|i|e|c|s|strong|em|pre|code)>)\s*$/g, '$1');
    
    return text;
}