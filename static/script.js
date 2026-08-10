const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const resetBtn = document.getElementById('reset-btn');
const loading = document.getElementById('loading');

function addMessage(text, isUser) {
    const messageDiv = document.createElement('div');
    const label = isUser ? 'You' : 'Assistant';
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = label;

    const content = document.createElement('div');
    content.className = 'message-content';

    if (isUser) {
        content.textContent = text;
    } else {
        content.innerHTML = renderMarkdown(text);
    }

    messageDiv.appendChild(header);
    messageDiv.appendChild(content);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    userInput.value = '';
    loading.style.display = 'block';

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `query=${encodeURIComponent(message)}`
        });

        const data = await response.json();

        if (data.error) {
            addMessage('Error: ' + data.error);
        } else {
            addMessage(data.response);
        }
    } catch (error) {
        addMessage('Request failed: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

async function resetConversation() {
    try {
        const response = await fetch('/reset', { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            addMessage('Error: ' + data.error);
        } else {
            addMessage('Conversation history cleared.');
        }
    } catch (error) {
        addMessage('Reset failed: ' + error.message);
    }
}

sendBtn.addEventListener('click', sendMessage);

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
});

resetBtn.addEventListener('click', resetConversation);
userInput.focus();

function renderMarkdown(text) {
    text = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gm, '<h1>$1</h1>');
    text = text.replace(/^\* (.*$)/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)+/gs, '<ul>$&</ul>');
    text = text.replace(/^(?!<[\/]?[h|u|l|p|b|i|e|c|s])/gm, '<p>')
        .replace(/(<[\/](h[1-6]|ul|li|p|b|i|e|c|s|strong|em|pre|code)>)\s*(?=<)/g, '$1')
        .replace(/(<[\/](h[1-6]|ul|li|p|b|i|e|c|s|strong|em|pre|code)>)\s*$/g, '$1');

    return text;
}