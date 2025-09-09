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
            logger.error(
                "Fix suggestion generation failed",
                error=str(e),
                issue_id=issue_metadata.get("id", "unknown")
            )
            return "Unable to generate fix suggestion at this time."
    
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
