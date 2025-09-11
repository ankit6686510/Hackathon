#!/usr/bin/env python3
"""
Demo: SherlockAI Enterprise Data Ingestion
Quick demonstration of scalable data ingestion beyond issues.json
"""

import asyncio
import pandas as pd
from datetime import datetime
import os

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')

from enterprise_data_ingestion import EnterpriseDataIngestion

async def demo_csv_ingestion():
    """Demo: Create and ingest a sample CSV file with production-like data"""
    print("🔄 Demo: CSV Ingestion for Large Datasets")
    print("=" * 50)
    
    # Create sample production data (simulating a real export)
    sample_data = [
        {
            "Issue ID": "PROD-001",
            "Issue Title": "Payment Gateway Timeout on HDFC Bank",
            "Problem Description": "Payment requests to HDFC bank timing out after 30 seconds during peak hours. Error code: GATEWAY_TIMEOUT. Affecting 15% of transactions.",
            "Solution": "Increased timeout to 60 seconds and implemented retry logic with exponential backoff. Added circuit breaker pattern for HDFC gateway.",
            "Categories": "Payments,HDFC,Timeout,Gateway",
            "Engineer": "payments-team@company.com",
            "Date Resolved": "2024-09-01"
        },
        {
            "Issue ID": "PROD-002", 
            "Issue Title": "UPI Collect Request Failing with Invalid VPA",
            "Problem Description": "UPI collect requests failing validation for certain VPA formats. Regex pattern not handling new bank VPA formats introduced in Sept 2024.",
            "Solution": "Updated VPA validation regex to support new bank formats. Added comprehensive test cases for all major bank VPA patterns.",
            "Categories": "UPI,Validation,VPA,Collect",
            "Engineer": "upi-team@company.com",
            "Date Resolved": "2024-09-05"
        },
        {
            "Issue ID": "PROD-003",
            "Issue Title": "Webhook Delivery Failure to Merchant Endpoints",
            "Problem Description": "Webhook delivery failing for 3 major merchants due to SSL certificate validation errors. Merchants using self-signed certificates.",
            "Solution": "Added configurable SSL verification bypass for whitelisted merchant endpoints. Implemented certificate pinning for enhanced security.",
            "Categories": "Webhooks,SSL,Merchants,Security",
            "Engineer": "integration-team@company.com", 
            "Date Resolved": "2024-09-10"
        },
        {
            "Issue ID": "PROD-004",
            "Issue Title": "Database Connection Pool Exhaustion",
            "Problem Description": "Application experiencing database connection pool exhaustion during peak traffic. Connection pool size of 20 insufficient for 1000+ concurrent users.",
            "Solution": "Increased connection pool size to 50 and implemented connection pooling optimization. Added monitoring for pool utilization.",
            "Categories": "Database,Performance,ConnectionPool,Scaling",
            "Engineer": "backend-team@company.com",
            "Date Resolved": "2024-09-08"
        },
        {
            "Issue ID": "PROD-005",
            "Issue Title": "Redis Cache Eviction Causing Performance Degradation", 
            "Problem Description": "Redis cache hitting memory limits and evicting frequently accessed keys. Cache hit ratio dropped from 95% to 60%.",
            "Solution": "Increased Redis memory allocation and implemented LRU eviction policy optimization. Added cache warming for critical keys.",
            "Categories": "Redis,Cache,Performance,Memory",
            "Engineer": "infrastructure-team@company.com",
            "Date Resolved": "2024-09-12"
        }
    ]
    
    # Create CSV file
    df = pd.DataFrame(sample_data)
    csv_file = "sample_production_issues.csv"
    df.to_csv(csv_file, index=False)
    print(f"✅ Created sample CSV with {len(sample_data)} production issues")
    
    # Set up ingestion with custom column mapping
    ingester = EnterpriseDataIngestion()
    
    column_mapping = {
        "id": "Issue ID",
        "title": "Issue Title", 
        "description": "Problem Description",
        "resolution": "Solution",
        "tags": "Categories",
        "resolved_by": "Engineer",
        "created_at": "Date Resolved"
    }
    
    # Ingest the data
    print(f"🚀 Ingesting data from {csv_file}...")
    stats = await ingester.ingest_from_csv(csv_file, column_mapping)
    
    print(f"\n📊 Ingestion Results:")
    print(f"   Total rows: {stats['total']}")
    print(f"   Successfully processed: {stats['processed']}")
    print(f"   Added to SherlockAI: {stats['success']}")
    
    # Clean up
    os.remove(csv_file)
    print(f"🧹 Cleaned up temporary file: {csv_file}")
    
    return stats

