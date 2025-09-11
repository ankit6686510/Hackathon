"""
AI service for embeddings and text generation
"""

import asyncio
import hashlib
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from pinecone import Pinecone
import structlog
import time

from app.config import settings
from app.database import get_redis

logger = structlog.get_logger()


class AIService:
    """Service for AI operations including embeddings and text generation"""
    
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index = self.pc.Index(settings.pinecone_index)
        
        # Model configurations
        self.embed_model = self._normalize_model(
            settings.gemini_embed_model, "text-embedding-004"
        )
        self.chat_model = self._normalize_model(
            settings.gemini_chat_model, "gemini-1.5-flash"
        )
    
    def _normalize_model(self, name: str, default: str) -> str:
        """Normalize model name to include 'models/' prefix"""
        model = name or default
        return model if model.startswith("models/") else f"models/{model}"
    
    def _generate_cache_key(self, text: str, model: str) -> str:
        """Generate cache key for embeddings"""
        content = f"{model}:{text}"
        return f"embedding:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embeddings for text with caching support
        
        Args:
            text: Text to embed
            use_cache: Whether to use Redis cache
            
        Returns:
            List of embedding values
        """
        if use_cache:
            # Try to get from cache first
            cache_key = self._generate_cache_key(text, self.embed_model)
            try:
                redis_client = await get_redis()
                cached_embedding = await redis_client.get(cache_key)
                if cached_embedding:
                    logger.debug("Retrieved embedding from cache", cache_key=cache_key)
                    return json.loads(cached_embedding)
            except Exception as e:
                logger.warning("Cache retrieval failed", error=str(e))
        
        # Generate new embedding
        try:
            start_time = time.time()
            resp = genai.embed_content(model=self.embed_model, content=text)
            embedding = self._extract_embedding(resp)
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(
                "Generated embedding",
                model=self.embed_model,
                text_length=len(text),
                execution_time_ms=execution_time
            )
            
            # Cache the result
            if use_cache:
                try:
                    redis_client = await get_redis()
                    await redis_client.setex(
                        cache_key,
                        settings.cache_ttl_embeddings,
                        json.dumps(embedding)
                    )
                except Exception as e:
                    logger.warning("Cache storage failed", error=str(e))
            
            return embedding
            
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e), text_length=len(text))
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")
    
    def _extract_embedding(self, resp: Any) -> List[float]:
        """Extract embedding values from Gemini response"""
        if isinstance(resp, dict):
            if "embedding" in resp:
                e = resp["embedding"]
                if isinstance(e, dict) and isinstance(e.get("values"), list):
                    return e["values"]
                if isinstance(e, list):
                    return e
            if "embeddings" in resp and resp["embeddings"]:
                first = resp["embeddings"][0]
                if isinstance(first, dict) and isinstance(first.get("values"), list):
                    return first["values"]
        
        if isinstance(resp, list) and resp:
            first = resp[0]
            if isinstance(first, dict):
                if "embedding" in first and isinstance(first["embedding"], dict):
                    vals = first["embedding"].get("values")
                    if isinstance(vals, list):
                        return vals
                if isinstance(first.get("values"), list):
                    return first["values"]
        
        raise RuntimeError("Unexpected embedding response format from Gemini")
    
    async def search_similar_issues(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        similarity_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar issues using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of similar issues with metadata
        """
        try:
            start_time = time.time()
            
            # Prepare query parameters
            query_params = {
                "vector": query_embedding,
                "top_k": top_k,
                "include_metadata": True
            }
            
            # Add filters if provided
            if filters:
                query_params["filter"] = filters
            
            # Execute search
            results = self.index.query(**query_params)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Process results
            matches = getattr(results, "matches", []) or []
            processed_results = []
            
            for match in matches:
                # Handle both dict and object formats
                if isinstance(match, dict):
                    score = match.get("score", 0.0)
                    metadata = match.get("metadata", {})
                    match_id = match.get("id", "")
                else:
                    score = getattr(match, "score", 0.0)
                    metadata = getattr(match, "metadata", {})
                    match_id = getattr(match, "id", "")
                
                # Apply similarity threshold
                if score >= similarity_threshold:
                    processed_results.append({
                        "id": match_id,
                        "score": score,
                        "metadata": metadata
                    })
            
            logger.info(
                "Vector search completed",
                query_dimension=len(query_embedding),
                top_k=top_k,
                results_count=len(processed_results),
                execution_time_ms=execution_time
            )
            
            return processed_results
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise RuntimeError(f"Vector search failed: {str(e)}")
    
    async def generate_fix_suggestion(
        self,
        issue_metadata: Dict[str, Any],
        query: str = ""
    ) -> str:
        """
        Generate AI-powered fix suggestion for an issue
        
        Args:
            issue_metadata: Issue metadata including title, description, resolution
            query: Original search query for context
            
        Returns:
            Generated fix suggestion
        """
        try:
            prompt = self._build_fix_prompt(issue_metadata, query)
            
            start_time = time.time()
            model = genai.GenerativeModel(self.chat_model)
            
            # Configure generation parameters
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 150,
            }
            
            resp = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Extract text from response
            suggestion = self._extract_text_from_response(resp)
            
            logger.info(
                "Generated fix suggestion",
                model=self.chat_model,
                issue_id=issue_metadata.get("id", "unknown"),
                execution_time_ms=execution_time,
                suggestion_length=len(suggestion)
            )
            
            return suggestion
            
        except Exception as e:
            error_str = str(e)
            logger.error(
                "Fix suggestion generation failed",
                error=error_str,
                issue_id=issue_metadata.get("id", "unknown")
            )
            
            # Check if it's a quota/rate limit error
            if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                return self._generate_fallback_suggestion(issue_metadata, query)
            else:
                return "Unable to generate fix suggestion at this time."

    def validate_payment_domain(self, query: str) -> Dict[str, Any]:
        """
        Validate if query is payment domain related
        
        Args:
            query: User's question
            
        Returns:
            Dict with validation result and details
        """
        query_lower = query.lower()
        
        # Payment domain keywords
        payment_keywords = [
            # Core payment terms
            'payment', 'transaction', 'upi', 'card', 'wallet', 'gateway',
            'checkout', 'refund', 'settlement', 'merchant', 'customer',
            
            # Payment methods
            'credit card', 'debit card', 'net banking', 'emi', 'bnpl',
            'qr code', 'nfc', 'contactless', 'tap to pay',
            
            # Banks and payment providers
            'hdfc', 'icici', 'axis', 'sbi', 'kotak', 'yes bank', 'pnb',
            'paytm', 'phonepe', 'gpay', 'amazon pay', 'mobikwik',
            'razorpay', 'stripe', 'paypal', 'cashfree', 'payu',
            'irctc',  # Indian Railway Catering and Tourism Corporation - major payment merchant
            
            # Payment errors and issues
            'timeout', 'failed', 'declined', 'error', 'invalid', 'expired',
            'insufficient funds', 'authentication', 'authorization', '3ds',
            'otp', 'pin', 'cvv', 'fraud', 'risk', 'chargeback',
            
            # Technical payment terms
            'api', 'webhook', 'callback', 'redirect', 'token', 'session',
            'encryption', 'ssl', 'tls', 'pci', 'compliance', 'mandate',
            'recurring', 'subscription', 'autopay', 'standing instruction',
            'ip whitelisting', 'whitelist', 'firewall', 'network', 'integration'
        ]
        
        # Bank codes and error codes
        bank_codes = ['5003', '5004', '5005', 'u30', 'u69', 'z6', 'z9']
        
        # Check for payment keywords
        payment_score = sum(1 for keyword in payment_keywords if keyword in query_lower)
        bank_code_found = any(code in query_lower for code in bank_codes)
        
        # Determine if it's payment related
        is_payment_related = payment_score > 0 or bank_code_found
        
        return {
            "is_payment_related": is_payment_related,
            "payment_score": payment_score,
            "bank_code_found": bank_code_found,
            "confidence": min(payment_score * 0.2, 1.0)  # Max confidence of 1.0
        }

    async def generate_payment_ai_solution(self, query: str) -> str:
        """
        Generate AI solution for payment domain issues only
        
        Args:
            query: Payment-related query
            
        Returns:
            Generated payment solution with disclaimer
        """
        try:
            prompt = f"""You are a senior fintech engineer at Juspay with deep expertise in payment systems, UPI, cards, gateways, and financial technology.

A user is asking about this payment-related issue: "{query}"

Since we don't have historical data for this specific issue, provide a comprehensive payment domain solution.

Requirements:
- Focus ONLY on payment/fintech domain knowledge
- Provide step-by-step troubleshooting for payment issues
- Include relevant payment error codes, bank-specific solutions
- Mention payment gateway configurations, API parameters
- Include monitoring and logging specific to payment systems
- Be practical and actionable for payment engineers
- Keep response under 500 words

Response format:
🤖 AI-Generated Payment Solution:
[Your detailed payment solution here]

⚠️ Note: This is an AI-generated answer based on payment domain knowledge. We are not 100% sure. Please verify with your team and update the system with the actual resolution.

Response:"""
            
            start_time = time.time()
            model = genai.GenerativeModel(self.chat_model)
            
            generation_config = {
                "temperature": 0.3,  # Lower for more precise technical responses
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 600,
            }
            
            resp = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            solution = self._extract_text_from_response(resp)
            
            logger.info(
                "Generated payment AI solution",
                model=self.chat_model,
                query=query,
                execution_time_ms=execution_time,
                solution_length=len(solution)
            )
            
            return solution
            
        except Exception as e:
            logger.error(
                "Payment AI solution generation failed",
                error=str(e),
                query=query
            )
            return """🤖 AI-Generated Payment Solution:
I'm unable to generate a solution at this time due to a technical issue. Please try again later or contact your payment engineering team for assistance.

⚠️ Note: This is an AI-generated answer based on payment domain knowledge. We are not 100% sure. Please verify with your team and update the system with the actual resolution."""

    async def store_pending_issue(self, query: str, ai_solution: str) -> str:
        """
        Store new payment issue for future learning
        
        Args:
            query: Payment issue query
            ai_solution: AI-generated solution
            
        Returns:
            Pending issue ID
        """
        try:
            from app.database import get_database
            from app.models import PendingIssue
            from datetime import datetime
            import uuid
            
            # Generate unique ID
            pending_id = f"PENDING-{uuid.uuid4().hex[:8].upper()}"
            
            # Extract payment metadata
            domain_validation = self.validate_payment_domain(query)
            
            # Create pending issue record
            async with get_database() as db:
                pending_issue = PendingIssue(
                    id=pending_id,
                    query=query,
                    ai_solution=ai_solution,
                    payment_score=domain_validation["payment_score"],
                    confidence_level=domain_validation["confidence"],
                    status="pending_verification",
                    created_at=datetime.utcnow()
                )
                
                db.add(pending_issue)
                await db.commit()
            
            logger.info(
                "Stored pending payment issue",
                pending_id=pending_id,
                query=query[:100],
                payment_score=domain_validation["payment_score"]
            )
            
            return pending_id
            
        except Exception as e:
            logger.error(
                "Failed to store pending issue",
                error=str(e),
                query=query[:100]
            )
            return "PENDING-ERROR"

    async def generate_general_solution(self, query: str) -> str:
        """
        Generate AI-powered general solution when no historical matches are found
        
        Args:
            query: User's technical query
            
        Returns:
            Generated general solution
        """
        try:
            prompt = f"""You are a senior fintech engineer at Juspay with expertise in payment systems, UPI, cards, and financial technology.

A user is asking about: "{query}"

Since we don't have any specific historical incidents matching this query, provide a comprehensive troubleshooting guide and general solution approach.

Requirements:
- Start with "🤖 AI-Generated Solution:"
- Provide step-by-step troubleshooting approach
- Include common causes and solutions
- Mention relevant tools, logs, or monitoring to check
- Be specific to fintech/payment domain when applicable
- Keep it practical and actionable
- End with "Note: This is an AI-generated response as we don't have historical data for this specific issue."

Response:"""
            
            start_time = time.time()
            model = genai.GenerativeModel(self.chat_model)
            
            # Configure generation parameters for more detailed response
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 400,
            }
            
            resp = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Extract text from response
            solution = self._extract_text_from_response(resp)
            
            logger.info(
                "Generated general solution",
                model=self.chat_model,
                query=query,
                execution_time_ms=execution_time,
                solution_length=len(solution)
            )
            
            return solution
            
        except Exception as e:
            logger.error(
                "General solution generation failed",
                error=str(e),
                query=query
            )
            return "🤖 AI-Generated Solution: I'm unable to generate a solution at this time due to a technical issue. Please try again later or contact your technical team for assistance.\n\nNote: This is an AI-generated response as we don't have historical data for this specific issue."

    async def generate_payment_smart_response(self, query: str) -> Dict[str, Any]:
        """
        Generate intelligent response for payment domain queries only
        
        Args:
            query: User's question
            
        Returns:
            Dict with response type, content, and metadata
        """
        try:
            # First validate if it's payment domain related
            domain_validation = self.validate_payment_domain(query)
            
            if not domain_validation["is_payment_related"]:
                return {
                    "type": "domain_rejection",
                    "content": "I specialize in payment-related issues only. Please ask about UPI transactions, payment gateways, card processing, bank integrations, payment errors, or other payment-related topics.\n\nFor general questions, please use other resources or contact your team.",
                    "domain_validation": domain_validation,
                    "has_historical_data": False
                }
            
            # It's payment related - proceed with search
            try:
                # Generate embedding and search for similar payment issues
                query_embedding = await self.embed_text(query)
                similar_issues = await self.search_similar_issues(
                    query_embedding, 
                    top_k=5, 
                    similarity_threshold=0.1  # Very low threshold to ensure we find JSP-1017
                )
                
                if similar_issues:
                    # Found historical payment issues
                    enhanced_results = []
                    for issue in similar_issues:
                        # Extract metadata for fix suggestion
                        metadata = issue.get('metadata', {})
                        if not metadata:
                            # If no metadata, use the issue data directly
                            metadata = issue
                        
                        suggestion = await self.generate_fix_suggestion(metadata, query)
                        issue['ai_suggestion'] = suggestion
                        enhanced_results.append(issue)
                    
                    return {
                        "type": "historical_payment_issues",
                        "content": enhanced_results,
                        "domain_validation": domain_validation,
                        "has_historical_data": True,
                        "confidence_note": "Based on historical payment incidents"
                    }
                else:
                    # No historical data - generate AI payment solution and store for learning
                    ai_solution = await self.generate_payment_ai_solution(query)
                    
                    # Store as pending issue for future learning
                    pending_id = await self.store_pending_issue(query, ai_solution)
                    
                    return {
                        "type": "ai_payment_solution",
                        "content": ai_solution,
                        "domain_validation": domain_validation,
                        "has_historical_data": False,
                        "pending_issue_id": pending_id,
                        "confidence_note": "AI-generated - please verify and update system"
                    }
                    
            except Exception as e:
                logger.error(f"Payment search failed: {e}")
                # Fallback to AI solution without storage
                ai_solution = await self.generate_payment_ai_solution(query)
                return {
                    "type": "ai_payment_solution_fallback",
                    "content": ai_solution,
                    "domain_validation": domain_validation,
                    "has_historical_data": False,
                    "error": str(e),
                    "confidence_note": "AI-generated - please verify and update system"
                }
                
        except Exception as e:
            logger.error(f"Payment smart response failed: {e}")
            return {
                "type": "error",
                "content": "I'm experiencing a technical issue. Please try again later or contact your payment engineering team for assistance.",
                "error": str(e),
                "has_historical_data": False
            }
    
    def _build_fix_prompt(self, metadata: Dict[str, Any], query: str = "") -> str:
        """Build prompt for fix suggestion generation"""
        title = metadata.get("title", "")
        description = metadata.get("description", "")
        resolution = metadata.get("resolution", "")
        tags = metadata.get("tags", [])
        
        prompt = f"""You are a senior fintech engineer at Juspay with expertise in payment systems, UPI, cards, and financial technology.

PAST INCIDENT:
Title: {title}
Description: {description}
Resolution: {resolution}
Tags: {', '.join(tags) if tags else 'None'}

CURRENT QUERY: {query}

Based on this past incident and its successful resolution, provide a concise, actionable fix suggestion for a new engineer facing a similar issue. 

Requirements:
- Start with "Fix Suggestion: "
- Be specific and actionable
- Focus on the most critical steps
- Keep it under 100 words
- Use technical terminology appropriate for Juspay engineers

Fix Suggestion: """
        
        return prompt
    
    def _generate_fallback_suggestion(self, issue_metadata: Dict[str, Any], query: str = "") -> str:
        """
        Generate rule-based fallback suggestion when AI is unavailable
        
        Args:
            issue_metadata: Issue metadata including title, description, resolution
            query: Original search query for context
            
        Returns:
            Rule-based fix suggestion
        """
        try:
            title = issue_metadata.get("title", "")
            description = issue_metadata.get("description", "")
            resolution = issue_metadata.get("resolution", "")
            tags = issue_metadata.get("tags", [])
            
            # Extract key information for rule-based suggestion
            suggestion_parts = []
            
            # Start with a standard prefix
            suggestion_parts.append("Fix Suggestion:")
            
            # Analyze the resolution for key actions
            resolution_lower = resolution.lower()
            
            # Common payment issue patterns and suggestions
            if "timeout" in resolution_lower:
                if "increased" in resolution_lower or "extend" in resolution_lower:
                    suggestion_parts.append("Increase timeout values in your configuration.")
                else:
                    suggestion_parts.append("Check and adjust timeout settings.")
            
            if "retry" in resolution_lower:
                suggestion_parts.append("Implement retry logic with exponential backoff.")
            
            if "config" in resolution_lower or "setting" in resolution_lower:
                suggestion_parts.append("Review and update configuration settings.")
            
            if "api" in resolution_lower:
                suggestion_parts.append("Check API endpoint configuration and parameters.")
            
            if "database" in resolution_lower or "db" in resolution_lower:
                suggestion_parts.append("Verify database connection and query performance.")
            
            if "cache" in resolution_lower:
                suggestion_parts.append("Clear cache and verify cache configuration.")
            
            if "restart" in resolution_lower or "reboot" in resolution_lower:
                suggestion_parts.append("Consider restarting the affected service.")
            
            # UPI/Payment specific patterns
            if any(tag.lower() in ["upi", "payment", "gateway"] for tag in tags):
                if "5003" in resolution or "5003" in description:
                    suggestion_parts.append("For UPI error 5003, check PSP timeout and retry configuration.")
                elif "webhook" in resolution_lower:
                    suggestion_parts.append("Verify webhook URL configuration and callback handling.")
                elif "bank" in resolution_lower:
                    suggestion_parts.append("Check bank-specific API configurations and error handling.")
            
            # If no specific patterns found, provide generic guidance
            if len(suggestion_parts) == 1:  # Only has the prefix
                suggestion_parts.append("Based on the historical resolution:")
                # Extract first sentence of resolution as guidance
                first_sentence = resolution.split('.')[0] if resolution else "Review the resolution details"
                suggestion_parts.append(f"'{first_sentence.strip()}.'")
                suggestion_parts.append("Apply similar steps to your current issue.")
            
            # Add monitoring/verification step
            suggestion_parts.append("Monitor logs and verify the fix resolves the issue.")
            
            # Add disclaimer
            suggestion_parts.append("(AI service temporarily unavailable - rule-based suggestion)")
            
            return " ".join(suggestion_parts)
            
        except Exception as e:
            logger.error("Fallback suggestion generation failed", error=str(e))
            return "Fix Suggestion: Apply the resolution steps from the similar historical issue. Monitor logs to verify the fix. (AI service temporarily unavailable)"
    
    def _extract_text_from_response(self, resp: Any) -> str:
        """Extract text from Gemini response"""
        # Try direct text attribute
        text = getattr(resp, "text", None)
        if text:
            return text.strip()
        
        # Try candidates structure
        if hasattr(resp, "candidates") and resp.candidates:
            candidate = resp.candidates[0]
            if hasattr(candidate, "content"):
                content = candidate.content
                if hasattr(content, "parts") and content.parts:
                    return content.parts[0].text.strip()
        
        return "Unable to generate suggestion."
    
    async def batch_embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        # Process in batches to avoid rate limits
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await asyncio.gather(
                *[self.embed_text(text) for text in batch],
                return_exceptions=True
            )
            
            for embedding in batch_embeddings:
                if isinstance(embedding, Exception):
                    logger.error("Batch embedding failed", error=str(embedding))
                    # Use zero vector as fallback
                    embeddings.append([0.0] * 768)  # Assuming 768-dim embeddings
                else:
                    embeddings.append(embedding)
        
        return embeddings
    
    async def store_embedding(
        self,
        issue_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store embedding in Pinecone vector database
        
        Args:
            issue_id: Unique identifier for the issue
            embedding: Embedding vector
            metadata: Issue metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare vector for upsert
            vector_data = {
                "id": issue_id,
                "values": embedding,
                "metadata": metadata
            }
            
            # Upsert to Pinecone
            self.index.upsert(vectors=[vector_data])
            
            logger.info(
                "Stored embedding in vector database",
                issue_id=issue_id,
                metadata_keys=list(metadata.keys())
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to store embedding",
                error=str(e),
                issue_id=issue_id
            )
            return False
    
    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        similarity_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Pinecone
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of similar vectors with metadata
        """
        try:
            start_time = time.time()
            
            # Prepare query parameters
            query_params = {
                "vector": query_embedding,
                "top_k": top_k,
                "include_metadata": True
            }
            
            # Add filters if provided
            if filters:
                query_params["filter"] = filters
            
            # Execute search
            results = self.index.query(**query_params)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Process results
            matches = getattr(results, "matches", []) or []
            processed_results = []
            
            for match in matches:
                # Handle both dict and object formats
                if isinstance(match, dict):
                    score = match.get("score", 0.0)
                    metadata = match.get("metadata", {})
                    match_id = match.get("id", "")
                else:
                    score = getattr(match, "score", 0.0)
                    metadata = getattr(match, "metadata", {})
                    match_id = getattr(match, "id", "")
                
                # Apply similarity threshold
                if score >= similarity_threshold:
                    result = {
                        "id": match_id,
                        "score": score,
                        "title": metadata.get("title", ""),
                        "description": metadata.get("description", ""),
                        "resolution": metadata.get("resolution", ""),
                        "tags": metadata.get("tags", []),
                        "created_at": metadata.get("created_at", ""),
                        "resolved_by": metadata.get("resolved_by", "")
                    }
                    processed_results.append(result)
            
            logger.info(
                "Vector search completed",
                query_dimension=len(query_embedding),
                top_k=top_k,
                results_count=len(processed_results),
                execution_time_ms=execution_time
            )
            
            return processed_results
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            return []
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "index_fullness": stats.get("index_fullness", 0.0),
                "namespaces": stats.get("namespaces", {})
            }
        except Exception as e:
            logger.error("Failed to get index stats", error=str(e))
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check AI service health"""
        health_status = {
            "gemini_embedding": {"status": "unknown"},
            "gemini_chat": {"status": "unknown"},
            "pinecone": {"status": "unknown"}
        }
        
        # Test Gemini embedding
        try:
            await self.embed_text("health check", use_cache=False)
            health_status["gemini_embedding"] = {"status": "healthy"}
        except Exception as e:
            health_status["gemini_embedding"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Gemini chat
        try:
            model = genai.GenerativeModel(self.chat_model)
            resp = model.generate_content("Say 'OK' for health check")
            health_status["gemini_chat"] = {"status": "healthy"}
        except Exception as e:
            health_status["gemini_chat"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Pinecone
        try:
            stats = self.index.describe_index_stats()
            health_status["pinecone"] = {
                "status": "healthy",
                "total_vectors": stats.get("total_vector_count", 0)
            }
        except Exception as e:
            health_status["pinecone"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        return health_status


# Global AI service instance
ai_service = AIService()
