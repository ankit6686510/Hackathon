"""
RAG (Retrieval-Augmented Generation) Service for SherlockAI
Implements formal RAG pipeline: Retrieval → Augmentation → Generation
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import structlog

from app.services.hybrid_search import hybrid_search_service
from app.services.ai_service import ai_service
from app.config import settings

logger = structlog.get_logger()


class QueryComplexity(Enum):
    """Query complexity classification for adaptive RAG routing"""
    SIMPLE = "simple"      # Single incident lookup (e.g., "UPI timeout")
    COMPLEX = "complex"    # Multi-incident analysis (e.g., "Why do refunds fail?")
    UNKNOWN = "unknown"    # No relevant incidents expected


class RAGResponse:
    """Structured RAG response with sources and metadata"""
    
    def __init__(
        self,
        query: str,
        generated_answer: str,
        retrieved_incidents: List[Dict[str, Any]],
        sources: List[str],
        confidence_score: float,
        query_complexity: QueryComplexity,
        execution_time_ms: float,
        rag_strategy: str
    ):
        self.query = query
        self.generated_answer = generated_answer
        self.retrieved_incidents = retrieved_incidents
        self.sources = sources
        self.confidence_score = confidence_score
        self.query_complexity = query_complexity
        self.execution_time_ms = execution_time_ms
        self.rag_strategy = rag_strategy
        self.timestamp = datetime.utcnow()


class RAGService:
    """
    Enterprise RAG service implementing formal Retrieval-Augmented Generation
    """
    
    def __init__(self):
        self.query_classifier_cache = {}
        
        # RAG configuration
        self.simple_query_top_k = 3
        self.complex_query_top_k = 8
        self.min_confidence_threshold = 0.3
        
        # Prompt templates
        self.simple_prompt_template = self._load_simple_prompt_template()
        self.complex_prompt_template = self._load_complex_prompt_template()
        self.classification_prompt_template = self._load_classification_prompt_template()
    
    def extract_exact_ticket_id(self, query: str) -> Optional[str]:
        """
        Extract exact ticket ID from query text
        
        Args:
            query: Query string to extract ticket ID from
            
        Returns:
            Exact ticket ID if found, None otherwise
        """
        import re
        
        # Ticket ID patterns for exact extraction
        id_patterns = [
            r'\b(JSP-\d+)\b',           # JSP-1046
            r'\b(EUL-\d+)\b',           # EUL-1234  
            r'\b(JIRA-\d+)\b',          # JIRA-1234
            r'\b(INC-\d+)\b',           # INC-5678
            r'\b(SLACK-\d+-\d+)\b',     # SLACK-timestamp-id
            r'\b(TICKET-\d+)\b',        # TICKET-1234
            r'\b(BUG-\d+)\b',           # BUG-5678
            r'\b(ISSUE-\d+)\b'          # ISSUE-9999
        ]
        
        query_clean = query.strip()
        
        for pattern in id_patterns:
            match = re.search(pattern, query_clean, re.IGNORECASE)
            if match:
                ticket_id = match.group(1).upper()
                logger.info(
                    "Exact ticket ID extracted",
                    query=query,
                    extracted_id=ticket_id,
                    pattern=pattern
                )
                return ticket_id
        
        return None

    def is_incident_id(self, query: str) -> bool:
        """
        Check if query contains an incident ID pattern
        
        Args:
            query: Query string to check
            
        Returns:
            True if query contains incident ID patterns
        """
        return self.extract_exact_ticket_id(query) is not None

    async def fetch_exact_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch exact ticket by ID from vector database
        BYPASSES all semantic search - direct ID lookup only
        
        Args:
            ticket_id: Exact ticket ID to fetch
            
        Returns:
            Complete ticket metadata if found, None if not found
        """
        try:
            # Use hybrid search service to access the corpus metadata directly
            if not hybrid_search_service.corpus_metadata:
                logger.warning("No corpus metadata available for exact ticket lookup")
                return None
            
            # Direct search through corpus metadata for exact ID match
            for incident in hybrid_search_service.corpus_metadata:
                if incident.get('id', '').upper() == ticket_id.upper():
                    logger.info(
                        "Exact ticket found by ID",
                        ticket_id=ticket_id,
                        found_id=incident.get('id'),
                        title=incident.get('title', '')[:50]
                    )
                    return incident
            
            logger.info(
                "Exact ticket not found by ID",
                ticket_id=ticket_id,
                searched_count=len(hybrid_search_service.corpus_metadata)
            )
            return None
            
        except Exception as e:
            logger.error(
                "Failed to fetch exact ticket by ID",
                ticket_id=ticket_id,
                error=str(e)
            )
            return None

    async def generate_exact_ticket_summary(self, ticket_data: Dict[str, Any]) -> str:
        """
        Generate 1-2 sentence AI summary using ONLY the provided ticket content
        
        Args:
            ticket_data: Complete ticket metadata
            
        Returns:
            Concise 1-2 sentence summary
        """
        try:
            title = ticket_data.get('title', 'No title')
            description = ticket_data.get('description', 'No description')
            resolution = ticket_data.get('resolution', 'No resolution')
            
            # Create focused prompt for exact ticket summary
            prompt = f"""You are a senior engineer. Summarize this specific ticket in exactly 1-2 sentences using ONLY the provided content. Be concise and technical.

Ticket Title: {title}
Description: {description}
Resolution: {resolution}

Provide a 1-2 sentence summary that captures the core issue and solution:"""

            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Very low for consistency
                    "max_output_tokens": 100,  # Short and focused
                }
            )
            
            summary = response.text.strip()
            
            logger.info(
                "Exact ticket summary generated",
                ticket_id=ticket_data.get('id'),
                summary_length=len(summary)
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "Failed to generate exact ticket summary",
                ticket_id=ticket_data.get('id'),
                error=str(e)
            )
            
            # Fallback to manual summary
            title = ticket_data.get('title', 'Unknown issue')
            resolution = ticket_data.get('resolution', 'No resolution available')
            return f"Issue: {title}. Resolution: {resolution[:100]}{'...' if len(resolution) > 100 else ''}"

    async def process_exact_ticket_query(self, query: str, ticket_id: str) -> RAGResponse:
        """
        Process exact ticket ID query - BYPASSES semantic search completely
        
        Args:
            query: Original user query
            ticket_id: Extracted ticket ID
            
        Returns:
            RAGResponse with exact ticket data or "not found" message
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Processing exact ticket query",
                query=query,
                ticket_id=ticket_id,
                bypass_semantic_search=True
            )
            
            # Fetch exact ticket by ID
            ticket_data = await self.fetch_exact_ticket_by_id(ticket_id)
            
            if not ticket_data:
                # Ticket not found - return clear message
                execution_time_ms = (time.time() - start_time) * 1000
                
                not_found_message = f"🔍 **Ticket Not Found**\n\n❌ Ticket `{ticket_id}` was not found in the knowledge base.\n\n**Possible reasons:**\n• Ticket ID may be incorrect\n• Ticket not yet indexed in the system\n• Ticket may be from a different system\n\n**What you can do:**\n• Double-check the ticket ID\n• Try searching with keywords from the issue\n• Contact the team that created the ticket"
                
                return RAGResponse(
                    query=query,
                    generated_answer=not_found_message,
                    retrieved_incidents=[],
                    sources=[],
                    confidence_score=1.0,  # High confidence in "not found"
                    query_complexity=QueryComplexity.SIMPLE,
                    execution_time_ms=execution_time_ms,
                    rag_strategy="exact_id_not_found"
                )
            
            # Generate AI summary using ONLY this ticket's content
            ai_summary = await self.generate_exact_ticket_summary(ticket_data)
            
            # Format exact ticket response
            exact_response = f"""🎯 **EXACT TICKET FOUND** - {ticket_data.get('id', 'Unknown')}