async def demo_manual_bulk_addition():
    """Demo: Add multiple issues programmatically (simulating API ingestion)"""
    print("\n🔄 Demo: Programmatic Bulk Addition")
    print("=" * 50)
    
    ingester = EnterpriseDataIngestion()
    
    # Simulate issues from different sources
    issues_to_add = [
        {
            "title": "Microservice Circuit Breaker Tripping Frequently",
            "description": "Order processing microservice circuit breaker opening due to downstream payment service latency spikes above 5 seconds.",
            "resolution": "Implemented bulkhead pattern and increased circuit breaker threshold to 10 seconds. Added fallback mechanism for order queuing.",
            "tags": ["Microservices", "CircuitBreaker", "Resilience", "OrderProcessing"],
            "resolved_by": "microservices-team@company.com"
        },
        {
            "title": "Kafka Consumer Lag Increasing During Peak Hours",
            "description": "Payment event consumers falling behind during peak traffic. Consumer lag reaching 10+ minutes affecting real-time payment status updates.",
            "resolution": "Increased consumer instances from 3 to 8 and optimized batch processing. Implemented parallel processing for non-dependent events.",
            "tags": ["Kafka", "Consumers", "Performance", "Payments", "EventStreaming"],
            "resolved_by": "data-platform-team@company.com"
        },
        {
            "title": "API Rate Limiting Blocking Legitimate Traffic",
            "description": "Aggressive rate limiting configuration blocking legitimate high-volume merchants during flash sales. 429 errors spiking to 15% of requests.",
            "resolution": "Implemented tiered rate limiting based on merchant category. Added burst allowance for verified high-volume merchants.",
            "tags": ["API", "RateLimiting", "Merchants", "Performance"],
            "resolved_by": "api-gateway-team@company.com"
        }
    ]
    
    success_count = 0
    
    for i, issue in enumerate(issues_to_add, 1):
        print(f"📝 Adding issue {i}/{len(issues_to_add)}: {issue['title'][:50]}...")
        
        success = await ingester.trainer.add_single_issue(
            title=issue["title"],
            description=issue["description"], 
            resolution=issue["resolution"],
            tags=issue["tags"],
            resolved_by=issue["resolved_by"]
        )
        
        if success:
            success_count += 1
    
    print(f"\n📊 Bulk Addition Results:")
    print(f"   Total issues: {len(issues_to_add)}")
    print(f"   Successfully added: {success_count}")
    
    return success_count

async def demo_search_quality():
    """Demo: Test search quality with the newly ingested data"""
    print("\n🔍 Demo: Testing Search Quality with New Data")
    print("=" * 50)
    
    ingester = EnterpriseDataIngestion()
    
    # Test queries that should match our ingested data
    test_queries = [
        "payment gateway timeout",
        "database connection pool",
        "webhook delivery failing",
        "redis cache performance",
        "microservice circuit breaker",
        "kafka consumer lag"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Searching: '{query}'")
        results = await ingester.trainer.test_search(query, top_k=2)
        
        if results:
            for i, result in enumerate(results, 1):
                score = result.get('score', 0)
                title = result.get('title', 'No title')
                print(f"   {i}. {title[:60]}... (Score: {score:.3f})")
        else:
            print("   No results found")

async def demo_vector_db_stats():
    """Demo: Show vector database statistics"""
    print("\n📊 Demo: Vector Database Statistics")
    print("=" * 50)
    
    ingester = EnterpriseDataIngestion()
    stats = await ingester.trainer.get_vector_db_stats()
    
    if stats:
        print(f"📈 Vector Database Stats:")
        print(f"   Total vectors: {stats.get('total_vectors', 'Unknown')}")
        print(f"   Dimension: {stats.get('dimension', 'Unknown')}")
        print(f"   Index status: {stats.get('status', 'Unknown')}")
    else:
        print("❌ Could not retrieve vector database statistics")

async def main():
    """Run all demos"""
    print("🚀 SherlockAI Enterprise Data Ingestion Demo")
    print("=" * 60)
    print("This demo shows how to scale beyond issues.json for production use")
    print()
    
    try:
        # Demo 1: CSV ingestion (most common enterprise use case)
        csv_stats = await demo_csv_ingestion()
        
        # Demo 2: Programmatic addition (API integration simulation)
        bulk_stats = await demo_manual_bulk_addition()
        
        # Demo 3: Test search quality
        await demo_search_quality()
        
        # Demo 4: Show database stats
        await demo_vector_db_stats()
        
        # Summary
        print("\n🎉 Demo Complete!")
        print("=" * 60)
        print(f"✅ CSV Ingestion: {csv_stats.get('success', 0)} issues added")
        print(f"✅ Bulk Addition: {bulk_stats} issues added")
        print(f"✅ Search Quality: Tested with 6 different queries")
        print(f"✅ Vector DB: Statistics retrieved")
        
        print("\n💡 Next Steps for Production:")
        print("1. Set up Jira/Zendesk API integration")
        print("2. Export your historical issues to CSV")
        print("3. Schedule automated daily ingestion")
        print("4. Monitor search quality and user feedback")
        print("5. Scale to thousands of issues!")
        
        print(f"\n📚 See ENTERPRISE_INGESTION_GUIDE.md for detailed setup instructions")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Make sure SherlockAI backend is running: python main.py")

if __name__ == "__main__":
    asyncio.run(main())
