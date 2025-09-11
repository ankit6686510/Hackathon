# 🎓 SherlockAI Training Guide

## How to Train Your SherlockAI Model

SherlockAI AI assistant learns from historical issues to provide intelligent suggestions. Here's how to train and expand its knowledge base.

## 🚀 Quick Start

### 1. Train with Existing Issues
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the training script
python train_model.py
```

This will load all issues from `issues.json` into both the database and vector database.

## 📊 Current Training Status

✅ **16 Issues Trained** - Your model is ready to use!
✅ **Vector Database**: 16 vectors with 768 dimensions
✅ **Search Performance**: 60-75% similarity scores for relevant matches

## 📝 Adding New Issues

### Method 1: Add to issues.json (Recommended for Bulk)

Edit the `issues.json` file and add new issues in this format:

```json
{
  "id": "JSP-1017",
  "title": "Your Issue Title",
  "description": "Detailed description of the problem",
  "resolution": "How the issue was resolved",
  "tags": ["tag1", "tag2", "tag3"],
  "created_at": "2024-05-15",
  "resolved_by": "engineer@juspay.in"
}
```

Then run the training script again:
```bash
python train_model.py
```

### Method 2: Add Single Issue via Script

Create a Python script to add individual issues:

```python
import asyncio
from train_model import SherlockAITrainer

async def add_new_issue():
    trainer = SherlockAITrainer()
    
    success = await trainer.add_single_issue(
        title="New Issue Title",
        description="Description of the problem",
        resolution="How it was fixed",
        tags=["tag1", "tag2"],
        resolved_by="your.email@juspay.in"
    )
    
    if success:
        print("✅ Issue added successfully!")
    else:
        print("❌ Failed to add issue")

# Run it
asyncio.run(add_new_issue())
```

### Method 3: Add via API (Coming Soon)

We'll add a web interface for easy issue management.

## 🔍 Testing Your Training

After adding new issues, test the search functionality:

```bash
# Test in the ChatGPT interface
# Go to: http://localhost:5173
# Try queries like:
# - "UPI payment failed"
# - "timeout error" 
# - "webhook issues"
```

## 📋 Issue Format Guidelines

### Required Fields
- **id**: Unique identifier (e.g., "JSP-1017", "MANUAL-123")
- **title**: Clear, descriptive title
- **description**: Detailed problem description
- **resolution**: How the issue was resolved

### Optional Fields
- **tags**: Array of relevant tags for categorization
- **created_at**: Date in YYYY-MM-DD format
- **resolved_by**: Email of the engineer who resolved it

### Best Practices

1. **Clear Titles**: Use descriptive titles that engineers would search for
   - ✅ "UPI Payment Failed with Error 5003"
   - ❌ "Payment Issue"

2. **Detailed Descriptions**: Include error messages, symptoms, and context
   - ✅ "UPI payment stuck in processing, timeout after 10s, Axis PSP"
   - ❌ "Payment not working"

3. **Actionable Resolutions**: Provide specific steps taken to fix the issue
   - ✅ "Increased PSP timeout to 30s and added retry with idempotency key"
   - ❌ "Fixed the timeout"

4. **Relevant Tags**: Use consistent tags for better categorization
   - Common tags: UPI, Cards, Webhooks, Timeout, API, Database, etc.

## 🎯 Training Examples

### Example 1: Payment Issue
```json
{
  "id": "JSP-1017",
  "title": "Credit Card Payment Declined with 3DS Error",
  "description": "Customer's credit card payment failing during 3DS authentication step. Error code 3DS_AUTH_FAILED returned from bank.",
  "resolution": "Updated 3DS flow to handle bank-specific error codes and added fallback authentication method.",
  "tags": ["Cards", "3DS", "Authentication", "Payment"],
  "created_at": "2024-05-15",
  "resolved_by": "payments.team@juspay.in"
}
```

### Example 2: API Issue
```json
{
  "id": "JSP-1018", 
  "title": "Merchant API Rate Limit Exceeded",
  "description": "Merchant hitting rate limits during peak hours, causing 429 errors and failed transactions.",
  "resolution": "Implemented exponential backoff in merchant SDK and increased rate limits for verified merchants.",
  "tags": ["API", "RateLimit", "SDK", "Performance"],
  "created_at": "2024-05-16",
  "resolved_by": "api.team@juspay.in"
}
```

## 🔧 Advanced Training

### Batch Training
For large datasets, use the batch training functionality:

```python
import asyncio
from train_model import SherlockAITrainer

async def batch_train():
    trainer = SherlockAITrainer()
    
    # Train from custom JSON file
    stats = await trainer.train_from_json("custom_issues.json")
    print(f"Trained {stats['vector_added']} issues")

asyncio.run(batch_train())
```

### Training Validation
Check training quality:

```python
import asyncio
from train_model import SherlockAITrainer

async def validate_training():
    trainer = SherlockAITrainer()
    
    # Test search quality
    results = await trainer.test_search("payment timeout", top_k=5)
    
    for result in results:
        print(f"Score: {result['score']:.3f} - {result['title']}")

asyncio.run(validate_training())
```

## 📈 Monitoring Training Quality

### Good Training Indicators
- **High Similarity Scores**: 60%+ for relevant matches
- **Diverse Results**: Different types of issues returned
- **Relevant Suggestions**: AI suggestions make sense

### Improving Training Quality
1. **Add More Issues**: More data = better results
2. **Improve Descriptions**: More detailed descriptions help matching
3. **Consistent Tagging**: Use standardized tags across issues
4. **Regular Updates**: Keep adding new resolved issues

## 🚨 Troubleshooting

### Common Issues

**"No similar issues found"**
- Add more training data
- Check if query matches issue terminology
- Verify vector database has data

**Low similarity scores**
- Improve issue descriptions
- Add more relevant issues
- Use more specific search terms

**Training script fails**
- Check API keys in `.env` file
- Ensure Pinecone index exists
- Verify network connectivity

### Getting Help

1. Check the logs for detailed error messages
2. Verify all environment variables are set
3. Test individual components (embedding, vector search)

## 🎯 Next Steps

1. **Add Your Issues**: Start with 20-50 real issues from your team
2. **Test Regularly**: Use the ChatGPT interface to test search quality
3. **Iterate**: Add more issues based on what engineers actually search for
4. **Monitor**: Track which searches return good results vs. poor results

Your SherlockAI is now trained and ready to help your engineering team find solutions faster! 🚀
