import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './styles.css';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isTyping?: boolean;
}

interface SearchResult {
  id: string;
  title: string;
  description: string;
  resolution: string;
  ai_suggestion: string;
  score: number;
  tags: string[];
  created_at: string;
  resolved_by?: string;
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  execution_time_ms: number;
  search_type: string;
  timestamp: string;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: "👋 Hi! I'm FixGenie, your AI-powered issue intelligence assistant. I can help you find solutions to technical problems based on our historical knowledge base.\n\nJust describe the issue you're facing, and I'll search through past incidents to find relevant solutions and provide AI-powered suggestions.",
      timestamp: new Date(),
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatSearchResults = (response: SearchResponse): string => {
    if (response.total_results === 0) {
      return `I couldn't find any similar issues in our knowledge base for "${response.query}". This might be a new type of issue.\n\n**Suggestions:**\n• Check if this is a known issue in recent documentation\n• Consider reaching out to the team that owns the affected service\n• Document this issue for future reference once resolved\n\n*Search completed in ${response.execution_time_ms.toFixed(0)}ms*`;
    }

    let formattedResponse = `I found **${response.total_results}** similar issue${response.total_results > 1 ? 's' : ''} that might help:\n\n`;

    response.results.forEach((result, index) => {
      formattedResponse += `## 🔍 **Issue #${index + 1}: ${result.title}**\n`;
      formattedResponse += `**Similarity Score:** ${(result.score * 100).toFixed(1)}%\n\n`;
      
      formattedResponse += `**Description:**\n${result.description}\n\n`;
      
      if (result.resolution) {
        formattedResponse += `**Resolution:**\n${result.resolution}\n\n`;
      }
      
      formattedResponse += `**💡 AI Suggestion:**\n${result.ai_suggestion}\n\n`;
      
      if (result.tags && result.tags.length > 0) {
        formattedResponse += `**Tags:** ${result.tags.map(tag => `\`${tag}\``).join(', ')}\n\n`;
      }
      
      if (result.resolved_by) {
        formattedResponse += `**Resolved by:** ${result.resolved_by}\n\n`;
      }
      
      formattedResponse += `---\n\n`;
    });

    formattedResponse += `*Search completed in ${response.execution_time_ms.toFixed(0)}ms using ${response.search_type} search*`;
    
    return formattedResponse;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    const typingMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isTyping: true,
    };

    setMessages(prev => [...prev, userMessage, typingMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage.content,
          top_k: 3,
          search_type: 'semantic'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const searchResponse: SearchResponse = await response.json();
      const formattedContent = formatSearchResults(searchResponse);

      // Remove typing message and add actual response
      setMessages(prev => {
        const newMessages = prev.filter(msg => !msg.isTyping);
        return [...newMessages, {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          content: formattedContent,
          timestamp: new Date(),
        }];
      });

    } catch (error) {
      console.error('Search error:', error);
      
      // Remove typing message and add error response
      setMessages(prev => {
        const newMessages = prev.filter(msg => !msg.isTyping);
        return [...newMessages, {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          content: `❌ I'm sorry, I encountered an error while searching for solutions. Please make sure the backend service is running and try again.\n\n**Error details:** ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date(),
        }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatMessageContent = (content: string) => {
    // Simple markdown-like formatting
    return content
      .split('\n')
      .map((line, index) => {
        if (line.startsWith('## ')) {
          return <h3 key={index} className="message-heading">{line.replace('## ', '')}</h3>;
        }
        if (line.startsWith('**') && line.endsWith('**')) {
          return <div key={index} className="message-bold">{line.replace(/\*\*/g, '')}</div>;
        }
        if (line.startsWith('*') && line.endsWith('*') && !line.includes('**')) {
          return <div key={index} className="message-italic">{line.replace(/\*/g, '')}</div>;
        }
        if (line === '---') {
          return <hr key={index} className="message-divider" />;
        }
        if (line.trim() === '') {
          return <br key={index} />;
        }
        
        // Handle inline code and tags
        const parts = line.split(/(`[^`]+`)/g);
        return (
          <div key={index} className="message-line">
            {parts.map((part, partIndex) => {
              if (part.startsWith('`') && part.endsWith('`')) {
                return <code key={partIndex} className="message-code">{part.slice(1, -1)}</code>;
              }
              return part;
            })}
          </div>
        );
      });
  };

  const TypingIndicator = () => (
    <div className="typing-indicator">
      <div className="typing-dot"></div>
      <div className="typing-dot"></div>
      <div className="typing-dot"></div>
    </div>
  );

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div className="header-content">
          <div className="header-title">
            <h1>🔧 FixGenie</h1>
            <span className="header-subtitle">AI-Powered Issue Intelligence</span>
          </div>
          <div className="header-status">
            <div className="status-indicator online"></div>
            <span>Online</span>
          </div>
        </div>
      </header>

      <div className="chat-messages">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className={`message ${message.type}`}
            >
              <div className="message-avatar">
                {message.type === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-header">
                  <span className="message-sender">
                    {message.type === 'user' ? 'You' : 'FixGenie'}
                  </span>
                  <span className="message-time">
                    {message.timestamp.toLocaleTimeString([], { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </span>
                </div>
                <div className="message-text">
                  {message.isTyping ? (
                    <TypingIndicator />
                  ) : (
                    formatMessageContent(message.content)
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="input-container">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Describe your issue... (e.g., 'UPI payment failed with timeout error')"
            className="chat-input"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading}
            className="send-button"
          >
            {isLoading ? (
              <div className="loading-spinner"></div>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path
                  d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
        <div className="input-footer">
          <span className="input-hint">
            💡 Try: "API timeout error", "Database connection failed", "Payment gateway issue"
          </span>
        </div>
      </form>
    </div>
  );
};

export default App;
