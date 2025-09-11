# 🧪 SherlockAI API Testing with Postman

## 🚀 Quick Setup

Your SherlockAI backend is running on: **http://localhost:8000**

## 📋 Available API Endpoints

### 1. Health Check
### 2. Enhanced AI Search (Unlimited Capabilities)
### 3. Analytics

---

## 🔧 Postman Collection Setup

### 1. **Health Check Endpoint**

**Method**: `GET`  
**URL**: `http://localhost:8000/api/v1/health`  
**Headers**: None required

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-11T08:07:27.602332Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "ai_service": "healthy"
  }
}
```

---

### 2. **Enhanced AI Search - Technical Issues**

**Method**: `POST`  
**URL**: `http://localhost:8000/api/v1/search`  
**Headers**: 
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "query": "payment gateway timeout error",
  "top_k": 3
}
```

**Expected Response**:
```json
{
  "query": "payment gateway timeout error",
  "results": [
    {
      "id": "JSP-1234",
      "score": 0.87,
      "title": "Payment Gateway Timeout on HDFC Bank",
      "description": "Payment requests timing out after 30 seconds...",
      "resolution": "Increased timeout to 60 seconds and implemented retry logic...",
      "ai_suggestion": "Fix Suggestion: Increase gateway timeout to 60s and add exponential backoff retry logic.",
      "tags": ["payment", "timeout", "HDFC"],
      "resolved_by": "john.doe@juspay.in"
    }
  ],
  "query_type": "technical_issue",
  "has_historical_data": true,
  "response_time_ms": 234
}
```

---

### 3. **Enhanced AI Search - Code Generation**

**Method**: `POST`  
**URL**: `http://localhost:8000/api/v1/search`  
**Headers**: 
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "query": "write a Python function to sort a list of dictionaries by a specific key",
  "top_k": 1
}
```

**Expected Response**:
```json
{
  "query": "write a Python function to sort a list of dictionaries by a specific key",
  "ai_response": "Here's a comprehensive solution for sorting a list of dictionaries:\n\n```python\ndef sort_dict_list(dict_list, key, reverse=False):\n    \"\"\"\n    Sort a list of dictionaries by a specific key\n    \n    Args:\n        dict_list: List of dictionaries to sort\n        key: Key to sort by\n        reverse: Sort in descending order if True\n    \n    Returns:\n        Sorted list of dictionaries\n    \"\"\"\n    return sorted(dict_list, key=lambda x: x.get(key, 0), reverse=reverse)\n\n# Usage examples:\nstudents = [\n    {'name': 'Alice', 'grade': 85},\n    {'name': 'Bob', 'grade': 92},\n    {'name': 'Charlie', 'grade': 78}\n]\n\n# Sort by grade (ascending)\nsorted_students = sort_dict_list(students, 'grade')\nprint(sorted_students)\n# Output: [{'name': 'Charlie', 'grade': 78}, {'name': 'Alice', 'grade': 85}, {'name': 'Bob', 'grade': 92}]\n\n# Sort by grade (descending)\nsorted_desc = sort_dict_list(students, 'grade', reverse=True)\nprint(sorted_desc)\n```\n\n**Best Practices:**\n- Use `get()` method to handle missing keys safely\n- Consider using `operator.itemgetter()` for better performance with large datasets\n- Add type hints for better code documentation",
  "query_type": "code_help",
  "has_historical_data": false,
  "response_time_ms": 1456
}
```

---

### 4. **Enhanced AI Search - General Knowledge**

**Method**: `POST`  
**URL**: `http://localhost:8000/api/v1/search`  
**Headers**: 
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "query": "explain machine learning in simple terms",
  "top_k": 1
}
```

**Expected Response**:
```json
{
  "query": "explain machine learning in simple terms",
  "ai_response": "Machine Learning is like teaching a computer to recognize patterns and make predictions, similar to how humans learn from experience.\n\n**Simple Analogy:**\nThink of it like teaching a child to recognize animals:\n- Show them 1000 pictures of cats and dogs\n- They learn the differences (cats have pointy ears, dogs vary more in size)\n- Now they can identify new cats and dogs they've never seen\n\n**How it works:**\n1. **Training**: Feed the computer lots of data with known answers\n2. **Learning**: The computer finds patterns in the data\n3. **Prediction**: It uses those patterns to make guesses about new data\n\n**Real Examples:**\n- Netflix recommending movies you might like\n- Email filtering spam automatically\n- Voice assistants understanding what you say\n- Photo apps recognizing faces\n\n**Types:**\n- **Supervised**: Learning with examples (like the cat/dog example)\n- **Unsupervised**: Finding hidden patterns in data\n- **Reinforcement**: Learning through trial and error (like game AI)\n\nThe key is that the computer gets better at its job the more data it sees, just like humans get better with practice!",
  "query_type": "conversational",
  "has_historical_data": false,
  "response_time_ms": 1823
}
```

---

### 5. **Enhanced AI Search - Conversational**

**Method**: `POST`  
**URL**: `http://localhost:8000/api/v1/search`  
**Headers**: 
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "query": "can you help with slack integration",
  "top_k": 1
}
```

**Expected Response**:
```json
{
  "query": "can you help with slack integration",
  "ai_response": "Yes! I can definitely help you with Slack integration. I can assist with:\n\n• **Slack API Integration**: Setting up apps, bots, and webhooks\n• **Bot Development**: Creating interactive bots with slash commands\n• **Workflow Automation**: Automating tasks and notifications\n• **Channel Management**: Managing channels, users, and permissions\n• **Custom Features**: Building custom Slack apps and integrations\n\n**What specifically would you like to know about Slack?**\n- Setting up a Slack bot?\n- Creating slash commands?\n- Webhook integrations?\n- OAuth authentication?\n- Interactive components (buttons, modals)?\n\nI can provide step-by-step guides, code examples, and troubleshoot any issues you're facing. Just let me know what aspect of Slack integration you need help with!",
  "query_type": "conversational",
  "has_historical_data": false,
  "response_time_ms": 1234
}
```

---

### 6. **Analytics Endpoint**

**Method**: `GET`  
**URL**: `http://localhost:8000/api/v1/analytics`  
**Headers**: None required