${'━' * 50}

📋 **{ticket_data.get('title', 'No title')}**

🤖 **AI Summary:** {ai_summary}

**📝 Full Description:**
{ticket_data.get('description', 'No description available')}

**🔧 Resolution:**
{ticket_data.get('resolution', 'No resolution available')}

**👨‍💻 Resolved by:** {ticket_data.get('resolved_by', 'Unknown')}
**📅 Date:** {ticket_data.get('created_at', 'Unknown')}
**🏷️ Tags:** {', '.join([f'`{tag}`' for tag in ticket_data.get('tags', [])]) or 'None'}

---
⚡ *Exact ID lookup completed in {(time.time() - start_time) * 1000:.0f}ms • Match Type: EXACT_ID • Confidence: 100%*"""

            execution_time_ms = (time.time() - start_time) * 1000
            
            # Format ticket data for retrieved_incidents
            formatted_ticket = ticket_data.copy()
            formatted_ticket['ai_suggestion'] = ai_summary
            formatted_ticket['score'] = 1.0
            formatted_ticket['fused_score'] = 1.0
            formatted_ticket['match_type'] = 'EXACT_ID'
            formatted_ticket['search_type'] = 'exact_id_lookup'
            
            response = RAGResponse(
                query=query,
                generated_answer=exact_response,
                retrieved_incidents=[formatted_ticket],
                sources=[f"[EXACT] {ticket_data.get('id', 'Unknown')} - {ticket_data.get('title', 'No title')[:60]}"],
                confidence_score=1.0,  # Perfect confidence for exact match
                query_complexity=QueryComplexity.SIMPLE,
                execution_time_ms=execution_time_ms,
                rag_strategy="exact_id_lookup"
            )
            
            logger.info(
                "Exact ticket query completed successfully",
                query=query,
                ticket_id=ticket_id,
                found=True,
                execution_time_ms=execution_time_ms
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Exact ticket query failed",
                query=query,
                ticket_id=ticket_id,
                error=str(e)
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return RAGResponse(
                query=query,
                generated_answer=f"❌ **Error fetching ticket {ticket_id}**\n\nAn error occurred while looking up the exact ticket: {str(e)}",
                retrieved_incidents=[],
                sources=[],
                confidence_score=0.0,
                query_complexity=QueryComplexity.UNKNOWN,
                execution_time_ms=execution_time_ms,
                rag_strategy="exact_id_error"
            )
    
    def is_payment_domain_query(self, query: str) -> bool:
        """
        Check if query is related to payment domain
        
        Args:
            query: Query string to check
            
        Returns:
            True if query is payment-related or is an incident ID
        """
        # CRITICAL FIX: Always allow incident IDs
        if self.is_incident_id(query):
            logger.info(
                "Query allowed - Incident ID detected",
                query=query,
                reason="incident_id_bypass"
            )
            return True
        
        # Check for payment domain keywords
        payment_keywords = [
            'payment', 'upi', 'gateway', 'transaction', 'card', 'wallet',
            'bank', 'refund', 'settlement', 'webhook', 'api', 'integration',
            'timeout', 'error', 'failure', 'processing', 'authorization',
            'authentication', 'merchant', 'pinelabs', 'payu', 'razorpay',
            'hdfc', 'axis', 'icici', 'sbi', 'kotak', 'visa', 'mastercard',
            'mobikwik', 'paytm', 'phonepe', 'gpay', 'amazonpay'
        ]
        
        query_lower = query.lower()
        is_payment_related = any(keyword in query_lower for keyword in payment_keywords)
        
        logger.info(
            "Payment domain check",
            query=query,
            is_payment_related=is_payment_related,
            is_incident_id=False
        )
        
        return is_payment_related
    
    def _load_simple_prompt_template(self) -> str:
        """Load prompt template for simple queries"""
        return """You are SherlockAI, a Senior AI Engineer at Juspay specializing in payment systems.
Your job: Use the provided context to generate a concise, actionable fix suggestion.

USER QUERY:
{query}

CONTEXT (Past Incidents):
{context}

INSTRUCTIONS:
- Generate a 1-sentence fix starting with "Fix Suggestion: "
- Base your answer ONLY on the provided context
- If context is not relevant, say "No relevant past incidents found for this specific issue."
- NEVER hallucinate or make up information
- Prioritize incidents with higher similarity scores and matching tags

Fix Suggestion:"""

    def _load_complex_prompt_template(self) -> str:
        """Load prompt template for complex queries"""
        return """You are SherlockAI, a Senior AI Engineer at Juspay with deep expertise in payment systems.
Your job: Analyze multiple past incidents to provide comprehensive troubleshooting guidance.

USER QUERY:
{query}

CONTEXT (Multiple Past Incidents):
{context}

