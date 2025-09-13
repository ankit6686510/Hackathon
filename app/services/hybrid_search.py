"""
Hybrid Search Service: Combines Semantic Search + BM25 Keyword Search
"""

import asyncio
import json
import pickle
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import structlog

from app.services.ai_service import ai_service
from app.config import settings

logger = structlog.get_logger()

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class HybridSearchService:
    """
    Hybrid search service combining semantic search with BM25 keyword search
    """
    
    def __init__(self):
        self.bm25_index = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.corpus_metadata = []
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        
        # Cache file paths
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.bm25_cache_file = self.cache_dir / "bm25_index.pkl"
        self.tfidf_cache_file = self.cache_dir / "tfidf_index.pkl"
        self.metadata_cache_file = self.cache_dir / "corpus_metadata.pkl"
        
        # Search weights for score fusion
        self.semantic_weight = 0.6  # Higher weight for semantic search
        self.bm25_weight = 0.3      # Medium weight for BM25
        self.tfidf_weight = 0.1     # Lower weight for TF-IDF
        
        # Load existing indices if available
        self._load_indices()
    
    def _preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text for BM25 indexing
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            List of processed tokens
        """
        if not text:
            return []
        
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and stem
        processed_tokens = []
        for token in tokens:
            if token not in self.stop_words and len(token) > 2:
                stemmed = self.stemmer.stem(token)
                processed_tokens.append(stemmed)
        
        return processed_tokens
    
    def _create_searchable_text(self, issue: Dict[str, Any]) -> str:
        """
        Create searchable text from issue metadata
        
        Args:
            issue: Issue metadata dictionary
            
        Returns:
            Combined searchable text
        """
        text_parts = []
        
        # Add title (higher weight by repeating)
        title = issue.get('title', '')
        if title:
            text_parts.extend([title] * 3)  # Triple weight for title
        
        # Add description
        description = issue.get('description', '')
        if description:
            text_parts.append(description)
        
        # Add resolution
        resolution = issue.get('resolution', '')
        if resolution:
            text_parts.append(resolution)
        
        # Add tags (higher weight by repeating)
        tags = issue.get('tags', [])
        if tags:
            tag_text = ' '.join(tags)
            text_parts.extend([tag_text] * 2)  # Double weight for tags
        
        # Add resolved_by (for person-specific searches)
        resolved_by = issue.get('resolved_by', '')
        if resolved_by:
            text_parts.append(str(resolved_by))
        
        return ' '.join(text_parts)
    
    async def build_indices(self, issues: List[Dict[str, Any]]) -> bool:
        """
        Build BM25 and TF-IDF indices from issues
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Building hybrid search indices", total_issues=len(issues))
            start_time = time.time()
            
            # Prepare corpus
            corpus = []
            self.corpus_metadata = []
            
            for issue in issues:
                searchable_text = self._create_searchable_text(issue)
                processed_tokens = self._preprocess_text(searchable_text)
                
                if processed_tokens:  # Only add if we have tokens
                    corpus.append(processed_tokens)
                    self.corpus_metadata.append({
                        'id': issue.get('id', ''),
                        'title': issue.get('title', ''),
                        'description': issue.get('description', ''),
                        'resolution': issue.get('resolution', ''),
                        'tags': issue.get('tags', []),
                        'created_at': issue.get('created_at', ''),
                        'resolved_by': issue.get('resolved_by', ''),
                        'searchable_text': searchable_text
                    })
            
            if not corpus:
                logger.error("No valid documents found for indexing")
                return False
            
            # Build BM25 index
            self.bm25_index = BM25Okapi(corpus)
            
            # Build TF-IDF index
            raw_documents = [meta['searchable_text'] for meta in self.corpus_metadata]
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2),  # Include bigrams
                min_df=1,
                max_df=0.95
            )
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(raw_documents)
            
            # Cache the indices
            self._save_indices()
            
            build_time = (time.time() - start_time) * 1000
            logger.info(
                "Hybrid search indices built successfully",
                corpus_size=len(corpus),
                bm25_vocab_size=len(self.bm25_index.doc_freqs),
                tfidf_features=self.tfidf_matrix.shape[1],
                build_time_ms=build_time
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to build hybrid search indices", error=str(e))
            return False
    
    def _save_indices(self):
        """Save indices to cache files"""
        try:
            # Save BM25 index
            with open(self.bm25_cache_file, 'wb') as f:
                pickle.dump(self.bm25_index, f)
            
            # Save TF-IDF components
            tfidf_data = {
                'vectorizer': self.tfidf_vectorizer,
                'matrix': self.tfidf_matrix
            }
            with open(self.tfidf_cache_file, 'wb') as f:
                pickle.dump(tfidf_data, f)
            
            # Save metadata
            with open(self.metadata_cache_file, 'wb') as f:
                pickle.dump(self.corpus_metadata, f)
            
            logger.info("Hybrid search indices cached successfully")
            
        except Exception as e:
            logger.error("Failed to cache indices", error=str(e))
    
    def _load_indices(self):
        """Load indices from cache files"""
        try:
            # Load BM25 index
            if self.bm25_cache_file.exists():
                with open(self.bm25_cache_file, 'rb') as f:
                    self.bm25_index = pickle.load(f)
            
            # Load TF-IDF components
            if self.tfidf_cache_file.exists():
                with open(self.tfidf_cache_file, 'rb') as f:
                    tfidf_data = pickle.load(f)
                    self.tfidf_vectorizer = tfidf_data['vectorizer']
                    self.tfidf_matrix = tfidf_data['matrix']
            
            # Load metadata
            if self.metadata_cache_file.exists():
                with open(self.metadata_cache_file, 'rb') as f:
                    self.corpus_metadata = pickle.load(f)
            
            if self.bm25_index and self.tfidf_vectorizer and self.corpus_metadata:
                logger.info(
                    "Hybrid search indices loaded from cache",
                    corpus_size=len(self.corpus_metadata)
                )
            
        except Exception as e:
            logger.error("Failed to load cached indices", error=str(e))
            # Reset indices on load failure
            self.bm25_index = None
            self.tfidf_vectorizer = None
            self.tfidf_matrix = None
            self.corpus_metadata = []
    
    async def bm25_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword search
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results with BM25 scores
        """
        if not self.bm25_index or not self.corpus_metadata:
            logger.warning("BM25 index not available")
            return []
        
        try:
            # Preprocess query
            query_tokens = self._preprocess_text(query)
            if not query_tokens:
                return []
            
            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top results
            top_indices = scores.argsort()[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include positive scores
                    result = self.corpus_metadata[idx].copy()
                    result['bm25_score'] = float(scores[idx])
                    result['search_type'] = 'bm25'
                    results.append(result)
            
            logger.debug(
                "BM25 search completed",
                query=query,
                results_count=len(results),
                top_score=results[0]['bm25_score'] if results else 0
            )
            
            return results
            
        except Exception as e:
            logger.error("BM25 search failed", error=str(e), query=query)
            return []
    
    async def tfidf_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform TF-IDF cosine similarity search
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results with TF-IDF scores
        """
        if not self.tfidf_vectorizer or self.tfidf_matrix is None:
            logger.warning("TF-IDF index not available")
            return []
        
        try:
            # Transform query
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Get top results
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.01:  # Minimum similarity threshold
                    result = self.corpus_metadata[idx].copy()
                    result['tfidf_score'] = float(similarities[idx])
                    result['search_type'] = 'tfidf'
                    results.append(result)
            
            logger.debug(
                "TF-IDF search completed",
                query=query,
                results_count=len(results),
                top_score=results[0]['tfidf_score'] if results else 0
            )
            
            return results
            
        except Exception as e:
            logger.error("TF-IDF search failed", error=str(e), query=query)
            return []
    
    async def semantic_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search using existing AI service
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results with semantic scores
        """
        try:
            # Generate embedding for query
            query_embedding = await ai_service.embed_text(query)
            
            # Search using existing semantic search
            semantic_results = await ai_service.search_similar_issues(
                query_embedding=query_embedding,
                top_k=top_k,
                similarity_threshold=0.1  # Low threshold for hybrid search
            )
            
            # Format results
            results = []
            for result in semantic_results:
                metadata = result.get('metadata', {})
                formatted_result = {
                    'id': result.get('id', ''),
                    'title': metadata.get('title', ''),
                    'description': metadata.get('description', ''),
                    'resolution': metadata.get('resolution', ''),
                    'tags': metadata.get('tags', []),
                    'created_at': metadata.get('created_at', ''),
                    'resolved_by': metadata.get('resolved_by', ''),
                    'semantic_score': result.get('score', 0.0),
                    'search_type': 'semantic'
                }
                results.append(formatted_result)
            
            logger.debug(
                "Semantic search completed",
                query=query,
                results_count=len(results),
                top_score=results[0]['semantic_score'] if results else 0
            )
            
            return results
            
        except Exception as e:
            logger.error("Semantic search failed", error=str(e), query=query)
            return []
    
    def _normalize_scores(self, results: List[Dict[str, Any]], score_key: str) -> List[Dict[str, Any]]:
        """
        Normalize scores to 0-1 range using min-max normalization
        
        Args:
            results: List of results with scores
            score_key: Key containing the score to normalize
            
        Returns:
            Results with normalized scores
        """
        if not results:
            return results
        
        scores = [r[score_key] for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            # All scores are the same
            for result in results:
                result[f'normalized_{score_key}'] = 1.0
        else:
            for result in results:
                normalized = (result[score_key] - min_score) / (max_score - min_score)
                result[f'normalized_{score_key}'] = normalized
        
        return results
    
    def _extract_merchant_id(self, text: str) -> Optional[str]:
        """
        Extract merchant ID from text
        
        Args:
            text: Text to search for merchant ID
            
        Returns:
            Merchant ID if found, None otherwise
        """
        text_lower = text.lower()
        
        # Merchant ID patterns
        merchant_patterns = [
            r'merchant_id[:\s]+([a-zA-Z0-9_-]+)',
            r'mid[:\s]+([a-zA-Z0-9_-]+)',
            r'merchant[:\s]+([a-zA-Z0-9_-]+)',
            r'\b([a-zA-Z0-9_]+_test)\b',  # test merchants
            r'\b([a-zA-Z0-9_]+_prod)\b',  # prod merchants
            r'\b(snapdeal_test|hdfc_merchant|axis_merchant|payu_merchant|razorpay_merchant)\b'
        ]
        
        for pattern in merchant_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1) if len(match.groups()) > 0 else match.group(0)
        
        return None
    
    def _extract_payment_gateway(self, text: str) -> Optional[str]:
        """
        Extract payment gateway from text
        
        Args:
            text: Text to search for payment gateway
            
        Returns:
            Payment gateway if found, None otherwise
        """
        text_lower = text.lower()
        
        # Payment gateway patterns
        pg_patterns = [
            r'pg[:\s]+([a-zA-Z0-9_-]+)',
            r'payment[_\s]*gateway[:\s]+([a-zA-Z0-9_-]+)',
            r'gateway[:\s]+([a-zA-Z0-9_-]+)',
            r'\b(pinelabs|hdfc|axis|icici|payu|razorpay|cashfree|phonepe|gpay|amazonpay)[\s_-]*(online|gateway|bank|pg)?\b',
            r'\b(upi|card|netbanking|wallet)[\s_-]*gateway\b'
        ]
        
        for pattern in pg_patterns:
            match = re.search(pattern, text_lower)
            if match:
                gateway = match.group(1) if len(match.groups()) > 0 else match.group(0)
                # Normalize gateway names
                gateway = gateway.replace('_gateway', '').replace('_pg', '').replace('_online', '')
                return gateway
        
        return None
    
    def _calculate_priority_score(self, query: str, result: Dict[str, Any], base_score: float) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculate priority score based on merchant_id and payment gateway matching
        
        Args:
            query: Search query
            result: Search result
            base_score: Base similarity score
            
        Returns:
            Tuple of (enhanced_score, match_type, match_details)
        """
        # Extract merchant_id and payment gateway from query
        query_merchant = self._extract_merchant_id(query)
        query_gateway = self._extract_payment_gateway(query)
        
        # Extract from result (title, description, tags)
        result_text = f"{result.get('title', '')} {result.get('description', '')} {' '.join(result.get('tags', []))}"
        result_merchant = self._extract_merchant_id(result_text)
        result_gateway = self._extract_payment_gateway(result_text)
        
        # Calculate priority boosts
        match_details = {
            'query_merchant': query_merchant,
            'query_gateway': query_gateway,
            'result_merchant': result_merchant,
            'result_gateway': result_gateway,
            'merchant_match': False,
            'gateway_match': False,
            'exact_match': False
        }
        
        # Check for matches
        merchant_match = query_merchant and result_merchant and query_merchant.lower() == result_merchant.lower()
        gateway_match = query_gateway and result_gateway and query_gateway.lower() == result_gateway.lower()
        
        match_details['merchant_match'] = merchant_match
        match_details['gateway_match'] = gateway_match
        
        # Priority scoring
        if merchant_match and gateway_match:
            # Perfect match: same merchant + same gateway
            enhanced_score = min(base_score * 2.5, 1.0)
            match_type = "PERFECT_MERCHANT_GATEWAY_MATCH"
            match_details['exact_match'] = True
        elif merchant_match:
            # High priority: same merchant
            enhanced_score = min(base_score * 2.0, 0.95)
            match_type = "MERCHANT_ID_MATCH"
        elif gateway_match:
            # Medium priority: same gateway
            enhanced_score = min(base_score * 1.5, 0.85)
            match_type = "PAYMENT_GATEWAY_MATCH"
        else:
            # Regular semantic/keyword match
            enhanced_score = base_score
            match_type = "SEMANTIC_MATCH"
        
        return enhanced_score, match_type, match_details
    
    def _detect_exact_match(self, query: str, result: Dict[str, Any]) -> bool:
        """
        Detect if this is an exact or near-exact match
        
        Args:
            query: Search query
            result: Search result
            
        Returns:
            True if exact/near-exact match
        """
        query_lower = query.lower().strip()
        title_lower = result.get('title', '').lower().strip()
        
        # Check for exact title match
        if query_lower == title_lower:
            return True
        
        # Check for high overlap (>80% of words match)
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())
        
        if len(query_words) > 0:
            overlap = len(query_words.intersection(title_words)) / len(query_words)
            if overlap >= 0.8:
                return True
        
        # Check for exact tag matches
        tags = [tag.lower() for tag in result.get('tags', [])]
        for tag in tags:
            if query_lower == tag or tag in query_lower:
                return True
        
        # Check for merchant_id + gateway priority match
        _, match_type, _ = self._calculate_priority_score(query, result, 1.0)
        if match_type == "PERFECT_MERCHANT_GATEWAY_MATCH":
            return True
        
        return False

    def _fuse_scores(self, all_results: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
        """
        Fuse scores from different search methods using weighted combination
        
        Args:
            all_results: Combined results from all search methods
            query: Original search query for exact match detection
            
        Returns:
            Results with fused scores, sorted by final score
        """
        # Group results by ID
        result_groups = {}
        for result in all_results:
            result_id = result['id']
            if result_id not in result_groups:
                result_groups[result_id] = {
                    'metadata': result,
                    'semantic_score': 0.0,
                    'bm25_score': 0.0,
                    'tfidf_score': 0.0,
                    'search_types': []
                }
            
            group = result_groups[result_id]
            search_type = result['search_type']
            group['search_types'].append(search_type)
            
            if search_type == 'semantic':
                group['semantic_score'] = result.get('normalized_semantic_score', 0.0)
            elif search_type == 'bm25':
                group['bm25_score'] = result.get('normalized_bm25_score', 0.0)
            elif search_type == 'tfidf':
                group['tfidf_score'] = result.get('normalized_tfidf_score', 0.0)
        
        # Calculate fused scores with priority matching
        fused_results = []
        for result_id, group in result_groups.items():
            # Calculate base fused score
            base_fused_score = (
                self.semantic_weight * group['semantic_score'] +
                self.bm25_weight * group['bm25_score'] +
                self.tfidf_weight * group['tfidf_score']
            )
            
            # Apply priority scoring based on merchant_id and payment gateway
            enhanced_score, match_type, match_details = self._calculate_priority_score(
                query, group['metadata'], base_fused_score
            )
            
            # CRITICAL FIX: Detect exact matches and apply additional boosts
            is_exact_match = self._detect_exact_match(query, group['metadata'])
            
            if is_exact_match:
                # Additional boost for exact title matches
                enhanced_score = min(enhanced_score * 1.2, 1.0)
                
                logger.info(
                    "EXACT MATCH DETECTED with Priority Scoring",
                    result_id=result_id,
                    title=group['metadata'].get('title', ''),
                    query=query,
                    match_type=match_type,
                    merchant_match=match_details.get('merchant_match', False),
                    gateway_match=match_details.get('gateway_match', False),
                    enhanced_score=enhanced_score
                )
            
            # Boost score if found by multiple methods
            method_count = len(set(group['search_types']))
            if method_count > 1:
                enhanced_score *= (1.0 + 0.1 * (method_count - 1))  # 10% boost per additional method
            
            result = group['metadata'].copy()
            result['fused_score'] = min(enhanced_score, 1.0)  # Cap at 1.0
            result['semantic_score'] = group['semantic_score']
            result['bm25_score'] = group['bm25_score']
            result['tfidf_score'] = group['tfidf_score']
            result['search_methods'] = list(set(group['search_types']))
            result['method_count'] = method_count
            result['is_exact_match'] = is_exact_match
            result['match_type'] = match_type
            result['priority_details'] = match_details
            
            fused_results.append(result)
        
        # Sort by fused score
        fused_results.sort(key=lambda x: x['fused_score'], reverse=True)
        
        return fused_results
    
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic, BM25, and TF-IDF search
        
        Args:
            query: Search query
            top_k: Number of final results to return
            min_score: Minimum fused score threshold
            
        Returns:
            List of search results with fused scores
        """
        try:
            start_time = time.time()
            
            # Perform all searches in parallel
            search_tasks = [
                self.semantic_search(query, top_k * 2),  # Get more results for fusion
                self.bm25_search(query, top_k * 2),
                self.tfidf_search(query, top_k * 2)
            ]
            
            semantic_results, bm25_results, tfidf_results = await asyncio.gather(
                *search_tasks, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(semantic_results, Exception):
                logger.error("Semantic search failed in hybrid", error=str(semantic_results))
                semantic_results = []
            
            if isinstance(bm25_results, Exception):
                logger.error("BM25 search failed in hybrid", error=str(bm25_results))
                bm25_results = []
            
            if isinstance(tfidf_results, Exception):
                logger.error("TF-IDF search failed in hybrid", error=str(tfidf_results))
                tfidf_results = []
            
            # Normalize scores within each method
            semantic_results = self._normalize_scores(semantic_results, 'semantic_score')
            bm25_results = self._normalize_scores(bm25_results, 'bm25_score')
            tfidf_results = self._normalize_scores(tfidf_results, 'tfidf_score')
            
            # Combine all results
            all_results = semantic_results + bm25_results + tfidf_results
            
            if not all_results:
                logger.warning("No results from any search method", query=query)
                return []
            
            # Fuse scores and rank (CRITICAL FIX: Pass query for exact match detection)
            fused_results = self._fuse_scores(all_results, query)
            
            # Apply minimum score threshold and limit results
            final_results = [
                result for result in fused_results
                if result['fused_score'] >= min_score
            ][:top_k]
            
            execution_time = (time.time() - start_time) * 1000
            
            logger.info(
                "Hybrid search completed",
                query=query,
                semantic_count=len(semantic_results),
                bm25_count=len(bm25_results),
                tfidf_count=len(tfidf_results),
                fused_count=len(fused_results),
                final_count=len(final_results),
                execution_time_ms=execution_time,
                top_score=final_results[0]['fused_score'] if final_results else 0
            )
            
            return final_results
            
        except Exception as e:
            logger.error("Hybrid search failed", error=str(e), query=query)
            return []
    
    async def get_search_suggestions(self, query: str, max_suggestions: int = 5) -> List[str]:
        """
        Get search suggestions based on query and available data
        
        Args:
            query: Partial or complete search query
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of suggested search queries
        """
        suggestions = []
        
        if not self.corpus_metadata:
            return suggestions
        
        try:
            query_lower = query.lower()
            
            # Extract common terms from corpus
            all_titles = [meta['title'].lower() for meta in self.corpus_metadata]
            all_tags = []
            for meta in self.corpus_metadata:
                all_tags.extend([tag.lower() for tag in meta.get('tags', [])])
            
            # Find matching titles
            for title in all_titles:
                if query_lower in title and title not in suggestions:
                    suggestions.append(title)
                    if len(suggestions) >= max_suggestions:
                        break
            
            # Find matching tags
            for tag in set(all_tags):
                if query_lower in tag and tag not in suggestions:
                    suggestions.append(tag)
                    if len(suggestions) >= max_suggestions:
                        break
            
            return suggestions[:max_suggestions]
            
        except Exception as e:
            logger.error("Failed to generate search suggestions", error=str(e))
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the search indices"""
        stats = {
            "bm25_available": self.bm25_index is not None,
            "tfidf_available": self.tfidf_vectorizer is not None,
            "corpus_size": len(self.corpus_metadata),
            "cache_files_exist": {
                "bm25": self.bm25_cache_file.exists(),
                "tfidf": self.tfidf_cache_file.exists(),
                "metadata": self.metadata_cache_file.exists()
            }
        }
        
        if self.bm25_index:
            stats["bm25_vocab_size"] = len(self.bm25_index.doc_freqs)
        
        if self.tfidf_matrix is not None:
            stats["tfidf_features"] = self.tfidf_matrix.shape[1]
            stats["tfidf_documents"] = self.tfidf_matrix.shape[0]
        
        return stats


# Global hybrid search service instance
hybrid_search_service = HybridSearchService()
