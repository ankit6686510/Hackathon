import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SearchSuggestions from './SearchSuggestions';
import GoogleAuth from './components/GoogleAuth';
import './styles.css';
import './components/auth.css';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isTyping?: boolean;
  searchResults?: SearchResult[];
  searchQuery?: string;
}

interface SearchResult {
  id: string;
  title: string;
  description: string;
  resolution: string;
  ai_suggestion: string;
  score: number;
  fused_score?: number;
  tags: string[];
  created_at: string;
  resolved_by?: string;
  // Additional properties from RAG response
  semantic_score?: number;
  bm25_score?: number;
  tfidf_score?: number;
  search_type?: string;
  search_methods?: string[];
  method_count?: number;
  relevance_score?: number;
  boosted_score?: number;
  // Priority matching properties
  match_type?: string;
  priority_details?: {
    query_merchant?: string;
    query_gateway?: string;
    result_merchant?: string;
    result_gateway?: string;
    merchant_match?: boolean;
    gateway_match?: boolean;
    exact_match?: boolean;
  };
}

interface FeedbackState {
  [resultId: string]: {
    rating?: number;
    helpful?: boolean;
    submitted: boolean;
    loading?: boolean;
    error?: boolean;
    feedbackId?: string;
  };
}

interface SearchResponse {
  result?: {
    query: string;
    generated_answer: string;
    retrieved_incidents: SearchResult[];
    sources: string[];
    confidence_score: number;
    query_complexity: string;
    execution_time_ms: number;
    rag_strategy: string;
  };
  metadata?: {
    confidence_level: string;
    incidents_retrieved: number;
    status: string;
  };
  // Legacy hybrid search format
  query?: string;
  results?: SearchResult[];
  total_results?: number;
  execution_time_ms?: number;
  search_type?: string;
  timestamp?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  given_name?: string;
  family_name?: string;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: "👋 Hi! I'm SherlockAI, your AI-powered payment issue intelligence assistant. I specialize in helping you solve payment-related problems based on our historical knowledge base.\n\n💳 **I focus exclusively on payment domain issues:**\n• UPI payment failures\n• Card transaction problems\n• Payment gateway timeouts\n• Wallet integration issues\n• Bank API errors\n• Settlement problems\n\nJust describe your payment issue, and I'll search through past incidents to find relevant solutions!",
      timestamp: new Date(),
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState>({});
  const [connectionStatus, setConnectionStatus] = useState<'online' | 'offline' | 'error'>('online');
  const [retryCount, setRetryCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Authentication state
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  // Error boundary state
  const [errorBoundary, setErrorBoundary] = useState<ErrorBoundaryState>({ hasError: false });

  // Check backend connectivity on mount
  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Check for existing session on mount
  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/me', {
        method: 'GET',
        credentials: 'include', // Include cookies
      });

      if (response.ok) {
        const data = await response.json();
        if (data.user) {
          setUser(data.user);
          setAccessToken(data.access_token);
        }
      }
    } catch (error) {
      console.error('Session check error:', error);
    } finally {
      setIsAuthLoading(false);
    }
  };

  // Authentication handlers
  const handleLoginSuccess = (userData: User, token: string) => {
    setUser(userData);
    setAccessToken(token);
    
    // Show welcome message
    const welcomeMessage: Message = {
      id: 'auth-welcome-' + Date.now(),
      type: 'assistant',
      content: `🎉 Welcome back, ${userData.name}! You're now signed in to SherlockAI.\n\nYour personalized payment issue intelligence is ready. I can now provide more tailored assistance based on your preferences and history.`,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, welcomeMessage]);
  };

  const handleLogoutSuccess = () => {
    setUser(null);
    setAccessToken(null);
    
    // Show logout message
    const logoutMessage: Message = {
      id: 'auth-logout-' + Date.now(),
      type: 'assistant',
      content: '👋 You have been signed out successfully. You can continue using SherlockAI as a guest, or sign in again for personalized features.',
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, logoutMessage]);
  };

  const checkBackendHealth = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/health', {
        method: 'GET',
        timeout: 5000
      } as any);
      
      if (response.ok) {
        setConnectionStatus('online');
        setRetryCount(0);
      } else {
        setConnectionStatus('error');
      }
    } catch (error) {
      setConnectionStatus('offline');
    }
  };

  // Submit feedback for a search result
  const submitFeedback = async (resultId: string, isHelpful: boolean, rating: number, searchQuery: string) => {
    // Set loading state for this specific result
    setFeedback(prev => ({
      ...prev,
      [resultId]: {
        ...prev[resultId],
        loading: true
      }
    }));

    try {
      // Prepare feedback data according to backend API requirements
      const feedbackData = {
        query: searchQuery,
        result_id: resultId,
        rating: rating,
        feedback_text: isHelpful ? "User found this suggestion helpful" : "User found this suggestion not helpful",
        helpful: isHelpful
      };

      const response = await fetch('http://localhost:8000/api/v1/analytics/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackData),
      });

      if (response.ok) {
        const responseData = await response.json();
        
        // Update feedback state with success
        setFeedback(prev => ({
          ...prev,
          [resultId]: {
            rating,
            helpful: isHelpful,
            submitted: true,
            loading: false,
            feedbackId: responseData.feedback_id
          }
        }));

        // Show brief success message
        const successMessage: Message = {
          id: 'feedback-success-' + Date.now(),
          type: 'assistant',
          content: `✅ ${isHelpful ? 'Great! Your positive feedback helps us improve.' : 'Thank you for the feedback. We\'ll work on better suggestions.'}`,
          timestamp: new Date(),
        };
        
        setMessages(prev => [...prev, successMessage]);
        
        // Remove success message after 4 seconds
        setTimeout(() => {
          setMessages(prev => prev.filter(msg => msg.id !== successMessage.id));
        }, 4000);
        
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      
      // Reset loading state and show error
      setFeedback(prev => ({
        ...prev,
        [resultId]: {
          ...prev[resultId],
          loading: false,
          error: true
        }
      }));
      
      // Show error message with retry option
      const errorMessage: Message = {
        id: 'feedback-error-' + Date.now(),
        type: 'assistant',
        content: '❌ Failed to submit feedback. Please check your connection and try again.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
      
      setTimeout(() => {
        setMessages(prev => prev.filter(msg => msg.id !== errorMessage.id));
      }, 5000);
    }
  };

  // Share functionality - copy conversation to clipboard
  const handleShare = async () => {
    try {
      const conversationText = messages
        .filter(msg => !msg.isTyping)
        .map(msg => {
          const timestamp = msg.timestamp.toLocaleString();
          const sender = msg.type === 'user' ? 'You' : 'SherlockAI';
          return `[${timestamp}] ${sender}:\n${msg.content}\n`;
        })
        .join('\n---\n\n');

      const shareText = `SherlockAI Conversation Export\n${'='.repeat(40)}\n\n${conversationText}`;
      
      await navigator.clipboard.writeText(shareText);
      
      // Show temporary success message
      const tempMessage: Message = {
        id: 'temp-share-' + Date.now(),
        type: 'assistant',
        content: '✅ Conversation copied to clipboard successfully!',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, tempMessage]);
      
      // Remove the temporary message after 3 seconds
      setTimeout(() => {
        setMessages(prev => prev.filter(msg => msg.id !== tempMessage.id));
      }, 3000);
      
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      
      // Show error message
      const errorMessage: Message = {
        id: 'temp-error-' + Date.now(),
        type: 'assistant',
        content: '❌ Failed to copy conversation to clipboard. Please try again.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
      
      // Remove the error message after 3 seconds
      setTimeout(() => {
        setMessages(prev => prev.filter(msg => msg.id !== errorMessage.id));
      }, 3000);
    }
  };

  // Delete chat functionality
  const handleDeleteChat = () => {
    setShowDeleteConfirm(true);
  };

  const confirmDeleteChat = () => {
    // Reset to initial welcome message
    setMessages([
      {
        id: '1',
        type: 'assistant',
        content: "👋 Hi! I'm SherlockAI, your AI-powered payment issue intelligence assistant. I specialize in helping you solve payment-related problems based on our historical knowledge base.\n\n💳 **I focus exclusively on payment domain issues:**\n• UPI payment failures\n• Card transaction problems\n• Payment gateway timeouts\n• Wallet integration issues\n• Bank API errors\n• Settlement problems\n\nJust describe your payment issue, and I'll search through past incidents to find relevant solutions!",
        timestamp: new Date(),
      }
    ]);
    setShowDeleteConfirm(false);
    setInputValue('');
    setFeedback({});
    setRetryCount(0);
  };

  const cancelDeleteChat = () => {
    setShowDeleteConfirm(false);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, [inputValue]);

  const formatSearchResults = (response: SearchResponse): { content: string; results: SearchResult[] } => {
    // Handle RAG response format with enhanced formatting
    if (response.result) {
      const ragResult = response.result;
      
      // Check if it's a "no results" response
      if (ragResult.retrieved_incidents.length === 0) {
        return {
          content: ragResult.generated_answer,
          results: []
        };
      }

      // Create enhanced incident report format
      const topIncident = ragResult.retrieved_incidents[0];
      const confidence = ragResult.confidence_score;
      const executionTime = ragResult.execution_time_ms;
      
      // ENHANCED MATCH DETECTION AND CONTEXT INTELLIGENCE
      const isPerfectMatch = confidence >= 0.98;
      const isExactMatch = confidence >= 0.9;
      const isHighlyRelevant = confidence >= 0.75;
      const isModeratelyRelevant = confidence >= 0.5;
      const isLowRelevant = confidence >= 0.3;
      
      // Detect technical domain for smart context
      const queryLower = ragResult.query.toLowerCase();
      const titleLower = topIncident.title.toLowerCase();
      
      let technicalDomain = '';
      let domainIcon = '';
      if (queryLower.includes('rsa') || queryLower.includes('pkcs') || queryLower.includes('encryption')) {
        technicalDomain = 'CRYPTOGRAPHIC INTEGRATION ISSUE';
        domainIcon = '🔐';
      } else if (queryLower.includes('webhook') || queryLower.includes('callback')) {
        technicalDomain = 'WEBHOOK INTEGRATION ISSUE';
        domainIcon = '🔗';
      } else if (queryLower.includes('upi') || queryLower.includes('payment')) {
        technicalDomain = 'PAYMENT PROCESSING ISSUE';
        domainIcon = '💳';
      } else if (queryLower.includes('gateway') || queryLower.includes('api')) {
        technicalDomain = 'GATEWAY INTEGRATION ISSUE';
        domainIcon = '🌐';
      } else {
        technicalDomain = 'TECHNICAL ISSUE';
        domainIcon = '⚙️';
      }
      
      // Enhanced match quality detection
      let matchQuality, matchType;
      if (isPerfectMatch) {
        matchQuality = 'PERFECT MATCH';
        matchType = 'EXACT TITLE MATCH';
      } else if (isExactMatch) {
        matchQuality = 'EXACT MATCH';
        matchType = 'PRECISE TECHNICAL MATCH';
      } else if (isHighlyRelevant) {
        matchQuality = 'HIGHLY RELEVANT';
        matchType = 'STRONG SEMANTIC MATCH';
      } else if (isModeratelyRelevant) {
        matchQuality = 'POTENTIALLY RELATED';
        matchType = 'MODERATE SIMILARITY';
      } else if (isLowRelevant) {
        matchQuality = 'LIMITED RELEVANCE';
        matchType = 'WEAK SIMILARITY';
      } else {
        matchQuality = 'WEAK MATCH';
        matchType = 'MINIMAL RELEVANCE';
      }
      
      const priority = isPerfectMatch ? '🎯 P0' :
                      isExactMatch ? '🔥 P0' : 
                      isHighlyRelevant ? '⚠️ P1' : 
                      isModeratelyRelevant ? '📋 P2' : '⚪ P3';
      
      // Build enhanced incident report
      let formattedResponse = '';

      // Header with incident match detection
      formattedResponse += `🚨 **INCIDENT MATCH FOUND** - ${topIncident.id}\n`;
      formattedResponse += `${'━'.repeat(50)}\n\n`;
      
      // ENHANCED SMART CONTEXT DETECTION WITH PRIORITY MATCHING
      const query = ragResult.query.toLowerCase();
      let contextDetection = '';
      
      // Check for priority matching details
      const priorityDetails = topIncident.priority_details || {};
      const priorityMatchType = topIncident.match_type || 'SEMANTIC_MATCH';
      const merchantMatch = priorityDetails.merchant_match;
      const gatewayMatch = priorityDetails.gateway_match;
      
      if (priorityMatchType === 'PERFECT_MERCHANT_GATEWAY_MATCH') {
        // Perfect priority match: same merchant + same gateway
        const merchant = priorityDetails.query_merchant || 'merchant';
        const gateway = priorityDetails.query_gateway || 'gateway';
        contextDetection = `🎯 **PERFECT MATCH**: ${merchant} + ${gateway} Integration`;
      } else if (priorityMatchType === 'MERCHANT_ID_MATCH') {
        // High priority: same merchant
        const merchant = priorityDetails.query_merchant || 'merchant';
        contextDetection = `🏆 **MERCHANT MATCH**: ${merchant} - Same Merchant Integration`;
      } else if (priorityMatchType === 'PAYMENT_GATEWAY_MATCH') {
        // Medium priority: same gateway
        const gateway = priorityDetails.query_gateway || 'gateway';
        contextDetection = `🥈 **GATEWAY MATCH**: ${gateway} - Same Payment Gateway`;
      } else if (isPerfectMatch || isExactMatch) {
        // For perfect/exact matches, show specific technical domain
        if (technicalDomain === 'CRYPTOGRAPHIC INTEGRATION ISSUE') {
          contextDetection = `${domainIcon} **PERFECT MATCH FOUND**: ${technicalDomain}`;
        } else if (query.includes('snapdeal') && query.includes('pinelabs')) {
          contextDetection = '🎯 **PERFECT MATCH**: Snapdeal + Pinelabs RSA Decryption Issue';
        } else if (query.includes('webhook') && query.includes('ssl')) {
          contextDetection = '🔗 **PERFECT MATCH**: Webhook SSL Certificate Issue';
        } else {
          contextDetection = `🎯 **PERFECT MATCH**: ${technicalDomain}`;
        }
      } else if (isHighlyRelevant) {
        // For highly relevant matches, show pattern detection
        if (query.includes('payment') && query.includes('gateway')) {
          contextDetection = '🌐 **PATTERN MATCH**: Payment Gateway Integration Issue';
        } else if (query.includes('upi') && query.includes('timeout')) {
          contextDetection = '💳 **PATTERN MATCH**: UPI Payment Timeout Issue';
        } else {
          contextDetection = `${domainIcon} **PATTERN MATCH**: ${technicalDomain}`;
        }
      } else {
        // For lower relevance, show generic match
        contextDetection = `${domainIcon} **INCIDENT MATCH**: ${technicalDomain}`;
      }
      
      formattedResponse += `${contextDetection}\n`;
      formattedResponse += `📊 **Confidence**: ${(confidence * 100).toFixed(0)}% | **Match Type**: ${matchType}\n`;
      formattedResponse += `⚡ **Impact**: ${priority} - ${isPerfectMatch || isExactMatch ? 'Production Blocking' : isHighlyRelevant ? 'Service Degradation' : 'Minor Impact'}\n\n`;

      // Problem Summary Section with Beautiful Numbered List Formatting
      formattedResponse += `📋 **PROBLEM SUMMARY**\n`;
      if (topIncident.description) {
        const description = topIncident.description;
        
        // Check if description contains numbered lists (1), 2), 3) etc.)
        const numberedListPattern = /(\d+\)\s*[^,]+(?:,\s*\d+\)\s*[^,]+)*)/g;
        const numberedMatches = description.match(numberedListPattern);
        
        if (numberedMatches && numberedMatches.length > 0) {
          // Extract and format numbered items beautifully
          const numberedText = numberedMatches[0];
          
          // Split on numbered patterns and clean up
          const numberedItems = numberedText.split(/(?=\d+\))/).filter(item => item.trim().length > 0);
          
          numberedItems.forEach(item => {
            const cleanItem = item.trim().replace(/,$/, '').replace(/\s+/g, ' ');
            if (cleanItem.length > 0 && /^\d+\)/.test(cleanItem)) {
              formattedResponse += `${cleanItem}\n`;
            }
          });
          
          // Add any remaining non-numbered content
          const remainingText = description.replace(numberedListPattern, '').trim();
          if (remainingText.length > 0) {
            const remainingLines = remainingText.split(/[.!?]+/).filter(line => line.trim().length > 0);
            remainingLines.slice(0, 2).forEach(line => {
              const trimmedLine = line.trim();
              if (trimmedLine.length > 0 && !trimmedLine.match(/^\d+\)/)) {
                formattedResponse += `→ ${trimmedLine}\n`;
              }
            });
          }
        } else {
          // Fallback to original formatting for non-numbered descriptions
          const descriptionLines = description.split(/[.!?]+/).filter(line => line.trim().length > 0);
          descriptionLines.slice(0, 4).forEach(line => {
            const trimmedLine = line.trim();
            if (trimmedLine.length > 0) {
              formattedResponse += `→ ${trimmedLine}\n`;
            }
          });
        }
      }
      formattedResponse += `\n`;

      // AI-Generated Immediate Fix
      formattedResponse += `🔧 **IMMEDIATE FIX** (AI-Generated)\n`;
      formattedResponse += `💡 ${ragResult.generated_answer.replace('Fix Suggestion: ', '')}\n\n`;

      // Enhanced Step-by-step Resolution with Better Parsing
      if (topIncident.resolution) {
        formattedResponse += `🛠️ **STEP-BY-STEP RESOLUTION**\n`;
        
        const resolution = topIncident.resolution;
        
        // Check if resolution already contains numbered steps
        const hasNumberedSteps = /\d+\)\s/.test(resolution);
        
        if (hasNumberedSteps) {
          // Parse existing numbered format (1), 2), 3) etc.)
          const numberedSteps = resolution.split(/(?=\d+\))/).filter(step => step.trim().length > 0);
          
          numberedSteps.forEach(step => {
            const cleanStep = step.trim().replace(/,$/, '').replace(/\s+/g, ' ');
            if (cleanStep.length > 0 && /^\d+\)/.test(cleanStep)) {
              formattedResponse += `${cleanStep}\n`;
            }
          });
        } else {
          // Parse paragraph-style resolution into logical steps
          const sentences = resolution.split(/[.!?]+/).filter(line => line.trim().length > 0);
          
          // Group related sentences and create logical steps
          const logicalSteps = [];
          let currentStep = '';
          
          sentences.forEach(sentence => {
            const trimmedSentence = sentence.trim();
            if (trimmedSentence.length === 0) return;
            
            // Check if this sentence starts a new action/step
            const startsNewStep = /^(Issue|Root cause|Recommended|Suggested|Resolution|Fixed|Implemented|Updated|Added|Created|Established|Coordinated|Identified|Investigation|Development|Configuration|Solution|Fix|Changes|Deployment)/i.test(trimmedSentence);
            
            if (startsNewStep && currentStep.length > 0) {
              // Save previous step and start new one
              logicalSteps.push(currentStep.trim());
              currentStep = trimmedSentence;
            } else if (startsNewStep) {
              // Start first step
              currentStep = trimmedSentence;
            } else {
              // Continue current step
              currentStep += (currentStep.length > 0 ? '. ' : '') + trimmedSentence;
            }
          });
          
          // Add the last step
          if (currentStep.length > 0) {
            logicalSteps.push(currentStep.trim());
          }
          
          // Format as numbered steps
          logicalSteps.slice(0, 6).forEach((step, index) => {
            if (step.length > 0) {
              formattedResponse += `${index + 1}. ${step}\n`;
            }
          });
        }
        
        formattedResponse += `\n`;
      }

      // Expert Contact Information
      if (topIncident.resolved_by) {
        formattedResponse += `👨‍💻 **EXPERT CONTACT**\n`;
        const resolverEmail = topIncident.resolved_by.includes('@') ? 
          topIncident.resolved_by : `${topIncident.resolved_by}@juspay.in`;
        formattedResponse += `📧 ${resolverEmail} (Original Resolver)\n`;
        formattedResponse += `📅 Resolved: ${topIncident.created_at}\n\n`;
      }

      // Tags Section
      if (topIncident.tags && topIncident.tags.length > 0) {
        formattedResponse += `🏷️ **TAGS**: ${topIncident.tags.map(tag => `\`${tag}\``).join(' • ')}\n\n`;
      }

      // Impact Metrics
      formattedResponse += `📈 **IMPACT METRICS**\n`;
      const estimatedSavings = isHighlyRelevant ? '2 hours → 15 minutes' : isModeratelyRelevant ? '1 hour → 30 minutes' : '45 minutes → 20 minutes';
      formattedResponse += `• Resolution Time: ${estimatedSavings} (with this knowledge)\n`;
      formattedResponse += `• Similar Issues Prevented: ${isHighlyRelevant ? '5+' : '2-3'} future incidents\n`;
      formattedResponse += `• Team Efficiency: ${isHighlyRelevant ? '90%' : '70%'} faster debugging\n\n`;

      // Related Incidents (if multiple results)
      if (ragResult.retrieved_incidents.length > 1) {
        formattedResponse += `🔗 **RELATED INCIDENTS**\n`;
        ragResult.retrieved_incidents.slice(1, 3).forEach((incident, index) => {
          const score = incident.fused_score || incident.score || 0;
          formattedResponse += `${index + 2}. **${incident.id}** - ${incident.title.substring(0, 50)}${incident.title.length > 50 ? '...' : ''}\n`;
          formattedResponse += `   📊 Similarity: ${(score * 100).toFixed(0)}% | 🏷️ ${incident.tags?.slice(0, 3).join(', ') || 'No tags'}\n`;
        });
        formattedResponse += `\n`;
      }

      // Performance Footer
      formattedResponse += `---\n`;
      formattedResponse += `⚡ *Search completed in ${executionTime.toFixed(0)}ms using ${ragResult.rag_strategy} • Powered by SherlockAI AI*`;

      return {
        content: formattedResponse,
        results: ragResult.retrieved_incidents
      };
    }

    // Handle legacy hybrid search format (fallback)
    if (response.total_results === 0) {
      return {
        content: `🔍 **NO MATCHING INCIDENTS FOUND**\n\n❌ I couldn't find any similar issues in our knowledge base for "${response.query}". This might be a new type of issue.\n\n**📋 Next Steps:**\n→ Check if this is a known issue in recent documentation\n→ Consider reaching out to the team that owns the affected service\n→ Document this issue for future reference once resolved\n\n---\n*Search completed in ${response.execution_time_ms?.toFixed(0)}ms using ${response.search_type} search*`,
        results: []
      };
    }

    // Legacy format - shouldn't be used anymore but kept for compatibility
    return {
      content: "Legacy search format detected. Please use RAG endpoint.",
      results: response.results || []
    };
  };

  const isGreeting = (text: string): boolean => {
    const greetings = ['hi', 'hii', 'hello', 'hey', 'hola', 'good morning', 'good afternoon', 'good evening'];
    const normalizedText = text.toLowerCase().trim();
    
    // Check if it's ONLY a greeting (not a greeting followed by technical content)
    const isOnlyGreeting = greetings.some(greeting => 
      normalizedText === greeting || 
      normalizedText === greeting + '!' ||
      normalizedText === greeting + '.'
    );
    
    // If it starts with a greeting but has technical keywords, treat as technical
    const hasTechnicalContent = normalizedText.includes('error') || 
                               normalizedText.includes('issue') || 
                               normalizedText.includes('problem') ||
                               normalizedText.includes('failed') ||
                               normalizedText.includes('timeout') ||
                               normalizedText.includes('gateway') ||
                               normalizedText.includes('api') ||
                               normalizedText.includes('payment') ||
                               normalizedText.includes('debug') ||
                               normalizedText.includes('help me') ||
                               normalizedText.includes('solve') ||
                               normalizedText.includes('merchant') ||
                               normalizedText.includes('integration') ||
                               normalizedText.includes('integrating') ||
                               normalizedText.includes('blocked') ||
                               normalizedText.includes('testing') ||
                               normalizedText.includes('server_error') ||
                               normalizedText.includes('internal_server_error') ||
                               normalizedText.includes('pinelabs') ||
                               normalizedText.includes('snapdeal') ||
                               normalizedText.includes('/txns') ||
                               normalizedText.includes('logs');
    
    // Debug logging
    console.log('isGreeting Debug:', {
      text: text.substring(0, 50) + '...',
      isOnlyGreeting,
      hasTechnicalContent,
      result: isOnlyGreeting && !hasTechnicalContent
    });
    
    return isOnlyGreeting && !hasTechnicalContent;
  };

  const isCapabilityQuery = (text: string): boolean => {
    const capabilityKeywords = [
      'what can you', 'what do you', 'what are you', 'what type', 'what kind',
      'capabilities', 'help with', 'solve', 'fix', 'support', 'handle',
      'what issues', 'what problems', 'show me', 'list', 'types of'
    ];
    
    const normalizedText = text.toLowerCase();
    return capabilityKeywords.some(keyword => normalizedText.includes(keyword));
  };

  const isIncidentID = (text: string): boolean => {
    // FIXED: Check if text CONTAINS an incident ID, not just exact match
    const idPatterns = [
      /\bJSP-\d+\b/i,           // JSP-1046 anywhere in text
      /\bJIRA-\d+\b/i,          // JIRA-1234 anywhere in text
      /\bINC-\d+\b/i,           // INC-5678 anywhere in text
      /\bSLACK-\d+-\d+\b/i,     // SLACK-timestamp-id anywhere in text
      /\bTICKET-\d+\b/i,        // TICKET-1234 anywhere in text
      /\bBUG-\d+\b/i,           // BUG-5678 anywhere in text
      /\bISSUE-\d+\b/i          // ISSUE-9999 anywhere in text
    ];
    
    const trimmedText = text.trim();
    return idPatterns.some(pattern => pattern.test(trimmedText));
  };

  const extractIncidentID = (text: string): string | null => {
    // Extract the actual incident ID from text
    const idPatterns = [
      /\b(JSP-\d+)\b/i,
      /\b(JIRA-\d+)\b/i,
      /\b(INC-\d+)\b/i,
      /\b(SLACK-\d+-\d+)\b/i,
      /\b(TICKET-\d+)\b/i,
      /\b(BUG-\d+)\b/i,
      /\b(ISSUE-\d+)\b/i
    ];
    
    for (const pattern of idPatterns) {
      const match = text.match(pattern);
      if (match) {
        return match[1];
      }
    }
    
    return null;
  };

  const isTechnicalQuery = (text: string): boolean => {
    // First check if it's an incident ID - these are always technical
    if (isIncidentID(text)) {
      return true;
    }
    
    const technicalKeywords = [
      'error', 'failed', 'failure', 'timeout', 'api', 'database', 'server', 'connection',
      'payment', 'upi', 'webhook', 'authentication', 'authorization', 'ssl', 'tls',
      'bug', 'issue', 'problem', 'broken', 'not working', 'crash', 'exception',
      'latency', 'performance', 'slow', 'down', 'outage', 'service', 'endpoint',
      'response', 'request', 'http', 'https', 'json', 'xml', 'sql', 'query',
      'deploy', 'deployment', 'build', 'compile', 'config', 'configuration',
      // Payment gateway and transaction specific terms
      'gateway', 'transaction', 'transactions', 'pg', 'hyper', 'authorizing', 'stuck',
      'processing', 'pending', 'declined', 'refund', 'settlement', 'capture', 'void',
      'merchant', 'order', 'status', 'sync', 'callback', 'notification', 'integration',
      'pinelabs', 'razorpay', 'payu', 'billdesk', 'ccavenue', 'easebuzz', 'cybersource',
      'hdfc', 'axis', 'icici', 'sbi', 'kotak', 'card', 'debit', 'credit', 'netbanking',
      'wallet', 'mobikwik', 'paytm', 'phonepe', 'gpay', 'amazonpay', 'freecharge'
    ];
    
    const normalizedText = text.toLowerCase();
    return technicalKeywords.some(keyword => normalizedText.includes(keyword));
  };

  const generateGreetingResponse = (): string => {
    const responses = [
      "👋 Hello! I'm SherlockAI, your AI-powered technical support assistant. I'm here to help you find solutions to technical issues based on our historical knowledge base.",
      "Hi there! 😊 I'm SherlockAI. I can help you troubleshoot technical problems by searching through past incidents and providing AI-powered solutions.",
      "Hey! 👋 I'm SherlockAI, ready to help you solve technical issues. Just describe any problem you're facing!"
    ];
    
    const randomResponse = responses[Math.floor(Math.random() * responses.length)];
    
    return `${randomResponse}\n\n**What I can help with:**\n• API errors and timeouts\n• Payment gateway issues\n• Database connection problems\n• Authentication failures\n• Performance issues\n• Deployment problems\n• And much more!\n\n**Example queries:**\n• "UPI payment failed with error 5003"\n• "Database connection timeout"\n• "API returning 500 error"\n• "Webhook not receiving callbacks"\n\nWhat technical issue can I help you with today?`;
  };

  const generateNonTechnicalResponse = (query: string): string => {
    return `I understand you said "${query}", but I'm specifically designed to help with **technical issues and troubleshooting**.\n\n**I can help you with:**\n• API errors and failures\n• Payment processing issues\n• Database problems\n• Authentication issues\n• Performance and timeout problems\n• Deployment and configuration issues\n\n**Try asking something like:**\n• "Payment API is returning timeout errors"\n• "Database connection keeps failing"\n• "UPI transactions are not processing"\n• "Webhook callbacks are not working"\n\nWhat technical problem can I help you solve? 🔧`;
  };

  const formatCapabilities = (capabilities: any): string => {
    if (!capabilities || !capabilities.categories) {
      return generateCapabilitiesResponse();
    }

    let response = `🔧 **SherlockAI Capabilities**\n\nI'm your AI-powered technical support assistant with access to ${capabilities.total_issues || 'multiple'} historical issues in our knowledge base.\n\n`;

    // Format each category
    Object.entries(capabilities.categories).forEach(([category, data]: [string, any]) => {
      response += `## 🏷️ **${category.charAt(0).toUpperCase() + category.slice(1)}**\n`;
      response += `**Issues in database:** ${data.count}\n`;
      
      if (data.examples && data.examples.length > 0) {
        response += `**Example issues:**\n`;
        data.examples.forEach((example: string, index: number) => {
          response += `• ${example}\n`;
        });
      }
      response += `\n`;
    });

    response += `## 🚀 **How I Help**\n`;
    response += `• **Semantic Search:** I understand the context and meaning of your queries\n`;
    response += `• **Historical Knowledge:** I search through past resolved incidents\n`;
    response += `• **AI-Powered Suggestions:** I generate actionable fix recommendations\n`;
    response += `• **Smart Routing:** I handle different types of queries appropriately\n\n`;

    response += `## 💡 **Example Queries**\n`;
    response += `• "UPI payment failed with error 5003"\n`;
    response += `• "Database connection timeout after 30 seconds"\n`;
    response += `• "API returning 500 internal server error"\n`;
    response += `• "Webhook not receiving callbacks from payment gateway"\n`;
    response += `• "SSL certificate validation failed"\n\n`;

    response += `**What technical issue can I help you solve today?** 🔍`;

    return response;
  };

  const generateCapabilitiesResponse = (): string => {
    return `🔧 **SherlockAI Capabilities**\n\nI'm your AI-powered technical support assistant designed to help you solve technical issues quickly and efficiently.\n\n## 🏷️ **Issue Categories I Handle**\n\n**Payment & Financial:**\n• UPI payment failures\n• Payment gateway timeouts\n• Transaction processing errors\n• Webhook callback issues\n• Settlement problems\n\n**API & Integration:**\n• API timeout errors\n• HTTP status code issues\n• Authentication failures\n• Rate limiting problems\n• Third-party integration issues\n\n**Database & Storage:**\n• Connection timeouts\n• Query performance issues\n• Data consistency problems\n• Migration failures\n• Backup/restore issues\n\n**Infrastructure & DevOps:**\n• Deployment failures\n• Configuration errors\n• SSL/TLS certificate issues\n• Load balancing problems\n• Monitoring and alerting\n\n**Security & Authentication:**\n• OAuth/JWT token issues\n• Permission and authorization errors\n• Security policy violations\n• Encryption/decryption problems\n• Access control issues\n\n## 🚀 **How I Help**\n• **Semantic Search:** I understand the context and meaning of your queries\n• **Historical Knowledge:** I search through past resolved incidents\n• **AI-Powered Suggestions:** I generate actionable fix recommendations\n• **Smart Routing:** I handle different types of queries appropriately\n\n## 💡 **Example Queries**\n• "UPI payment failed with error 5003"\n• "Database connection timeout after 30 seconds"\n• "API returning 500 internal server error"\n• "Webhook not receiving callbacks from payment gateway"\n• "SSL certificate validation failed"\n\n**What technical issue can I help you solve today?** 🔍`;
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInputValue(value);
    setShowSuggestions(value.length >= 2 && !isLoading);
  };

  const handleInputFocus = () => {
    if (inputValue.length >= 2) {
      setShowSuggestions(true);
    }
  };

  const handleInputBlur = () => {
    // Delay hiding suggestions to allow clicking on them
    setTimeout(() => setShowSuggestions(false), 200);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      setShowSuggestions(false);
      handleSubmit(e);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const handleRetry = () => {
    if (retryCount < 3) {
      setRetryCount(prev => prev + 1);
      checkBackendHealth();
    }
  };

  const handleSubmit = async (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    // Check connection status
    if (connectionStatus === 'offline') {
      const errorMessage: Message = {
        id: 'connection-error-' + Date.now(),
        type: 'assistant',
        content: '🔌 **Connection Error**\n\nI\'m unable to connect to the backend service. Please check:\n• Is the backend server running on port 8000?\n• Are there any network connectivity issues?\n• Try refreshing the page\n\nYou can also try the retry button below.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

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
    const queryText = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    try {
      // Check if it's a greeting
      if (isGreeting(queryText)) {
        const greetingResponse = generateGreetingResponse();
        
        // Remove typing message and add greeting response
        setMessages(prev => {
          const newMessages = prev.filter(msg => !msg.isTyping);
          return [...newMessages, {
            id: (Date.now() + 2).toString(),
            type: 'assistant',
            content: greetingResponse,
            timestamp: new Date(),
          }];
        });
        return;
      }

      // CRITICAL FIX: Check for incident ID FIRST before capability queries
      if (isIncidentID(queryText)) {
        console.log('Incident ID detected:', queryText);
        
        // Show immediate feedback for ID search
        setMessages(prev => {
          const newMessages = prev.filter(msg => !msg.isTyping);
          return [...newMessages, {
            id: (Date.now() + 1.5).toString(),
            type: 'assistant',
            content: `🔍 **Searching for incident ${queryText.toUpperCase()}...**\n\nLooking up exact incident details...`,
            timestamp: new Date(),
            isTyping: true
          }];
        });
        
        // Try exact ID search first with hybrid search (which has better ID matching)
        try {
          const idResponse = await fetch('http://localhost:8000/api/v1/search/hybrid', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: queryText,
              top_k: 5,
              min_score: 0.1  // Lower threshold for ID searches
            }),
          });

          if (idResponse.ok) {
            const idSearchResult = await idResponse.json();
            
            // Check if we found an exact ID match
            const exactMatch = idSearchResult.results?.find((result: SearchResult) => 
              result.id.toLowerCase() === extractIncidentID(queryText)?.toLowerCase()
            );
            
            if (exactMatch) {
              // Format as direct ID result
              const directIdContent = `🎯 **INCIDENT FOUND** - ${exactMatch.id}\n${'━'.repeat(50)}\n\n📋 **${exactMatch.title}**\n\n**Problem Description:**\n${exactMatch.description}\n\n🔧 **Resolution:**\n${exactMatch.resolution}\n\n👨‍💻 **Resolved by:** ${exactMatch.resolved_by || 'Unknown'}\n📅 **Date:** ${exactMatch.created_at}\n\n🏷️ **Tags:** ${exactMatch.tags?.map(tag => `\`${tag}\``).join(' • ') || 'None'}\n\n---\n⚡ *Direct ID lookup completed instantly*`;
              
              // Remove typing message and show direct result
              setMessages(prev => {
                const newMessages = prev.filter(msg => !msg.isTyping);
                return [...newMessages, {
                  id: (Date.now() + 2).toString(),
                  type: 'assistant',
                  content: directIdContent,
                  timestamp: new Date(),
                  searchResults: [exactMatch],
                  searchQuery: queryText
                }];
              });
              
              setConnectionStatus('online');
              setRetryCount(0);
              return;
            }
          }
        } catch (error) {
          console.error('ID search error:', error);
        }
        
        // If exact ID not found, show helpful message and fall through to RAG search
        setMessages(prev => {
          const newMessages = prev.filter(msg => !msg.isTyping);
          return [...newMessages, {
            id: (Date.now() + 1.8).toString(),
            type: 'assistant',
            content: `❌ **Incident ${extractIncidentID(queryText)?.toUpperCase()} not found**\n\nSearching for similar incidents...`,
            timestamp: new Date(),
            isTyping: true
          }];
        });
      }

      // Check if it's a capability query (AFTER ticket ID check)
      if (isCapabilityQuery(queryText) && !isIncidentID(queryText)) {
        try {
          const capResponse = await fetch('http://localhost:8000/api/v1/search/capabilities');
          if (capResponse.ok) {
            const capabilities = await capResponse.json();
            const formattedCapabilities = formatCapabilities(capabilities);
            
            // Remove typing message and add capabilities response
            setMessages(prev => {
              const newMessages = prev.filter(msg => !msg.isTyping);
              return [...newMessages, {
                id: (Date.now() + 2).toString(),
                type: 'assistant',
                content: formattedCapabilities,
                timestamp: new Date(),
              }];
            });
            return;
          }
        } catch (error) {
          console.error('Capabilities fetch error:', error);
        }
        
        // Fallback if capabilities endpoint fails
        const fallbackCapabilities = generateCapabilitiesResponse();
        setMessages(prev => {
          const newMessages = prev.filter(msg => !msg.isTyping);
          return [...newMessages, {
            id: (Date.now() + 2).toString(),
            type: 'assistant',
            content: fallbackCapabilities,
            timestamp: new Date(),
          }];
        });
        return;
      }

      // Check if it's a technical query
      if (!isTechnicalQuery(queryText)) {
        const nonTechnicalResponse = generateNonTechnicalResponse(queryText);
        
        // Remove typing message and add non-technical response
        setMessages(prev => {
          const newMessages = prev.filter(msg => !msg.isTyping);
          return [...newMessages, {
            id: (Date.now() + 2).toString(),
            type: 'assistant',
            content: nonTechnicalResponse,
            timestamp: new Date(),
          }];
        });
        return;
      }

      // Continue with RAG search for non-ID technical queries
      if (!isIncidentID(queryText)) {
        console.log('Incident ID detected:', queryText);
        
        // Show immediate feedback for ID search
        setMessages(prev => {
          const newMessages = prev.filter(msg => !msg.isTyping);
          return [...newMessages, {
            id: (Date.now() + 1.5).toString(),
            type: 'assistant',
            content: `🔍 **Searching for incident ${queryText.toUpperCase()}...**\n\nLooking up exact incident details...`,
            timestamp: new Date(),
            isTyping: true
          }];
        });
        
        // Try exact ID search first with hybrid search (which has better ID matching)
        try {
          const idResponse = await fetch('http://localhost:8000/api/v1/search/hybrid', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: queryText,
              top_k: 5,
              min_score: 0.1  // Lower threshold for ID searches
            }),
          });

          if (idResponse.ok) {
            const idSearchResult = await idResponse.json();
            
            // Check if we found an exact ID match
            const exactMatch = idSearchResult.results?.find((result: SearchResult) => 
              result.id.toLowerCase() === queryText.toLowerCase()
            );
            
            if (exactMatch) {
              // Format as direct ID result
              const directIdContent = `🎯 **INCIDENT FOUND** - ${exactMatch.id}\n${'━'.repeat(50)}\n\n📋 **${exactMatch.title}**\n\n**Problem Description:**\n${exactMatch.description}\n\n🔧 **Resolution:**\n${exactMatch.resolution}\n\n👨‍💻 **Resolved by:** ${exactMatch.resolved_by || 'Unknown'}\n📅 **Date:** ${exactMatch.created_at}\n\n🏷️ **Tags:** ${exactMatch.tags?.map(tag => `\`${tag}\``).join(' • ') || 'None'}\n\n---\n⚡ *Direct ID lookup completed instantly*`;
              
              // Remove typing message and show direct result
              setMessages(prev => {
                const newMessages = prev.filter(msg => !msg.isTyping);
                return [...newMessages, {
                  id: (Date.now() + 2).toString(),
                  type: 'assistant',
                  content: directIdContent,
                  timestamp: new Date(),
                  searchResults: [exactMatch],
                  searchQuery: queryText
                }];
              });
              
              setConnectionStatus('online');
              setRetryCount(0);
              return;
            }
          }
        } catch (error) {
          console.error('ID search error:', error);
        }
        
        // If exact ID not found, show helpful message and fall through to RAG search
        setMessages(prev => {
          const newMessages = prev.filter(msg => !msg.isTyping);
          return [...newMessages, {
            id: (Date.now() + 1.8).toString(),
            type: 'assistant',
            content: `❌ **Incident ${queryText.toUpperCase()} not found**\n\nSearching for similar incidents...`,
            timestamp: new Date(),
            isTyping: true
          }];
        });
      }

      // Proceed with RAG search (Retrieval-Augmented Generation)
      const response = await fetch('http://localhost:8000/api/v1/rag/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: queryText,
          include_sources: true,
          max_incidents: 3,
          confidence_threshold: isIncidentID(queryText) ? 0.1 : 0.3  // Lower threshold for ID searches
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const searchResponse: SearchResponse = await response.json();
      const { content: formattedContent, results } = formatSearchResults(searchResponse);

      // Remove typing message and add actual response
      setMessages(prev => {
        const newMessages = prev.filter(msg => !msg.isTyping);
        return [...newMessages, {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          content: formattedContent,
          timestamp: new Date(),
          searchResults: results,
          searchQuery: queryText
        }];
      });

      // Update connection status to online on successful request
      setConnectionStatus('online');
      setRetryCount(0);

    } catch (error) {
      console.error('Search error:', error);
      
      // Update connection status
      setConnectionStatus('error');
      
      // Remove typing message and add error response
      setMessages(prev => {
        const newMessages = prev.filter(msg => !msg.isTyping);
        return [...newMessages, {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          content: `❌ **Search Error**\n\nI encountered an error while searching for solutions. This could be due to:\n\n• Backend service is temporarily unavailable\n• Network connectivity issues\n• Server overload\n\n**Error details:** ${error instanceof Error ? error.message : 'Unknown error'}\n\n**What you can do:**\n• Try again in a few moments\n• Check if the backend service is running\n• Refresh the page and try again\n\nIf the problem persists, please contact the development team.`,
          timestamp: new Date(),
        }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatMessageContent = (content: string) => {
    // Enhanced markdown-like formatting with better asterisk handling
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
        
        // Handle inline formatting (bold, italic, code)
        let processedLine = line;
        
        // Process inline bold text **text**
        processedLine = processedLine.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Process inline italic text *text* (but not if it's part of **)
        processedLine = processedLine.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
        
        // Process inline code `text`
        processedLine = processedLine.replace(/`([^`]+)`/g, '<code class="message-code">$1</code>');
        
        return (
          <div 
            key={index} 
            className="message-line"
            dangerouslySetInnerHTML={{ __html: processedLine }}
          />
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

  const FeedbackButtons = ({ resultId, searchQuery }: { resultId: string; searchQuery: string }) => {
    const resultFeedback = feedback[resultId];
    
    // Show success state
    if (resultFeedback?.submitted && !resultFeedback?.error) {
      return (
        <div className="feedback-submitted">
          <span className="feedback-thanks">
            ✅ {resultFeedback.helpful ? 'Thanks! Glad this helped.' : 'Thanks for the feedback!'}
          </span>
        </div>
      );
    }

    // Show error state with retry option
    if (resultFeedback?.error) {
      return (
        <div className="feedback-error">
          <span className="feedback-error-text">❌ Failed to submit feedback</span>
          <button
            onClick={() => {
              // Reset error state
              setFeedback(prev => ({
                ...prev,
                [resultId]: {
                  ...prev[resultId],
                  error: false
                }
              }));
            }}
            className="feedback-button retry"
            title="Try again"
          >
            🔄 Retry
          </button>
        </div>
      );
    }

    // Show loading state
    if (resultFeedback?.loading) {
      return (
        <div className="feedback-loading">
          <span className="feedback-label">Submitting feedback...</span>
          <div className="feedback-spinner"></div>
        </div>
      );
    }

    // Show default feedback buttons
    return (
      <div className="feedback-buttons">
        <span className="feedback-label">Was this helpful?</span>
        <button
          onClick={() => submitFeedback(resultId, true, 5, searchQuery)}
          className="feedback-button helpful"
          title="Yes, this was helpful"
          disabled={resultFeedback?.loading}
        >
          👍 Yes
        </button>
        <button
          onClick={() => submitFeedback(resultId, false, 1, searchQuery)}
          className="feedback-button not-helpful"
          title="No, this wasn't helpful"
          disabled={resultFeedback?.loading}
        >
          👎 No
        </button>
      </div>
    );
  };

  const getStatusDisplay = () => {
    switch (connectionStatus) {
      case 'online':
        return { text: '16 Issues Trained', className: 'online' };
      case 'offline':
        return { text: 'Backend Offline', className: 'offline' };
      case 'error':
        return { text: 'Connection Error', className: 'error' };
      default:
        return { text: 'Checking...', className: 'checking' };
    }
  };

  const status = getStatusDisplay();

  // Error boundary component
  if (errorBoundary.hasError) {
    return (
      <div className="error-boundary">
        <div className="error-content">
          <h2>🚨 Something went wrong</h2>
          <p>SherlockAI encountered an unexpected error. Please refresh the page to continue.</p>
          <button 
            onClick={() => window.location.reload()}
            className="error-button"
          >
            Refresh Page
          </button>
          {errorBoundary.error && (
            <details className="error-details">
              <summary>Error Details</summary>
              <pre>{errorBoundary.error.toString()}</pre>
            </details>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div className="header-content">
          <div className="header-title">
            <h1>� SherlockAI</h1>
            <span className="header-subtitle">AI-Powered Payment Issue Intelligence</span>
          </div>
          <div className="header-actions">
            <div className="header-auth">
              {!isAuthLoading && (
                <GoogleAuth
                  onLoginSuccess={handleLoginSuccess}
                  onLogoutSuccess={handleLogoutSuccess}
                  user={user}
                />
              )}
            </div>
            {user && (
              <div className="header-buttons">
                <button 
                  onClick={handleShare}
                  className="header-button share-button"
                  title="Share conversation"
                  disabled={messages.length <= 1}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M18 8C19.6569 8 21 6.65685 21 5C21 3.34315 19.6569 2 18 2C16.3431 2 15 3.34315 15 5C15 5.18438 15.0156 5.36532 15.0455 5.54139L8.95447 9.45861C8.59412 9.16721 8.12353 9 7.6 9H7.4C5.73726 9 4.4 10.3373 4.4 12C4.4 13.6627 5.73726 15 7.4 15H7.6C8.12353 15 8.59412 14.8328 8.95447 14.5414L15.0455 18.4586C15.0156 18.6347 15 18.8156 15 19C15 20.6569 16.3431 22 18 22C19.6569 22 21 20.6569 21 19C21 17.3431 19.6569 16 18 16C17.4765 16 16.9059 16.1672 16.5455 16.4586L10.4545 12.5414C10.4844 12.3653 10.5 12.1844 10.5 12C10.5 11.8156 10.4844 11.6347 10.4545 11.4586L16.5455 7.54139C16.9059 7.83279 17.4765 8 18 8Z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <button 
                  onClick={handleDeleteChat}
                  className="header-button delete-button"
                  title="Delete conversation"
                  disabled={messages.length <= 1}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M3 6H5H21M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19ZM10 11V17M14 11V17"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="modal-overlay">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="delete-confirm-modal"
          >
            <div className="modal-header">
              <h3>🗑️ Delete Conversation</h3>
            </div>
            <div className="modal-content">
              <p>Are you sure you want to delete this conversation? This action cannot be undone.</p>
            </div>
            <div className="modal-actions">
              <button 
                onClick={cancelDeleteChat}
                className="modal-button cancel-button"
              >
                Cancel
              </button>
              <button 
                onClick={confirmDeleteChat}
                className="modal-button delete-button"
              >
                Delete
              </button>
            </div>
          </motion.div>
        </div>
      )}

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
                    {message.type === 'user' ? 'You' : 'SherlockAI'}
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
                    <>
                      {formatMessageContent(message.content)}
                      {message.searchResults && message.searchResults.length > 0 && (
                        <div className="search-results-feedback">
                          <FeedbackButtons 
                            resultId={message.searchResults[0].id} 
                            searchQuery={message.searchQuery || ''} 
                          />
                        </div>
                      )}
                    </>
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
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            placeholder="Describe your issue... (e.g., 'UPI payment failed with timeout error')"
            className="chat-input"
            disabled={isLoading}
            rows={1}
            style={{ resize: 'none', overflow: 'hidden' }}
          />
          <SearchSuggestions
            inputValue={inputValue}
            onSuggestionClick={handleSuggestionClick}
            isVisible={showSuggestions}
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
            💡 Try: "API timeout error", "Database connection failed", "Payment gateway issue" | Press Shift+Enter for new line
          </span>
        </div>
      </form>
    </div>
  );
};

export default App;