INSTRUCTIONS:
- Provide a structured analysis based on the incidents above
- Include: 1) Root cause patterns, 2) Step-by-step resolution, 3) Prevention measures
- Base your answer ONLY on the provided context
- If no clear patterns emerge, focus on the most relevant incident
- NEVER hallucinate or make up information
- Format as: "Analysis: [root cause] | Resolution: [steps] | Prevention: [measures]"

Analysis:"""

    def _load_classification_prompt_template(self) -> str:
        """Load prompt template for query classification"""
        return """Classify this technical query for RAG routing:

QUERY: "{query}"

CLASSIFICATION OPTIONS:
- simple: Can be answered with 1-2 specific incidents (e.g., "UPI timeout error 5003", "Card tokenization failing")
- complex: Needs analysis of multiple incidents or patterns (e.g., "Why do refunds fail?", "Root cause of payment timeouts")
- unknown: Likely no relevant incidents in payment domain (e.g., "How to deploy service?", "Database schema design")

EXAMPLES:
- "UPI payment failed with error 5003" → simple
- "Webhook delivery keeps failing" → simple  
- "What causes most payment failures?" → complex
- "How to optimize payment success rates?" → complex
- "How to set up monitoring?" → unknown

Answer only with: simple, complex, or unknown"""

    async def classify_query_complexity(self, query: str) -> QueryComplexity:
        """
        Classify query complexity for adaptive RAG routing
        
        Args:
            query: User's question
            
        Returns:
            QueryComplexity enum value
        """
        # Check cache first
        cache_key = query.lower().strip()
        if cache_key in self.query_classifier_cache:
            return self.query_classifier_cache[cache_key]
        
        try:
            # Use lightweight model for classification
            prompt = self.classification_prompt_template.format(query=query)
            
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 10,
                }
            )
            
            classification = response.text.strip().lower()
            
            # Map to enum
            if "simple" in classification:
                complexity = QueryComplexity.SIMPLE
            elif "complex" in classification:
                complexity = QueryComplexity.COMPLEX
            else:
                complexity = QueryComplexity.UNKNOWN
            
            # Cache result
            self.query_classifier_cache[cache_key] = complexity
            
            logger.info(
                "Query classified",
                query=query,
                complexity=complexity.value,
                raw_classification=classification
            )
            
            return complexity
            
        except Exception as e:
            logger.error("Query classification failed", error=str(e), query=query)
            # Default to simple for safety
            return QueryComplexity.SIMPLE

    def _build_context_from_incidents(
        self, 
        incidents: List[Dict[str, Any]], 
        query_complexity: QueryComplexity
    ) -> str:
        """
        Build context string from retrieved incidents
        
        Args:
            incidents: List of retrieved incidents
            query_complexity: Complexity level for formatting
            
        Returns:
            Formatted context string
        """
        if not incidents:
            return "No relevant incidents found."
        
        context_blocks = []
        
        for i, incident in enumerate(incidents, 1):
            # Extract error patterns if available
            error_patterns = []
            if 'error_patterns' in incident:
                for pattern in incident['error_patterns']:
                    code = pattern.get('code', '')
                    message = pattern.get('message', '')
                    if code or message:
                        error_patterns.append(f"{code} {message}".strip())
            
            # Build incident block
            block = f"""INCIDENT {i}:
