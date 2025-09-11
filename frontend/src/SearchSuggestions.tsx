import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchSuggestionsProps {
  inputValue: string;
  onSuggestionClick: (suggestion: string) => void;
  isVisible: boolean;
}

const SearchSuggestions: React.FC<SearchSuggestionsProps> = ({
  inputValue,
  onSuggestionClick,
  isVisible
}) => {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Predefined suggestions for common issues
  const commonSuggestions = [
    "UPI payment failed with error 5003",
    "API timeout error after 30 seconds",
    "Database connection timeout",
    "Webhook retries exhausted",
    "SSL certificate validation failed",
    "Payment gateway timeout",
    "3DS authentication failed",
    "Card tokenization failing",
    "Settlement file parsing error",
    "OTP delivery latency",
    "Mandate creation timeout",
    "Refund webhook not processed",
    "Intent deeplink broken",
    "Authorization 3DS step fails",
    "API returning 500 error",
    "Database query performance issue",
    "Redis connection failed",
    "Load balancer health check failing",
    "Microservice discovery timeout",
    "JWT token validation error"
  ];

  useEffect(() => {
    if (!inputValue.trim() || inputValue.length < 2) {
      setSuggestions([]);
      return;
    }

    const fetchSuggestions = async () => {
      setIsLoading(true);
      try {
        // Try to fetch from API first
        const response = await fetch('http://localhost:8000/api/v1/search/suggestions');
        if (response.ok) {
          const data = await response.json();
          const apiSuggestions = data.suggestions || [];
          
          // Filter suggestions based on input
          const filtered = apiSuggestions.filter((suggestion: string) =>
            suggestion.toLowerCase().includes(inputValue.toLowerCase())
          );
          
          setSuggestions(filtered.slice(0, 5));
        } else {
          throw new Error('API not available');
        }
      } catch (error) {
        // Fallback to local suggestions
        const filtered = commonSuggestions.filter(suggestion =>
          suggestion.toLowerCase().includes(inputValue.toLowerCase())
        );
        setSuggestions(filtered.slice(0, 5));
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce the API call
    const timeoutId = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(timeoutId);
  }, [inputValue]);

  if (!isVisible || (!isLoading && suggestions.length === 0)) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
        className="search-suggestions"
      >
        {isLoading ? (
          <div className="suggestion-item loading">
            <div className="suggestion-loading">
              <div className="loading-spinner-small"></div>
              <span>Finding suggestions...</span>
            </div>
          </div>
        ) : (
          suggestions.map((suggestion, index) => (
            <motion.div
              key={suggestion}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: index * 0.05 }}
              className="suggestion-item"
              onClick={() => onSuggestionClick(suggestion)}
            >
              <div className="suggestion-icon">🔍</div>
              <div className="suggestion-text">
                {suggestion}
              </div>
            </motion.div>
          ))
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default SearchSuggestions;
