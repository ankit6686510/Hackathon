# 🏢 SherlockAI Enterprise Data Ingestion Guide

## Industry-Grade Data Sources (Beyond issues.json)

You're absolutely right that `issues.json` is just for initial setup. SherlockAI is built with enterprise-grade data ingestion capabilities for handling large amounts of real production data.

## 🚀 Available Data Sources

### 1. **Jira Integration** (Recommended for Engineering Teams)
```python
from enterprise_data_ingestion import EnterpriseDataIngestion

async def ingest_jira_data():
    ingester = EnterpriseDataIngestion()
    
    stats = await ingester.ingest_from_jira(
        jira_url="https://yourcompany.atlassian.net",
        username="your-email@company.com", 
        api_token="your-jira-api-token",
        project_key="JSP",  # Your project key
        max_issues=5000     # Can handle thousands
    )
    
    print(f"✅ Imported {stats['success']} issues from Jira")
```

**Benefits:**
- ✅ Direct integration with your existing issue tracking
- ✅ Automatically pulls resolved tickets with descriptions and resolutions
- ✅ Preserves metadata (assignee, labels, components)
- ✅ Handles Jira markup cleaning

### 2. **CSV/Excel Bulk Import** (For Data Exports)
```python
async def ingest_csv_data():
    ingester = EnterpriseDataIngestion()
    
    # Custom column mapping for your CSV format
    mapping = {
        "title": "Issue Title",           # Map CSV column to issue field
        "description": "Problem Desc",   
        "resolution": "Solution",
        "tags": "Categories",
        "resolved_by": "Engineer"
    }
    
    stats = await ingester.ingest_from_csv("production_issues.csv", mapping)
    print(f"✅ Imported {stats['success']} issues from CSV")
```

**Benefits:**
- ✅ Handle massive datasets (10K+ rows)
- ✅ Flexible column mapping
- ✅ Supports Excel files (.xlsx)
- ✅ Batch processing with progress tracking

### 3. **Zendesk Integration** (For Support Teams)
```python
async def ingest_zendesk_data():
    ingester = EnterpriseDataIngestion()
    
    stats = await ingester.ingest_from_zendesk(
        subdomain="yourcompany",
        email="admin@company.com",
        api_token="your-zendesk-token",
        max_tickets=10000
    )
    
    print(f"✅ Imported {stats['success']} tickets from Zendesk")
```

**Benefits:**
- ✅ Pulls solved support tickets
- ✅ Extracts resolutions from ticket comments
- ✅ Handles pagination automatically
- ✅ Cleans HTML formatting

### 4. **Slack Export Processing** (For Team Knowledge)
```python
async def ingest_slack_data():
    ingester = EnterpriseDataIngestion()
    
    stats = await ingester.ingest_from_slack_export(
        export_dir="/path/to/slack/export",
        channels=["tech-support", "incidents", "engineering"]
    )
    
    print(f"✅ Extracted {stats['success']} issues from Slack")
```

**Benefits:**
- ✅ Mines tribal knowledge from Slack conversations
- ✅ Identifies issue-resolution threads automatically
- ✅ Processes multiple channels
- ✅ Extracts context from threaded conversations

### 5. **Database Migration** (For Legacy Systems)
```python
async def ingest_database_data():
    ingester = EnterpriseDataIngestion()
    
    # Connect to your existing database
    connection_string = "postgresql://user:pass@host:5432/database"
    
    query = """
    SELECT 
        ticket_id,
        title,
        description, 
        resolution,
        created_date,
        resolved_by
    FROM support_tickets 
    WHERE status = 'resolved'
    """
    
    field_mapping = {
        "id": "ticket_id",
        "title": "title",
        "description": "description",
        "resolution": "resolution",
        "created_at": "created_date",
        "resolved_by": "resolved_by"
    }
    
    stats = await ingester.ingest_from_database(connection_string, query, field_mapping)
    print(f"✅ Migrated {stats['success']} issues from legacy database")
```

**Benefits:**
- ✅ Migrate from any SQL database
- ✅ Custom SQL queries for data filtering
- ✅ Flexible field mapping
- ✅ Handles large datasets efficiently

## 📊 Scale Comparison

| Data Source | Scale | Use Case | Setup Time |
|-------------|-------|----------|------------|
| `issues.json` | 10-100 issues | Initial setup, demos | 5 minutes |
| **Jira API** | 1K-50K issues | Production engineering teams | 15 minutes |
| **CSV Import** | 10K-100K issues | Data exports, migrations | 10 minutes |
| **Zendesk API** | 5K-25K tickets | Support team knowledge | 15 minutes |
| **Slack Export** | 1K-10K threads | Team tribal knowledge | 20 minutes |
| **Database** | 50K-500K records | Legacy system migration | 30 minutes |