ID: {incident.get('id', 'Unknown')}
Title: {incident.get('title', 'No title')}
Description: {incident.get('description', 'No description')}
Resolution: {incident.get('resolution', 'No resolution')}
Tags: {', '.join(incident.get('tags', []))}
Similarity Score: {incident.get('fused_score', incident.get('score', 0)):.3f}"""

            if error_patterns:
                block += f"\nError Patterns: {', '.join(error_patterns)}"
            
            if 'search_methods' in incident:
                block += f"\nFound by: {', '.join(incident['search_methods'])}"
            
            context_blocks.append(block)
        
        separator = "\n" + "-" * 50 + "\n"
        return separator.join(context_blocks)

    def _calculate_confidence_score(
        self, 
        incidents: List[Dict[str, Any]], 
        query_complexity: QueryComplexity
    ) -> float:
        """
        Calculate confidence score for the RAG response
        
        Args:
            incidents: Retrieved incidents
            query_complexity: Query complexity level
            
        Returns:
            Confidence score between 0 and 1
        """
        if not incidents:
            return 0.0
        
        # Base confidence on top result score
        top_score = incidents[0].get('fused_score', incidents[0].get('score', 0))
        
        # Adjust based on query complexity
        if query_complexity == QueryComplexity.SIMPLE:
            # Simple queries need high similarity
            confidence = min(top_score * 1.2, 1.0)
        elif query_complexity == QueryComplexity.COMPLEX:
            # Complex queries benefit from multiple incidents
            avg_score = sum(inc.get('fused_score', inc.get('score', 0)) for inc in incidents[:3]) / min(3, len(incidents))
            confidence = min(avg_score * 1.1, 1.0)
        else:
            # Unknown queries get lower confidence
            confidence = min(top_score * 0.8, 1.0)
        
        # Boost confidence if multiple search methods found the same result
        if incidents[0].get('method_count', 1) > 1:
            confidence = min(confidence * 1.1, 1.0)
        
        return confidence

    def _validate_semantic_relevance(self, query: str, incidents: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        REVOLUTIONARY SEMANTIC VALIDATION - Sam Altman Style
        
        This is not just validation - it's INTELLIGENT DOMAIN UNDERSTANDING
        
        Args:
            query: Original user query
            incidents: Retrieved incidents
            
        Returns:
            Tuple of (is_relevant, reason_for_decision)
        """
        if not incidents:
            return False, "no_incidents_retrieved"
        
        try:
            query_lower = query.lower()
            
            # STEP 1: DOMAIN INTELLIGENCE - What is the user ACTUALLY asking about?
            query_domain = self._extract_query_domain(query_lower)
            query_entities = self._extract_query_entities(query_lower)
            query_intent = self._extract_query_intent(query_lower)
            
            logger.info(
                "Query Intelligence Analysis",
                query=query[:100],
                domain=query_domain,
                entities=query_entities,
                intent=query_intent
            )
            
            # STEP 2: INCIDENT INTELLIGENCE - What do our incidents ACTUALLY cover?
            best_match_score = 0
            best_match_reason = "no_semantic_overlap"
            
            for incident in incidents:
                incident_text = f"{incident.get('title', '')} {incident.get('description', '')} {' '.join(incident.get('tags', []))}".lower()
                
                # Domain compatibility check
                incident_domain = self._extract_query_domain(incident_text)
                domain_match = self._calculate_domain_compatibility(query_domain, incident_domain)
                
                # Entity overlap check
                incident_entities = self._extract_query_entities(incident_text)
                entity_overlap = len(query_entities.intersection(incident_entities)) / max(len(query_entities), 1)
                
                # Intent alignment check
                incident_intent = self._extract_query_intent(incident_text)
                intent_alignment = 1.0 if query_intent == incident_intent else 0.3
                
                # Calculate composite relevance score
                composite_score = (domain_match * 0.5) + (entity_overlap * 0.3) + (intent_alignment * 0.2)
                
                logger.info(
                    "Incident Intelligence Analysis",
                    incident_id=incident.get('id'),
                    incident_domain=incident_domain,
                    incident_entities=list(incident_entities),
                    domain_match=domain_match,
                    entity_overlap=entity_overlap,
                    intent_alignment=intent_alignment,
                    composite_score=composite_score
                )
                
                if composite_score > best_match_score:
                    best_match_score = composite_score
                    if composite_score >= 0.6:
                        best_match_reason = "high_semantic_relevance"
                    elif composite_score >= 0.4:
                        best_match_reason = "moderate_semantic_relevance"
                    elif composite_score >= 0.2:
                        best_match_reason = "weak_semantic_relevance"
                    else:
                        best_match_reason = "no_semantic_relevance"
            
            # STEP 3: INTELLIGENT DECISION MAKING
            # This is where we separate good AI from great AI
            
            # CRITICAL FIX: If hybrid search found high-scoring matches, trust them
            # Check if any incident has a high hybrid search score
            max_hybrid_score = 0
            for incident in incidents:
                hybrid_score = incident.get('fused_score', incident.get('score', 0))
                if hybrid_score > max_hybrid_score:
                    max_hybrid_score = hybrid_score
            
            # If hybrid search found a very high scoring match, trust it
            if max_hybrid_score >= 0.8:
                logger.info(
                    "HIGH HYBRID SEARCH SCORE - TRUSTING MATCH",
                    query=query[:50],
                    max_hybrid_score=max_hybrid_score,
                    semantic_score=best_match_score,
                    reason="high_hybrid_confidence"
                )
                return True, "high_hybrid_confidence"
            
            # High confidence: Strong domain + entity match
            if best_match_score >= 0.6:
                logger.info(
                    "HIGH RELEVANCE DETECTED",
                    query=query[:50],
                    best_score=best_match_score,
                    reason=best_match_reason
                )
                return True, best_match_reason
            
            # Medium confidence: Some overlap but not strong
            elif best_match_score >= 0.3:
                logger.info(
                    "MODERATE RELEVANCE DETECTED",
                    query=query[:50],
                    best_score=best_match_score,
                    reason=best_match_reason
                )
                return True, best_match_reason
            
            # RELAXED THRESHOLD: If hybrid search found decent matches, be more lenient
            elif max_hybrid_score >= 0.5 and best_match_score >= 0.1:
                logger.info(
                    "HYBRID SEARCH CONFIDENCE - ACCEPTING MATCH",
                    query=query[:50],
                    hybrid_score=max_hybrid_score,
                    semantic_score=best_match_score,
                    reason="hybrid_search_confidence"
                )
                return True, "hybrid_search_confidence"
            
            # Low confidence: Reject and be honest
            else:
                logger.info(
                    "INSUFFICIENT RELEVANCE - REJECTING MATCH",
                    query=query[:50],
                    best_score=best_match_score,
                    max_hybrid_score=max_hybrid_score,
                    reason="insufficient_semantic_overlap",
                    message="Being honest about lack of relevance"
                )
                return False, "insufficient_semantic_overlap"
            
        except Exception as e:
            logger.error("Semantic validation failed", error=str(e))
            return False, "validation_error"

    def _extract_query_domain(self, text: str) -> str:
        """Extract the primary domain from query text"""
        if any(term in text for term in ['wallet', 'mobikwik', 'paytm', 'phonepe_wallet', 'amazonpay']):
            return 'wallet'
        elif any(term in text for term in ['card', 'visa', 'mastercard', 'debit', 'credit', 'tokenization']):
            return 'card'
        elif any(term in text for term in ['upi', 'bhim', 'gpay', 'phonepe_upi']):
            return 'upi'
        elif any(term in text for term in ['webhook', 'callback', 'notification']):
            return 'webhook'
        elif any(term in text for term in ['gateway', 'api', 'integration']):
            return 'gateway'
        else:
            return 'general'

    def _extract_query_entities(self, text: str) -> set:
        """Extract specific entities (merchants, gateways, banks) from text"""
        entities = set()
        text_lower = text.lower()
        
        # Merchants
        merchants = ['snapdeal', 'firstcry', 'mobikwik', 'citymall', 'flipkart', 'amazon']
        for merchant in merchants:
            if merchant in text_lower:
                entities.add(merchant)
        
        # Gateways
        gateways = ['pinelabs', 'payu', 'razorpay', 'checkout', 'stripe']
        for gateway in gateways:
            if gateway in text_lower:
                entities.add(gateway)
        
        # Banks
        banks = ['hdfc', 'axis', 'icici', 'sbi', 'kotak']
        for bank in banks:
            if bank in text_lower:
                entities.add(bank)
        
        # CRITICAL: Extract exact technical terms and error codes
        exact_terms = [
            'messagenotrecognized', 'pkcs15', 'rsa', 'ssl', 'tls',
            'internal_server_error', 'timeout', 'webhook', 'callback',
            'tokenization', 'encryption', 'decryption', 'signature',
            'authentication', 'authorization', 'validation'
        ]
        for term in exact_terms:
            if term in text_lower:
                entities.add(term)
        
        return entities

    def _extract_exact_technical_terms(self, text: str) -> set:
        """Extract exact technical terms that must match precisely"""
        exact_terms = set()
        text_lower = text.lower()
        
        # Error codes (must match exactly)
        error_codes = [
            'messagenotrecognized', 'transienterror', 'invalidrequest',
            'authenticationfailed', 'insufficientfunds', 'cardexpired',
            'invalidcvv', 'invalidpin', 'cardblocked', 'limitexceeded'
        ]
        
        # Technical standards
        tech_standards = [
            'pkcs15', 'pkcs1', 'rsa', 'aes', 'sha256', 'hmac',
            'jwt', 'oauth', 'ssl', 'tls', 'x509'
        ]
        
        # Gateway-specific terms
        gateway_terms = [
            'pinelabs-online', 'checkout', 'razorpay', 'payu',
            'amazonpay', 'phonepe', 'gpay', 'paytm'
        ]
        
        all_exact_terms = error_codes + tech_standards + gateway_terms
        
        for term in all_exact_terms:
            if term in text_lower:
                exact_terms.add(term)
        
        return exact_terms

    def _calculate_exact_match_boost(self, query: str, incident: Dict[str, Any]) -> float:
        """Calculate boost score for exact technical term matches"""
        query_exact_terms = self._extract_exact_technical_terms(query)
        
        # Check incident title, description, and tags
        incident_text = f"{incident.get('title', '')} {incident.get('description', '')} {' '.join(incident.get('tags', []))}"
        incident_exact_terms = self._extract_exact_technical_terms(incident_text)
        
        if not query_exact_terms:
            return 1.0  # No boost if no exact terms in query
        
        # Calculate exact match ratio
        exact_matches = query_exact_terms.intersection(incident_exact_terms)
        exact_match_ratio = len(exact_matches) / len(query_exact_terms)
        
        # Massive boost for exact matches
        if exact_match_ratio >= 0.8:  # 80%+ exact terms match
            boost = 10.0
        elif exact_match_ratio >= 0.6:  # 60%+ exact terms match
            boost = 5.0
        elif exact_match_ratio >= 0.4:  # 40%+ exact terms match
            boost = 2.0
        elif exact_match_ratio >= 0.2:  # 20%+ exact terms match
            boost = 1.5
        else:
            boost = 1.0  # No boost
        
        logger.info(
            "Exact match boost calculation",
            incident_id=incident.get('id'),
            query_exact_terms=list(query_exact_terms),
            incident_exact_terms=list(incident_exact_terms),
            exact_matches=list(exact_matches),
            exact_match_ratio=exact_match_ratio,
            boost_factor=boost
        )
        
        return boost

    def _filter_by_tags(self, query: str, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter incidents by matching tags for precision"""
        if not incidents:
            return incidents
        
        # Extract key entities from query
        query_entities = self._extract_query_entities(query)
        query_exact_terms = self._extract_exact_technical_terms(query)
        
        # Combine all query terms for filtering
        all_query_terms = query_entities.union(query_exact_terms)
        
        if not all_query_terms:
            return incidents  # No filtering if no key terms found
        
        # Score each incident by tag relevance
        scored_incidents = []
        
        for incident in incidents:
            incident_tags = [tag.lower() for tag in incident.get('tags', [])]
            
            # Calculate tag match score
            tag_matches = 0
            for term in all_query_terms:
                for tag in incident_tags:
                    if term in tag or tag in term:
                        tag_matches += 1
                        break
            
            tag_match_ratio = tag_matches / max(len(all_query_terms), 1)
            
            # Keep incidents with at least some tag relevance
            if tag_match_ratio > 0 or len(incident_tags) == 0:  # Keep untagged incidents too
                incident_copy = incident.copy()
                incident_copy['tag_match_score'] = tag_match_ratio
                scored_incidents.append(incident_copy)
                
                logger.info(
                    "Tag filtering",
                    incident_id=incident.get('id'),
                    incident_tags=incident_tags,
                    query_terms=list(all_query_terms),
                    tag_matches=tag_matches,
                    tag_match_ratio=tag_match_ratio
                )
        
        # Sort by tag relevance (but don't filter out completely)
        scored_incidents.sort(key=lambda x: x.get('tag_match_score', 0), reverse=True)
        
        logger.info(
            "Tag filtering completed",
            original_count=len(incidents),
            filtered_count=len(scored_incidents),
            query_terms=list(all_query_terms)
        )
        
        return scored_incidents

    def _extract_query_intent(self, text: str) -> str:
        """Extract the primary intent from query text"""
        if any(term in text for term in ['failed', 'failing', 'error', 'timeout', 'blocked']):
            return 'troubleshooting'
        elif any(term in text for term in ['integrate', 'integration', 'setup', 'configure']):
            return 'integration'
        elif any(term in text for term in ['test', 'testing', 'sandbox', 'debug']):
            return 'testing'
        else:
            return 'general'

    def _calculate_domain_compatibility(self, query_domain: str, incident_domain: str) -> float:
        """Calculate how compatible two domains are"""
        if query_domain == incident_domain:
            return 1.0
        
        # Some domains are related
        related_domains = {
            'wallet': ['gateway', 'general'],
            'card': ['gateway', 'general'],
            'upi': ['gateway', 'general'],
            'webhook': ['gateway', 'general'],
            'gateway': ['wallet', 'card', 'upi', 'webhook', 'general']
        }
        
        if incident_domain in related_domains.get(query_domain, []):
            return 0.5
        
        return 0.1  # Very low compatibility for unrelated domains

    def _rerank_incidents_by_relevance(self, query: str, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank incidents by semantic relevance to the query
        
        Args:
            query: Original user query
            incidents: Retrieved incidents
            
        Returns:
            Reranked incidents with most relevant first
        """
        if not incidents:
            return incidents
        
        try:
            query_lower = query.lower()
            query_terms = set(query_lower.split())
            
            # Score each incident for relevance
            scored_incidents = []
            
            for incident in incidents:
                incident_text = f"{incident.get('title', '')} {incident.get('description', '')} {' '.join(incident.get('tags', []))}".lower()
                incident_terms = set(incident_text.split())
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(query_terms, incident_terms, query_lower, incident_text)
                
                # Boost score if it's a direct match
                original_score = incident.get('fused_score', incident.get('score', 0))
                
                # If highly relevant, boost the score significantly
                if relevance_score > 0.8:
                    boosted_score = min(original_score * 1.5, 1.0)
                elif relevance_score > 0.5:
                    boosted_score = min(original_score * 1.2, 1.0)
                else:
                    boosted_score = original_score
                
                incident_copy = incident.copy()
                incident_copy['relevance_score'] = relevance_score
                incident_copy['boosted_score'] = boosted_score
                scored_incidents.append(incident_copy)
                
                logger.info(
                    "Incident relevance scoring",
                    incident_id=incident.get('id'),
                    original_score=original_score,
                    relevance_score=relevance_score,
                    boosted_score=boosted_score
                )
            
            # Sort by boosted score (relevance-adjusted)
            scored_incidents.sort(key=lambda x: x['boosted_score'], reverse=True)
            
            return scored_incidents
            
        except Exception as e:
            logger.error("Incident reranking failed", error=str(e))
            return incidents

    def _calculate_relevance_score(self, query_terms: set, incident_terms: set, query_text: str, incident_text: str) -> float:
        """
        Calculate semantic relevance score between query and incident
        
        Args:
            query_terms: Set of query terms
            incident_terms: Set of incident terms
            query_text: Full query text
            incident_text: Full incident text
            
        Returns:
            Relevance score between 0 and 1
        """
        try:
            # Step 1: Check for domain compatibility (CRITICAL FIX)
            domain_penalty = self._calculate_domain_penalty(query_text, incident_text)
            
            # Step 2: Check for exact entity matches (high weight)
            entity_matches = 0
            entities = ['snapdeal', 'pinelabs', 'firstcry', 'mobikwik', 'payu', 'razorpay', 'citymall']
            
            for entity in entities:
                if entity in query_text and entity in incident_text:
                    entity_matches += 1
            
            # Step 3: Check for technical term matches
            tech_terms = ['gateway', 'api', 'error', 'timeout', 'payment', 'transaction', 'integration', 'wallet', 'flow']
            tech_matches = 0
            
            for term in tech_terms:
                if term in query_text and term in incident_text:
                    tech_matches += 1
            
            # Step 4: Check for specific error patterns
            error_patterns = ['internal_server_error', 'server_error', '500', 'rsa', 'decryption', 'encryption', 'invalid_data']
            error_matches = 0
            
            for pattern in error_patterns:
                if pattern in query_text and pattern in incident_text:
                    error_matches += 1
            
            # Step 5: Calculate weighted score
            entity_weight = 0.6  # Increased weight for entity matches
            tech_weight = 0.25
            error_weight = 0.15
            
            max_entities = len([e for e in entities if e in query_text])
            max_tech = len([t for t in tech_terms if t in query_text])
            max_errors = len([p for p in error_patterns if p in query_text])
            
            entity_score = (entity_matches / max(max_entities, 1)) if max_entities > 0 else 0
            tech_score = (tech_matches / max(max_tech, 1)) if max_tech > 0 else 0
            error_score = (error_matches / max(max_errors, 1)) if max_errors > 0 else 0
            
            base_score = (entity_score * entity_weight + 
                         tech_score * tech_weight + 
                         error_score * error_weight)
            
            # Step 6: Apply domain penalty (CRITICAL FIX)
            final_score = base_score * (1 - domain_penalty)
            
            logger.info(
                "Relevance calculation details",
                entity_matches=entity_matches,
                tech_matches=tech_matches,
                error_matches=error_matches,
                base_score=base_score,
                domain_penalty=domain_penalty,
                final_score=final_score
            )
            
            return min(final_score, 1.0)
            
        except Exception as e:
            logger.error("Relevance score calculation failed", error=str(e))
            return 0.0

    def _calculate_domain_penalty(self, query_text: str, incident_text: str) -> float:
        """
        Calculate penalty for domain mismatches (wallet vs card vs UPI)
        
        Args:
            query_text: Query text
            incident_text: Incident text
            
        Returns:
            Penalty score between 0 and 1 (0 = no penalty, 1 = maximum penalty)
        """
        try:
            # Define payment domains
            wallet_terms = ['wallet', 'mobikwik', 'paytm', 'phonepe', 'amazonpay', 'freecharge']
            card_terms = ['card', 'visa', 'mastercard', 'rupay', 'amex', 'debit', 'credit']
            upi_terms = ['upi', 'bhim', 'gpay', 'phonepe_upi']
            
            # Detect domains in query and incident
            query_domains = set()
            incident_domains = set()
            
            query_lower = query_text.lower()
            incident_lower = incident_text.lower()
            
            # Check wallet domain
            if any(term in query_lower for term in wallet_terms):
                query_domains.add('wallet')
            if any(term in incident_lower for term in wallet_terms):
                incident_domains.add('wallet')
                
            # Check card domain
            if any(term in query_lower for term in card_terms):
                query_domains.add('card')
            if any(term in incident_lower for term in card_terms):
                incident_domains.add('card')
                
            # Check UPI domain
            if any(term in query_lower for term in upi_terms):
                query_domains.add('upi')
            if any(term in incident_lower for term in upi_terms):
                incident_domains.add('upi')
            
            # Calculate penalty
            if not query_domains or not incident_domains:
                # If we can't detect domains, apply small penalty
                return 0.1
            
            # If domains don't overlap, apply heavy penalty
            if not query_domains.intersection(incident_domains):
                logger.info(
                    "Domain mismatch detected",
                    query_domains=list(query_domains),
                    incident_domains=list(incident_domains),
                    penalty=0.7
                )
                return 0.7  # Heavy penalty for domain mismatch
            
            # If domains match, no penalty
            return 0.0
            
        except Exception as e:
            logger.error("Domain penalty calculation failed", error=str(e))
            return 0.1  # Small penalty on error

    def _check_incident_relevance(self, query_terms: set, incident_terms: set) -> bool:
        """
        Check if a single incident is relevant to the query terms
        
        Args:
            query_terms: Set of query terms
            incident_terms: Set of incident terms
            
        Returns:
            True if incident is relevant
        """
        try:
            # Check for domain/technology overlap
            payment_domains = {
                'upi', 'card', 'wallet', 'bank', 'payment', 'gateway', 'transaction',
                'refund', 'settlement', 'webhook', 'api', 'integration', 'timeout',
                'error', 'failure', 'processing', 'authorization', 'authentication'
            }
            
            # Check if query and incident share payment domain terms
            query_payment_terms = query_terms.intersection(payment_domains)
            incident_payment_terms = incident_terms.intersection(payment_domains)
            
            if not query_payment_terms or not incident_payment_terms:
                # If either has no payment terms, check for any term overlap
                common_terms = query_terms.intersection(incident_terms)
                return len(common_terms) >= 2  # At least 2 common terms
            
            # Check for specific technology/service overlap
            specific_services = {
                'mobikwik', 'payu', 'hdfc', 'axis', 'icici', 'sbi', 'kotak',
                'pinelabs', 'razorpay', 'paytm', 'phonepe', 'gpay', 'amazonpay',
                'visa', 'mastercard', 'rupay', 'amex', 'jcb', 'diners'
            }
            
            query_services = query_terms.intersection(specific_services)
            incident_services = incident_terms.intersection(specific_services)
            
            # If query mentions specific services, incident should too
            if query_services and not incident_services:
                return False
            
            # Check for common meaningful terms (not just stop words)
            meaningful_overlap = query_terms.intersection(incident_terms)
            meaningful_overlap = meaningful_overlap - {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
            
            return len(meaningful_overlap) >= 2
            
        except Exception as e:
            logger.error("Incident relevance check failed", error=str(e))
            # If validation fails, be conservative and allow the match
            return True

    def _generate_no_results_response(self, query: str, query_complexity: QueryComplexity) -> str:
        """
        Generate helpful "no results found" response
        
        Args:
            query: Original user query
            query_complexity: Query complexity level
            
        Returns:
            Helpful no results response
        """
        # Extract key terms from query for suggestions
        query_lower = query.lower()
        key_terms = []
        
        # Extract important terms (not common words)
        words = query_lower.split()
        important_words = [w for w in words if len(w) > 3 and w not in {'with', 'from', 'that', 'this', 'have', 'been', 'were', 'they', 'there', 'where', 'when', 'what', 'which', 'would', 'could', 'should'}]
        key_terms = important_words[:5]  # Top 5 key terms
        
        response = f"""🔍 **No Relevant Historical Incidents Found**

❌ I couldn't find any past incidents closely related to your specific issue:
"{query}"

💡 **This appears to be a new type of issue** not well-covered in our current knowledge base.

🚀 **Recommended Next Steps:**
• Contact the relevant integration team directly
• Check official API documentation for the services mentioned
• Review your dashboard/configuration settings
• Search internal documentation or Slack channels
• Escalate to the team that owns the affected service

📝 **Keywords for future searches:** {', '.join(key_terms) if key_terms else 'payment, integration, error'}

🔄 **Help us improve:** Once this issue is resolved, please document the solution so future engineers can benefit from your experience.

---
*This honest "no results" response helps maintain trust by not forcing irrelevant matches.*"""

        return response

    def _extract_sources(self, incidents: List[Dict[str, Any]]) -> List[str]:
        """
        Extract source citations from incidents
        
        Args:
            incidents: Retrieved incidents
            
        Returns:
            List of source citations
        """
        sources = []
        for incident in incidents:
            incident_id = incident.get('id', 'Unknown')
            title = incident.get('title', 'No title')
            score = incident.get('fused_score', incident.get('score', 0))
            
            source = f"[{incident_id}] {title[:60]}{'...' if len(title) > 60 else ''} (Score: {score:.3f})"
            sources.append(source)
        
        return sources

    async def retrieve_incidents(
        self, 
        query: str, 
        query_complexity: QueryComplexity
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant incidents based on query complexity
        
        Args:
            query: User's question
            query_complexity: Classified complexity level
            
        Returns:
            List of retrieved incidents
        """
        # Determine retrieval parameters based on complexity
        if query_complexity == QueryComplexity.SIMPLE:
            top_k = self.simple_query_top_k
            min_score = 0.2
        elif query_complexity == QueryComplexity.COMPLEX:
            top_k = self.complex_query_top_k
            min_score = 0.15
        else:  # UNKNOWN
            top_k = self.simple_query_top_k
            min_score = 0.3
        
        # Use hybrid search for retrieval
        incidents = await hybrid_search_service.hybrid_search(
            query=query,
            top_k=top_k,
            min_score=min_score
        )
        
        logger.info(
            "Incidents retrieved",
            query=query,
            complexity=query_complexity.value,
            retrieved_count=len(incidents),
            top_score=incidents[0].get('fused_score', 0) if incidents else 0
        )
        
        return incidents

    async def generate_rag_response(
        self, 
        query: str, 
        incidents: List[Dict[str, Any]], 
        query_complexity: QueryComplexity
    ) -> str:
        """
        Generate response using retrieved incidents as context
        
        Args:
            query: User's question
            incidents: Retrieved incidents
            query_complexity: Query complexity level
            
        Returns:
            Generated response
        """
        # Build context
        context = self._build_context_from_incidents(incidents, query_complexity)
        
        # Select prompt template based on complexity
        if query_complexity == QueryComplexity.COMPLEX:
            prompt = self.complex_prompt_template.format(query=query, context=context)
        else:
            prompt = self.simple_prompt_template.format(query=query, context=context)
        
        try:
            # Generate response
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for consistency
                    "max_output_tokens": 200 if query_complexity == QueryComplexity.SIMPLE else 400,
                }
            )
            
            generated_text = response.text.strip()
            
            logger.info(
                "RAG response generated",
                query=query,
                complexity=query_complexity.value,
                response_length=len(generated_text),
                context_incidents=len(incidents)
            )
            
            return generated_text
            
        except Exception as e:
            logger.error("RAG generation failed", error=str(e), query=query)
            
            # Fallback to rule-based response
            if incidents:
                top_incident = incidents[0]
                return f"Fix Suggestion: Based on incident {top_incident.get('id', 'Unknown')}, try: {top_incident.get('resolution', 'No resolution available')[:100]}..."
            else:
                return "No relevant past incidents found for this specific issue. Please consult your team or documentation."

    async def process_rag_query(self, query: str) -> RAGResponse:
        """
        Main RAG pipeline: Retrieval → Augmentation → Generation
        
        Args:
            query: User's question
            
        Returns:
            RAGResponse with generated answer and metadata
        """
        start_time = time.time()
        
        try:
            # STEP 0: EXACT TICKET ID DETECTION - BYPASS SEMANTIC SEARCH
            ticket_id = self.extract_exact_ticket_id(query)
            if ticket_id:
                logger.info(
                    "EXACT TICKET ID DETECTED - BYPASSING SEMANTIC SEARCH",
                    query=query,
                    ticket_id=ticket_id,
                    bypass_semantic=True
                )
                return await self.process_exact_ticket_query(query, ticket_id)
            
            # Step 1: Query Classification (Routing)
            query_complexity = await self.classify_query_complexity(query)
            
            # Step 2: Retrieval
            incidents = await self.retrieve_incidents(query, query_complexity)
            
            # Step 3: PRECISION-GUIDED FILTERING AND BOOSTING
            if incidents:
                # Apply tag-based filtering for precision
                incidents = self._filter_by_tags(query, incidents)
                
                # Apply exact match boosting
                for incident in incidents:
                    exact_boost = self._calculate_exact_match_boost(query, incident)
                    original_score = incident.get('fused_score', incident.get('score', 0))
                    boosted_score = min(original_score * exact_boost, 1.0)
                    incident['exact_match_boost'] = exact_boost
                    incident['precision_boosted_score'] = boosted_score
                
                # Re-sort by precision-boosted scores
                incidents.sort(key=lambda x: x.get('precision_boosted_score', 0), reverse=True)
                
                # Rerank by semantic relevance
                incidents = self._rerank_incidents_by_relevance(query, incidents)
            
            # Step 4: Semantic Relevance Validation (REVOLUTIONARY APPROACH)
            is_relevant, relevance_reason = self._validate_semantic_relevance(query, incidents)
            
            # Step 5: Check if we should return "no results" response
            if not incidents or not is_relevant:
                logger.info(
                    "No relevant incidents found - BEING HONEST",
                    query=query,
                    incidents_count=len(incidents),
                    semantic_relevance=is_relevant,
                    relevance_reason=relevance_reason,
                    reason="no_incidents" if not incidents else "not_semantically_relevant"
                )
                
                # Generate helpful "no results" response
                no_results_answer = self._generate_no_results_response(query, query_complexity)
                execution_time_ms = (time.time() - start_time) * 1000
                
                return RAGResponse(
                    query=query,
                    generated_answer=no_results_answer,
                    retrieved_incidents=[],
                    sources=[],
                    confidence_score=0.0,
                    query_complexity=query_complexity,
                    execution_time_ms=execution_time_ms,
                    rag_strategy="no_relevant_results"
                )
            
            # Step 5: Check confidence threshold for weak matches
            confidence_score = self._calculate_confidence_score(incidents, query_complexity)
            
            # If confidence is too low, return "no results" instead of weak match
            if confidence_score < 0.4:  # Adjusted threshold for better recall
                logger.info(
                    "Low confidence match rejected",
                    query=query,
                    confidence=confidence_score,
                    top_incident_id=incidents[0].get('id', 'unknown') if incidents else None
                )
                
                no_results_answer = self._generate_no_results_response(query, query_complexity)
                execution_time_ms = (time.time() - start_time) * 1000
                
                return RAGResponse(
                    query=query,
                    generated_answer=no_results_answer,
                    retrieved_incidents=[],
                    sources=[],
                    confidence_score=confidence_score,
                    query_complexity=query_complexity,
                    execution_time_ms=execution_time_ms,
                    rag_strategy="low_confidence_rejected"
                )
            
            # Step 6: Generate response for good matches
            generated_answer = await self.generate_rag_response(query, incidents, query_complexity)
            
            # Step 7: Post-processing
            sources = self._extract_sources(incidents)
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Determine RAG strategy used
            rag_strategy = f"{query_complexity.value}_query_with_{len(incidents)}_incidents"
            
            response = RAGResponse(
                query=query,
                generated_answer=generated_answer,
                retrieved_incidents=incidents,
                sources=sources,
                confidence_score=confidence_score,
                query_complexity=query_complexity,
                execution_time_ms=execution_time_ms,
                rag_strategy=rag_strategy
            )
            
            logger.info(
                "RAG pipeline completed successfully",
                query=query,
                complexity=query_complexity.value,
                incidents_count=len(incidents),
                confidence=confidence_score,
                execution_time_ms=execution_time_ms,
                semantic_relevance=is_relevant
            )
            
            return response
            
        except Exception as e:
            logger.error("RAG pipeline failed", error=str(e), query=query)
            
            # Return error response
            execution_time_ms = (time.time() - start_time) * 1000
            return RAGResponse(
                query=query,
                generated_answer=f"RAG pipeline error: {str(e)}",
                retrieved_incidents=[],
                sources=[],
                confidence_score=0.0,
                query_complexity=QueryComplexity.UNKNOWN,
                execution_time_ms=execution_time_ms,
                rag_strategy="error_fallback"
            )

    async def log_rag_feedback(
        self, 
        query: str, 
        rag_response: RAGResponse, 
        user_feedback: str,
        feedback_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log user feedback for RAG evaluation and learning
        
        Args:
            query: Original query
            rag_response: RAG response that was provided
            user_feedback: "UPVOTE", "DOWNVOTE", or "NEUTRAL"
            feedback_details: Additional feedback metadata
            
        Returns:
            True if logged successfully
        """
        try:
            feedback_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "query": query,
                "rag_strategy": rag_response.rag_strategy,
                "query_complexity": rag_response.query_complexity.value,
                "retrieved_incident_ids": [inc.get('id') for inc in rag_response.retrieved_incidents],
                "generated_answer": rag_response.generated_answer,
                "confidence_score": rag_response.confidence_score,
                "execution_time_ms": rag_response.execution_time_ms,
                "user_feedback": user_feedback,
                "feedback_details": feedback_details or {}
            }
            
            # Store in database (implement based on your DB setup)
            # For now, log to structured logger
            logger.info(
                "RAG feedback logged",
                **feedback_entry
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to log RAG feedback", error=str(e))
            return False

    def get_rag_metrics(self) -> Dict[str, Any]:
        """
        Get RAG performance metrics
        
        Returns:
            Dictionary of RAG metrics
        """
        # This would typically query your feedback database
        # For now, return basic metrics
        return {
            "total_queries_processed": len(self.query_classifier_cache),
            "query_complexity_distribution": {
                "simple": sum(1 for c in self.query_classifier_cache.values() if c == QueryComplexity.SIMPLE),
                "complex": sum(1 for c in self.query_classifier_cache.values() if c == QueryComplexity.COMPLEX),
                "unknown": sum(1 for c in self.query_classifier_cache.values() if c == QueryComplexity.UNKNOWN)
            },
            "cache_hit_rate": len(self.query_classifier_cache) / max(len(self.query_classifier_cache), 1),
            "avg_confidence_threshold": self.min_confidence_threshold
        }


# Global RAG service instance
rag_service = RAGService()
