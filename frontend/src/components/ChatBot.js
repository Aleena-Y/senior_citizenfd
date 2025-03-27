import React, { useState, useRef, useEffect } from 'react';
import '../styles/ChatBot.css';

function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      type: 'bot',
      content: 'Hello! I\'m your FD Rate Assistant. How can I help you today?'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    // Add user message
    setMessages(prev => [...prev, { type: 'user', content: inputMessage }]);
    
    // Generate bot response
    const response = generateBotResponse(inputMessage);
    setTimeout(() => {
      setMessages(prev => [...prev, { type: 'bot', content: response }]);
    }, 500);

    setInputMessage('');
  };

  const generateBotResponse = (message) => {
    const lowerMessage = message.toLowerCase();
    
    // Basic response logic based on keywords
    if (lowerMessage.includes('rate') || lowerMessage.includes('interest')) {
      return 'I can help you find the best FD rates! Would you like to see rates for a specific tenure or bank?';
    } else if (lowerMessage.includes('tenure') || lowerMessage.includes('period')) {
      return 'We offer various tenures from short-term (7 days) to long-term (10 years). What duration are you interested in?';
    } else if (lowerMessage.includes('bank') || lowerMessage.includes('institution')) {
      return 'We have rates from multiple banks including public and private sector banks. Which type of bank would you prefer?';
    } else if (lowerMessage.includes('tax') || lowerMessage.includes('saving')) {
      return 'Yes, we have special tax-saving FD schemes. Would you like to know more about them?';
    } else if (lowerMessage.includes('senior') || lowerMessage.includes('citizen')) {
      return 'Yes, we offer special rates for senior citizens! Would you like to see those rates?';
    } else if (lowerMessage.includes('minimum') || lowerMessage.includes('amount')) {
      return 'The minimum deposit amount varies by bank and scheme. Most banks start from ₹1,000. Would you like to know more?';
    } else if (lowerMessage.includes('help') || lowerMessage.includes('assist')) {
      return 'I can help you with:\n- Finding best FD rates\n- Comparing different banks\n- Understanding tax benefits\n- Special schemes for senior citizens\nWhat would you like to know?';
    } else {
      return 'I\'m here to help you with FD rates and related information. Could you please be more specific about what you\'d like to know?';
    }
  };

  return (
    <div className="chatbot-container">
      <button 
        className="chatbot-toggle"
        onClick={() => setIsOpen(!isOpen)}
      >
        <img 
          src="/assets/lady-avatar.svg" 
          alt="Chat Assistant" 
          className="chatbot-avatar"
        />
        {!isOpen && <span className="chatbot-badge">💬</span>}
      </button>

      {isOpen && (
        <div className="chatbot-window">
          <div className="chatbot-header">
            <h3>FD Rate Assistant</h3>
            <button 
              className="close-button"
              onClick={() => setIsOpen(false)}
            >
              ×
            </button>
          </div>
          
          <div className="chatbot-messages">
            {messages.map((message, index) => (
              <div 
                key={index} 
                className={`message ${message.type}-message`}
              >
                {message.type === 'bot' && (
                  <img 
                    src="/assets/lady-avatar.svg" 
                    alt="Assistant" 
                    className="message-avatar"
                  />
                )}
                <div className="message-content">
                  {message.content.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="chatbot-input">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Type your message..."
              className="message-input"
            />
            <button type="submit" className="send-button">
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export default ChatBot; 