## 🔧 Quick Setup Examples

### Example 1: Juspay Engineering Team
```bash
# 1. Set up Jira API token
# 2. Run ingestion
python -c "
import asyncio
from enterprise_data_ingestion import EnterpriseDataIngestion

async def main():
    ingester = EnterpriseDataIngestion()
    await ingester.ingest_from_jira(
        jira_url='https://juspay.atlassian.net',
        username='engineer@juspay.in',
        api_token='your-token',
        project_key='JSP',
        max_issues=2000
    )

asyncio.run(main())
"
```

### Example 2: Support Team CSV Export
```bash
# 1. Export tickets from your support system to CSV
# 2. Run ingestion
python -c "
import asyncio
from enterprise_data_ingestion import EnterpriseDataIngestion

async def main():
    ingester = EnterpriseDataIngestion()
    await ingester.ingest_from_csv('support_tickets_2024.csv')

asyncio.run(main())
"
```

## 🎯 Production Deployment Strategy

### Phase 1: Initial Training (Week 1)
1. **Start with CSV export** of your last 6 months of resolved issues
2. **Import 500-1000 issues** to establish baseline
3. **Test search quality** with real engineer queries

### Phase 2: Live Integration (Week 2)
1. **Set up Jira/Zendesk API** for ongoing ingestion
2. **Schedule daily/weekly imports** of new resolved issues
3. **Monitor search performance** and relevance scores

### Phase 3: Scale & Optimize (Week 3+)
1. **Expand to multiple data sources** (Slack, legacy systems)
2. **Fine-tune search parameters** based on usage analytics
3. **Add automated quality checks** for new training data

## 🔄 Automated Ingestion Pipeline

Create a scheduled job for continuous learning:

```python
# scheduled_ingestion.py
import asyncio
from datetime import datetime, timedelta
from enterprise_data_ingestion import EnterpriseDataIngestion

async def daily_ingestion():
    """Run daily to import new resolved issues"""
    ingester = EnterpriseDataIngestion()
    
    # Get issues resolved in last 24 hours
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Jira JQL for recent issues
    jql = f'project = "JSP" AND status = "Done" AND resolved >= "{yesterday}"'
    
    stats = await ingester.ingest_from_jira(
        jira_url="https://company.atlassian.net",
        username="bot@company.com",
        api_token="bot-token",
        project_key="JSP",
        max_issues=100
    )
    
    print(f"Daily ingestion: {stats['success']} new issues added")

if __name__ == "__main__":
    asyncio.run(daily_ingestion())
```

Schedule with cron:
```bash
# Add to crontab for daily 2 AM runs
0 2 * * * cd /path/to/sherlockai && python scheduled_ingestion.py
```

## 📈 Monitoring & Analytics

SherlockAI automatically tracks:
- **Search performance** (response times, relevance scores)
- **Training data quality** (embedding success rates)
- **Usage patterns** (most searched terms, popular issues)
- **Feedback loops** (user ratings on suggestions)

Access analytics via:
```python
from app.services.ai_service import ai_service

# Get training statistics
stats = await ai_service.get_index_stats()
print(f"Total trained issues: {stats['total_vectors']}")

# Get search analytics
from app.database import get_database
# Query search_logs table for usage patterns
```

## 🚨 Best Practices

### Data Quality
1. **Clean descriptions**: Remove PII, sensitive data
2. **Meaningful titles**: Ensure searchable, descriptive titles
3. **Complete resolutions**: Include actual fix steps, not just "resolved"
4. **Consistent tagging**: Use standardized tags across sources

### Performance
1. **Batch processing**: Import in chunks of 100-500 issues
2. **Rate limiting**: Respect API limits (Jira: 10 req/sec, Zendesk: 5 req/sec)
3. **Incremental updates**: Only import new/changed issues
4. **Monitor costs**: Track embedding API usage

### Security
1. **API tokens**: Use service accounts with read-only access
2. **Data sanitization**: Remove sensitive information before training
3. **Access control**: Limit who can run ingestion scripts
4. **Audit logs**: Track all data imports and sources

## 🎉 Ready to Scale!

Your SherlockAI is now equipped with enterprise-grade data ingestion capabilities. You can:

✅ **Import thousands of issues** from production systems
✅ **Continuously learn** from new resolved issues  
✅ **Scale horizontally** across multiple data sources
✅ **Maintain data quality** with automated validation
✅ **Monitor performance** with built-in analytics

The `issues.json` file was just the beginning - now you have a true enterprise AI knowledge system! 🚀
