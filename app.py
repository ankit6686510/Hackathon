import os
import streamlit as st
import requests
import json
from datetime import datetime

# Updated API URL to match the new backend structure
API_URL = os.getenv("SherlockAI_API_URL", "http://localhost:8000/api/v1/search")
HEALTH_URL = os.getenv("SherlockAI_HEALTH_URL", "http://localhost:8000/api/v1/health")

st.set_page_config(page_title="SherlockAI", page_icon="🔍", layout="centered")

# Add custom CSS for better styling
st.markdown("""
<style>
.main-header {
    text-align: center;
    color: #1f77b4;
    margin-bottom: 2rem;
}
.result-card {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 4px solid #1f77b4;
}
.error-box {
    background-color: #ffe6e6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #ff4444;
}
.success-box {
    background-color: #e6ffe6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #44ff44;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🔍 SherlockAI — AI-Powered Issue Intelligence</h1>', unsafe_allow_html=True)
st.markdown("**Transform tribal knowledge into AI-augmented institutional memory**")

# Add backend status check
def check_backend_status():
    """Check if the backend is running"""
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            return True, health_data.get("status", "unknown")
        else:
            return False, f"Backend returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Backend not reachable"
    except requests.exceptions.Timeout:
        return False, "Backend timeout"
    except Exception as e:
        return False, f"Backend error: {str(e)}"

# Check backend status
backend_online, backend_status = check_backend_status()

if not backend_online:
    st.error(f"❌ **Backend Error:** {backend_status}")
    st.info("🔧 **To fix this:**")
    st.code("python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    st.info("Make sure the backend is running at http://localhost:8000")
    st.stop()
else:
    if backend_status == "healthy":
        st.success("✅ Backend is healthy and ready")
    elif backend_status == "degraded":
        st.warning("⚠️ Backend is running but some services are degraded")
    else:
        st.info(f"ℹ️ Backend status: {backend_status}")

# Main search interface
st.markdown("### 🔍 Search Historical Issues")

# Input section
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input(
        "Describe your issue:", 
        placeholder="e.g., UPI payment failed with error 5003",
        help="Describe the technical issue you're facing"
    )
with col2:
    top_k = st.slider("Max Results", 1, 10, 3)

# Search type selection
search_type = st.selectbox(
    "Search Type:",
    ["semantic", "keyword"],
    index=0,
    help="Semantic search uses AI to understand meaning, keyword search looks for exact matches"
)

# Advanced options in expander
with st.expander("🔧 Advanced Options"):
    include_resolved_only = st.checkbox("Only resolved issues", value=True)
    similarity_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.7, 0.1)

# Search button and logic
if st.button("🔍 Search Issues", type="primary") or (query and st.session_state.get("auto_search")):
    if not query.strip():
        st.warning("⚠️ Please enter an issue description.")
    else:
        # Prepare search request
        search_payload = {
            "query": query,
            "top_k": top_k,
            "search_type": search_type,
            "include_resolved_only": include_resolved_only,
            "similarity_threshold": similarity_threshold
        }
        
        with st.spinner("🔍 Searching through historical issues..."):
            try:
                # Make API request with proper error handling
                response = requests.post(
                    API_URL, 
                    json=search_payload, 
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                results = data.get("results", [])
                execution_time = data.get("execution_time_ms", 0)
                
                # Display results
                if not results:
                    st.info("🤷‍♂️ No similar past issues found. Try adjusting your search terms or lowering the similarity threshold.")
                else:
                    st.success(f"✅ Found {len(results)} similar issue(s) in {execution_time:.0f}ms")
                    
                    for i, result in enumerate(results):
                        with st.container():
                            st.markdown(f"### 📋 Result #{i+1}: {result.get('title', 'Untitled Issue')}")
                            
                            # Score and metadata
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                score = result.get('score', 0)
                                if score > 0.9:
                                    st.metric("🎯 Similarity", f"{score:.1%}", delta="Excellent match")
                                elif score > 0.7:
                                    st.metric("🎯 Similarity", f"{score:.1%}", delta="Good match")
                                else:
                                    st.metric("🎯 Similarity", f"{score:.1%}", delta="Partial match")
                            
                            with col2:
                                created_at = result.get('created_at', '')
                                if created_at:
                                    try:
                                        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                        st.metric("📅 Date", date_obj.strftime("%Y-%m-%d"))
                                    except:
                                        st.metric("📅 Date", "Unknown")
                                else:
                                    st.metric("📅 Date", "Unknown")
                            
                            with col3:
                                resolved_by = result.get('resolved_by', 'Unknown')
                                st.metric("👤 Resolved By", resolved_by if len(resolved_by) < 15 else resolved_by[:12] + "...")
                            
                            # Description
                            description = result.get('description', '')
                            if description:
                                st.markdown("**📝 Description:**")
                                st.markdown(f"> {description}")
                            
                            # Resolution
                            resolution = result.get('resolution', '')
                            if resolution:
                                st.markdown("**✅ Resolution:**")
                                st.markdown(f"> {resolution}")
                            
                            # AI Suggestion (highlighted)
                            ai_suggestion = result.get('ai_suggestion', '')
                            if ai_suggestion:
                                st.markdown("**🤖 AI Fix Suggestion:**")
                                st.info(ai_suggestion)
                            
                            # Tags
                            tags = result.get('tags', [])
                            if tags and isinstance(tags, list):
                                st.markdown("**🏷️ Tags:**")
                                tag_html = " ".join([f'<span style="background-color: #e1f5fe; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin: 2px;">{tag}</span>' for tag in tags])
                                st.markdown(tag_html, unsafe_allow_html=True)
                            
                            st.markdown("---")
                
                # Display search metadata
                with st.expander("📊 Search Details"):
                    st.json({
                        "query": query,
                        "search_type": search_type,
                        "results_found": len(results),
                        "execution_time_ms": execution_time,
                        "similarity_threshold": similarity_threshold,
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except requests.exceptions.ConnectionError:
                st.error("❌ **Connection Error:** Cannot connect to the backend API")
                st.info("🔧 **To fix this:**")
                st.code("python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
                st.info("Make sure the backend is running at http://localhost:8000")
                
            except requests.exceptions.Timeout:
                st.error("⏱️ **Timeout Error:** The search request took too long")
                st.info("The backend might be processing a complex query. Please try again.")
                
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ **API Error:** {e}")
                if hasattr(e.response, 'text'):
                    try:
                        error_detail = e.response.json().get('detail', 'Unknown error')
                        st.error(f"Details: {error_detail}")
                    except:
                        st.error(f"Response: {e.response.text}")
                        
            except json.JSONDecodeError:
                st.error("❌ **Response Error:** Invalid response from backend")
                st.info("The backend returned an invalid response. Please check the backend logs.")
                
            except Exception as e:
                st.error(f"❌ **Unexpected Error:** {str(e)}")
                st.info("An unexpected error occurred. Please try again or contact support.")

# Sidebar with additional info
with st.sidebar:
    st.markdown("### 🎯 About SherlockAI")
    st.markdown("""
    **SherlockAI** transforms tribal knowledge into AI-augmented institutional memory.
    
    **Features:**
    - 🔍 Semantic search through historical issues
    - 🤖 AI-powered fix suggestions
    - ⚡ Sub-second response times
    - 📊 Similarity scoring
    - 🏷️ Intelligent tagging
    """)
    
    st.markdown("### 💡 Example Queries")
    example_queries = [
        "UPI payment failed with error 5003",
        "Database connection timeout",
        "API returning 500 error",
        "Webhook not receiving callbacks",
        "SSL certificate expired"
    ]
    
    for example in example_queries:
        if st.button(f"💭 {example}", key=f"example_{example}"):
            st.session_state.auto_search = True
            st.experimental_set_query_params(query=example)
            st.experimental_rerun()
    
    st.markdown("### 📈 System Status")
    if backend_online:
        st.success("✅ Backend Online")
        st.info(f"Status: {backend_status}")
    else:
        st.error("❌ Backend Offline")
    
    st.markdown("### 🔗 Quick Links")
    st.markdown("- [API Docs](http://localhost:8000/docs)")
    st.markdown("- [Health Check](http://localhost:8000/api/v1/health)")
    st.markdown("- [Metrics](http://localhost:8000/metrics)")