**Expected Response**:
```json
{
  "total_searches": 156,
  "popular_queries": [
    {"query": "payment timeout", "count": 23},
    {"query": "database connection", "count": 18},
    {"query": "authentication error", "count": 15}
  ],
  "query_types": {
    "technical_issue": 45,
    "code_help": 38,
    "conversational": 32,
    "general": 41
  },
  "average_response_time_ms": 1247,
  "success_rate": 0.98
}
```

---

## 🧪 Testing Scenarios

### Scenario 1: Test Unlimited AI Capabilities
1. **Technical Question**: "Redis connection timeout in production"
2. **Code Generation**: "create a REST API endpoint in FastAPI"
3. **General Knowledge**: "what is blockchain technology"
4. **Creative Task**: "help me write a project proposal"

### Scenario 2: Test Query Classification
Send different types of queries and verify the `query_type` in responses:
- Technical issues → `technical_issue`
- Code requests → `code_help`
- General questions → `conversational` or `general`

### Scenario 3: Test Historical Data Integration
Send technical queries that might match your historical issues and verify:
- `has_historical_data: true`
- Relevant historical matches with scores
- AI-generated fix suggestions

---

## 🔍 Response Analysis

### Key Fields to Check:
- **`query_type`**: Verify correct classification
- **`has_historical_data`**: True for technical issues with matches
- **`response_time_ms`**: Should be under 3000ms
- **`ai_response`** or **`results`**: Quality and relevance of responses

### Success Indicators:
- ✅ Health check returns 200 OK
- ✅ All query types get appropriate responses
- ✅ No more "I only help with technical issues" restrictions
- ✅ Code generation includes working examples
- ✅ General questions get helpful explanations

---

## 🚀 Advanced Testing

### Custom Headers (Optional):
```
X-User-ID: test-user-123
X-Session-ID: session-456
```

### Batch Testing:
Create a collection with all the above requests and run them sequentially to verify all capabilities work.

### Performance Testing:
- Send multiple concurrent requests
- Measure response times
- Verify system stability

---

## 🎯 Expected Behavior

Your enhanced SherlockAI should now:
1. **Accept ANY question** - no restrictions
2. **Provide intelligent responses** for all query types
3. **Generate code** with explanations and examples
4. **Answer general knowledge** questions helpfully
5. **Maintain technical expertise** with historical data integration

**No more frustrating "I only help with technical issues" responses!** 🎉
