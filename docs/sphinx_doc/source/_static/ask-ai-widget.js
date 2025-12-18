/**
 * Ask AI Widget
 */
class AskAIWidget {
  constructor() {
    this.isOpen = false;
    this.messages = [];
    this.isTyping = false;
    this.apiConnected = false;
    this.sessionId = this.generateSessionId();
    this.init();
  }

  generateSessionId() {
    // Try to get existing session ID from sessionStorage
    let sessionId = sessionStorage.getItem('ask-ai-session-id');

    if (!sessionId) {
      // Generate new session ID if none exists
      sessionId = `browser-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('ask-ai-session-id', sessionId);
    }

    console.log('Using session ID:', sessionId);
    return sessionId;
  }

  async init() {
    this.createWidget();
    this.bindEvents();
    this.observeThemeChanges();
    await this.checkApiConnection();
    await this.loadConversationHistory();
    this.addWelcomeMessage();
  }



  createWidget() {
    // Create widget container
    const widget = document.createElement('div');
    widget.className = 'ask-ai-widget';
    widget.innerHTML = `
      <!-- Ask AI Button -->
      <button class="ask-ai-button" id="askAiButton" title="Ask Juicer">
        🤖
      </button>

      <!-- Chat Modal -->
      <div class="ask-ai-modal" id="askAiModal">
        <!-- Header -->
        <div class="ask-ai-header">
          <h3 class="ask-ai-title">DataJuicer Q&A Copilot</h3>
          <div class="ask-ai-header-buttons">
            <button class="ask-ai-clear" id="askAiClear" title="Restart conversation"><i class="fa-solid fa-arrows-rotate"></i></button>
            <button class="ask-ai-expand" id="askAiExpand" title="Expand/Collapse"><i class="fa-solid fa-expand"></i></button>
            <button class="ask-ai-close" id="askAiClose" title="Minimize"><i class="fa-solid fa-minus"></i></button>
          </div>
        </div>

        <!-- Messages Area -->
        <div class="ask-ai-messages" id="askAiMessages">
          <div class="ask-ai-welcome">
            👋 Hi! I'm Juicer. Ask me anything about Data-Juicer!
          </div>
        </div>

        <!-- Input Area -->
        <div class="ask-ai-input-area">
          <textarea 
            class="ask-ai-input" 
            id="askAiInput" 
            placeholder="Type your question here..."
            rows="1"
          ></textarea>
          <button class="ask-ai-send" id="askAiSend" title="Send message">
            ➤
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(widget);

    // Store references
    this.button = document.getElementById('askAiButton');
    this.modal = document.getElementById('askAiModal');
    this.closeBtn = document.getElementById('askAiClose');
    this.clearBtn = document.getElementById('askAiClear');
    this.expandBtn = document.getElementById('askAiExpand');
    this.messagesContainer = document.getElementById('askAiMessages');
    this.input = document.getElementById('askAiInput');
    this.sendBtn = document.getElementById('askAiSend');
    this.isExpanded = false;
  }

  bindEvents() {
    // Toggle modal
    this.button.addEventListener('click', () => this.toggleModal());
    this.closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.closeModal();
    });
    this.clearBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.clearConversation();
    });
    this.expandBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleExpand();
    });

    // Send message
    this.sendBtn.addEventListener('click', () => this.sendMessage());

    // Handle Enter key in input
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Auto-resize textarea
    this.input.addEventListener('input', () => this.autoResizeInput());

    // Close modal when clicking outside
    document.addEventListener('click', (e) => {
      if (this.isOpen && 
          !this.modal.contains(e.target) && 
          !this.button.contains(e.target) &&
          !this.expandBtn.contains(e.target) &&
          !this.closeBtn.contains(e.target) &&
          !this.clearBtn.contains(e.target)) {
        this.closeModal();
      }
    });

    // Handle escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.closeModal();
      }
    });
  }

  toggleModal() {
    if (this.isOpen) {
      this.closeModal();
    } else {
      this.openModal();
    }
  }

  openModal() {
    this.isOpen = true;
    this.modal.classList.add('show');
    this.input.focus();
    this.scrollToBottom();
  }

  closeModal() {
    this.isOpen = false;
    this.modal.classList.remove('show');
  }

  toggleExpand() {
    this.isExpanded = !this.isExpanded;
    
    if (this.isExpanded) {
      this.modal.classList.add('expanded');
      // 尝试查找图标元素（可能是 <i> 或 <svg>）
      const icon = this.expandBtn.querySelector('i, svg');
      if (icon) {
        icon.classList.remove('fa-expand');
        icon.classList.add('fa-compress');
      }
      this.expandBtn.title = 'Collapse';
    } else {
      this.modal.classList.remove('expanded');
      // 尝试查找图标元素（可能是 <i> 或 <svg>）
      const icon = this.expandBtn.querySelector('i, svg');
      if (icon) {
        icon.classList.remove('fa-compress');
        icon.classList.add('fa-expand');
      }
      this.expandBtn.title = 'Expand';
    }
  }

  autoResizeInput() {
    this.input.style.height = 'auto';
    this.input.style.height = Math.min(this.input.scrollHeight, 100) + 'px';
  }

  async checkApiConnection() {
    try {
      const response = await fetch(`${this.getApiBaseUrl()}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': this.sessionId
        }
      });

      if (response.ok) {
        const data = await response.json();
        this.apiConnected = data.status === 'healthy';
      } else {
        this.apiConnected = false;
      }
    } catch (error) {
      console.warn('Failed to connect to API:', error);
      this.apiConnected = false;
    }
  }

  async loadConversationHistory() {
    if (!this.apiConnected) {
      console.log('API not connected, skipping history load');
      return;
    }

    try {
      const requestBody = {
        input: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: "",
              },
            ],
          },
        ],
        session_id: this.sessionId,
        user_id: "",
      };
      console.log('Loading conversation history for session:', this.sessionId);

      const response = await fetch(`${this.getApiBaseUrl()}/memory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': this.sessionId
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const data = await response.json();
        const messages = data.messages || [];

        console.log('Loaded', messages.length, 'historical messages');

        // Clear existing messages (except welcome message)
        const existingMessages = this.messagesContainer.querySelectorAll('.ask-ai-message');
        existingMessages.forEach(msg => msg.remove());

        // Add historical messages
        messages.forEach(msg => {
          if (msg.content && typeof msg.content === 'string') {
            const isUser = msg.role === 'user';
            const content = msg.content.trim();

            // 简单判断：如果以 [{ 开头且以 }] 结尾，很可能是 JSON 数组
            if (!(content.startsWith('[{') && content.endsWith('}]'))) {
              if (content) {
                // Generate message ID for historical messages if not present
                const messageId = msg.id || `history_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                this.addMessage(content, isUser ? 'user' : 'assistant', messageId);
              }
            }
          }
        });

        // Store messages in local array
        this.messages = messages;

        if (messages.length > 0) {
          this.scrollToBottom();
        }
      } else {
        console.warn('Failed to load conversation history:', response.status);
      }
    } catch (error) {
      console.warn('Error loading conversation history:', error);
    }
  }

  addWelcomeMessage() {
    // Only add welcome message if no history was loaded
    if (this.messages.length === 0) {
      // Update welcome message based on API connection status
      const welcomeElement = this.messagesContainer.querySelector('.ask-ai-welcome');
      if (welcomeElement) {
        if (this.apiConnected) {
          welcomeElement.innerHTML = '👋 Hi! I\'m Juicer, your AI assistant for Data-Juicer! <span style="color: #28a745;">🟢 Connected</span><br>Ask me anything about Data-Juicer!';
        } else {
          welcomeElement.innerHTML = '👋 Hi! I\'m Juicer, your AI assistant for Data-Juicer! <span style="color: #dc3545;">🔴 Offline Mode</span><br>Please ensure the API service is running.';
        }
      }
    } else {
      // Remove welcome message if we have history
      const welcomeElement = this.messagesContainer.querySelector('.ask-ai-welcome');
      if (welcomeElement) {
        welcomeElement.remove();
      }
    }
  }

  async sendMessage() {
    const message = this.input.value.trim();
    if (!message || this.isTyping) return;

    // Add user message
    this.addMessage(message, 'user');
    this.input.value = '';
    this.autoResizeInput();

    try {
      // Start streaming - this will handle the typing indicator internally
      await this.getAIResponseStream(message);
    } catch (error) {
      this.addMessage('Sorry, I encountered an error. Please try again later.', 'assistant');
      console.error('AI response error:', error);
    }
  }

  addMessage(content, type, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `ask-ai-message ${type}`;
    
    // For assistant messages, render as markdown; for user messages, keep as plain text
    if (type === 'assistant') {
      messageDiv.innerHTML = this.renderMarkdown(content);
    } else {
      messageDiv.textContent = content;
    }

    // Generate unique message ID if not provided
    const msgId = messageId || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    messageDiv.setAttribute('data-message-id', msgId);


    this.messagesContainer.appendChild(messageDiv);
    this.scrollToBottom();

    // Store message
    this.messages.push({ content, type, timestamp: Date.now(), messageId: msgId });
  }

  showTypingIndicator() {
    this.isTyping = true;
    this.sendBtn.disabled = true;

    const typingDiv = document.createElement('div');
    typingDiv.className = 'ask-ai-message typing';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;

    this.messagesContainer.appendChild(typingDiv);
    this.scrollToBottom();
  }

  hideTypingIndicator() {
    this.isTyping = false;
    this.sendBtn.disabled = false;

    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
      typingIndicator.remove();
    }
  }

  scrollToBottom() {
    setTimeout(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }, 100);
  }




  async clearConversation() {
    if (!confirm('Are you sure you want to clear the conversation history? This action cannot be undone.')) {
      return;
    }

    try {
      // Call the clear endpoint
      const requestBody = {
        input: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: "",
              },
            ],
          },
        ],
        session_id: this.sessionId,
        user_id: "",
      };

      const response = await fetch(`${this.getApiBaseUrl()}/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': this.sessionId
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        // Clear local messages
        this.messages = [];
        
        // Clear UI messages
        const existingMessages = this.messagesContainer.querySelectorAll('.ask-ai-message');
        existingMessages.forEach(msg => msg.remove());
        
        // Remove welcome message if it exists
        const welcomeElement = this.messagesContainer.querySelector('.ask-ai-welcome');
        if (welcomeElement) {
          welcomeElement.remove();
        }
        
        // Add the original welcome message (same as first-time opening)
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'ask-ai-welcome';
        welcomeDiv.innerHTML = '👋 Hi! I\'m Juicer. Ask me anything about Data-Juicer!';
        this.messagesContainer.appendChild(welcomeDiv);
        
        console.log('Conversation history cleared successfully');
      } else {
        console.error('Failed to clear conversation history:', response.status);
        alert('Failed to clear conversation history. Please try again.');
      }
    } catch (error) {
      console.error('Error clearing conversation history:', error);
      alert('Error clearing conversation history. Please check your connection and try again.');
    }
  }

  async getAIResponseStream(message) {
    const assistantMessageDiv = document.createElement('div');
    assistantMessageDiv.className = 'ask-ai-message assistant';

    // Initialize with temporary ID, will be replaced with server ID
    let messageId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    assistantMessageDiv.setAttribute('data-message-id', messageId);

    // Show typing indicator initially
    assistantMessageDiv.innerHTML = `
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;

    this.messagesContainer.appendChild(assistantMessageDiv);
    this.scrollToBottom();

    this.isTyping = true;
    this.sendBtn.disabled = true;

    let hasReceivedContent = false;

    try {
      // Prepare request according to backend spec
      const requestBody = {
        input: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: message.trim(),
              },
            ],
          },
        ],
        session_id: this.sessionId,
        user_id: "",
      };

      console.log('Sending streaming request to:', `${this.getApiBaseUrl()}/process`);
      console.log('Request body:', requestBody);

      const response = await fetch(`${this.getApiBaseUrl()}/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': this.sessionId,
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data:')) continue;

          const jsonString = line.slice(5).trim(); // Remove "data:"
          if (!jsonString) continue;

          try {
            const data = JSON.parse(jsonString);
            console.log('Parsed SSE event:', data);

            // End of stream
            if (data.object === "response" && data.status === "completed") {
              console.log('Stream ended normally.');
              break;
            }

            // Handle errors
            if (data.object === "response" && data.error) {
              throw new Error(data.error.message || 'An error occurred during processing.');
            }

            // Handle tool use: plugin_call
            if (data.object === "message" && data.type === "plugin_call") {
              const toolCall = data.content.find(item => item.type === "data")?.data;
              if (toolCall) {
                const toolName = toolCall.name || 'Unknown Tool';
                assistantMessageDiv.innerHTML = `
                  <div class="tool-indicator" style="color: #888; font-style: italic; font-size: 0.9em; opacity: 0.8;">
                    <span class="tool-icon">🔧</span>
                    <span class="tool-text">Using ${toolName}</span>
                    <span class="tool-dots">
                      <span style="animation: blink 1.4s infinite both; animation-delay: 0.0s;">.</span>
                      <span style="animation: blink 1.4s infinite both; animation-delay: 0.2s;">.</span>
                      <span style="animation: blink 1.4s infinite both; animation-delay: 0.4s;">.</span>
                    </span>
                  </div>
                  <style>
                    @keyframes blink {
                      0%, 80%, 100% { opacity: 0; }
                      40% { opacity: 1; }
                    }
                  </style>
                `;
                this.scrollToBottom();
              }
            }

            // Handle tool output: plugin_call_output
            if (data.object === "message" && data.type === "plugin_call_output") {
              const output = data.content.find(item => item.type === "data")?.data?.output;
              if (output) {
                console.log('Tool output received:', output.substring(0, 200) + '...');
                // Optionally render output in collapsed section
              }
            }

            // Handle incremental text content
            if (
              data.object === "content" &&
              data.type === "text" &&
              data.delta === true &&
              data.text !== undefined
            ) {
              if (!hasReceivedContent) {
                assistantMessageDiv.textContent = '';
                this.currentStreamContent = '';
                hasReceivedContent = true;
              }
              this.currentStreamContent += data.text;
              // Render markdown for the accumulated content
              assistantMessageDiv.innerHTML = this.renderMarkdown(this.currentStreamContent);
              this.scrollToBottom();
            }

            // Final message delivery (optional sync)
            if (
              data.object === "message" &&
              data.status === "completed" &&
              data.role === "assistant" &&
              Array.isArray(data.content)
            ) {
              const fullText = data.content
                .filter(c => c.type === "text")
                .map(c => c.text)
                .join('');
              if (fullText && !hasReceivedContent) {
                assistantMessageDiv.innerHTML = this.renderMarkdown(fullText);
                hasReceivedContent = true;
                this.scrollToBottom();
              }
              
              // Use server-provided message ID
              if (data.id) {
                messageId = data.id;
                assistantMessageDiv.setAttribute('data-message-id', data.id);
                console.log('Using server message ID:', data.id);
              }
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE data:', parseError, 'Raw:', jsonString);
          }
        }
      }

      // Final fallback: ensure there's content
      if (!hasReceivedContent || !assistantMessageDiv.textContent.trim()) {
        assistantMessageDiv.innerHTML = this.renderMarkdown(
          'I processed your request but no valid response was generated. Please try again.'
        );
      }
    } catch (error) {
      console.error('Fetch error:', error);
      assistantMessageDiv.innerHTML = this.renderMarkdown(
        '无法连接到 AI 服务，请检查网络或联系管理员。'
      );
    } finally {
      this.isTyping = false;
      this.sendBtn.disabled = false;
      
      // Store message in local array with server-provided ID
      this.messages.push({ 
        content: assistantMessageDiv.textContent, 
        type: 'assistant', 
        timestamp: Date.now(), 
        messageId: messageId  // This will be the server ID if available
      });
    }
  }
  // Keep the old method for backward compatibility
  async getAIResponse(message) {
    try {
      // This method now just calls the streaming version and returns the final result
      const messageDiv = document.createElement('div');
      await this.getAIResponseStream(message, messageDiv);
      return messageDiv.textContent;
    } catch (error) {
      console.error('API call failed:', error);
      return this.getOfflineResponse(message);
    }
  }

  getApiBaseUrl() {
    // 优先从 meta 标签获取配置
    const metaApiUrl = document.querySelector('meta[name="juicer-api-url"]');
    if (metaApiUrl && metaApiUrl.content) {
      return metaApiUrl.content;
    }

    // 从全局变量获取配置
    if (window.JUICER_API_URL) {
      return window.JUICER_API_URL;
    }

    const currentHost = window.location.hostname;

    // Default to localhost for development
    if (currentHost === 'localhost' || currentHost === '127.0.0.1') {
      return 'http://localhost:8080';
    }

    return 'http://localhost:8080';
  }


  getOfflineResponse(message) {
    // Unified offline response when API is not available
    return "Sorry, the Q&A Bot API is not configured or currently unavailable. Please refer to the Data-Juicer documentation for information, or contact the administrator to configure the API service.";
  }

  renderMarkdown(text) {
    if (!text) return '';
    
    // Escape HTML first to prevent XSS
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

    // Code blocks (```language\ncode\n```)
    html = html.replace(/```(\w+)?\n([\s\S]*?)\n```/g, (match, lang, code) => {
      const language = lang ? ` class="language-${lang}"` : '';
      return `<pre><code${language}>${code}</code></pre>`;
    });

    // Inline code (`code`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold (**text** or __text__)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');

    // Italic (*text* or _text_)
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

    // Links [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Headers (# ## ###)
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Unordered lists (- item or * item)
    html = html.replace(/^[\s]*[-*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Ordered lists (1. item)
    html = html.replace(/^[\s]*\d+\. (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, (match) => {
      // Check if this is part of an unordered list already
      if (match.includes('<ul>')) {
        return match;
      }
      return `<ol>${match}</ol>`;
    });

    // Line breaks (double newline becomes paragraph)
    html = html.replace(/\n\n/g, '</p><p>');
    html = `<p>${html}</p>`;

    // Single line breaks
    html = html.replace(/\n/g, '<br>');

    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>\s*<\/p>/g, '');

    return html;
  }

  // Helper function to detect JSON list strings

  // Public method to add custom responses
  addCustomResponse(keywords, response) {
    // This could be extended to add custom keyword-response mappings
    console.log('Custom response added:', keywords, response);
  }

  // Observe theme changes from the Sphinx theme
  observeThemeChanges() {
    // Apply initial theme
    this.updateWidgetTheme();

    // Watch for theme changes on html or body element
    const targetNode = document.documentElement || document.body;
    
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && 
            (mutation.attributeName === 'class' || 
             mutation.attributeName === 'data-theme' ||
             mutation.attributeName === 'data-bs-theme')) {
          this.updateWidgetTheme();
        }
      });
    });

    observer.observe(targetNode, {
      attributes: true,
      attributeFilter: ['class', 'data-theme', 'data-bs-theme']
    });
  }

  updateWidgetTheme() {
    const html = document.documentElement;
    const body = document.body;
    
    // Check various theme indicators
    const isDark = 
      html.getAttribute('data-theme') === 'dark';
    
    if (isDark) {
      this.modal.classList.add('theme-dark');
      this.button.classList.add('theme-dark');
    } else {
      this.modal.classList.remove('theme-dark');
      this.button.classList.remove('theme-dark');
    }
  }
}

// Initialize the widget when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
  // Check if we're in a Sphinx documentation page
  if (document.body.classList.contains('furo') || document.querySelector('.furo')) {
    new AskAIWidget();
  } else {
    // Fallback for other themes
    setTimeout(() => {
      new AskAIWidget();
    }, 1000);
  }
});

// Export for potential external usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AskAIWidget;
}