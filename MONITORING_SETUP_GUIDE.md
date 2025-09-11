# FixGenie Monitoring System - Complete Setup Guide

## 🎯 Overview

FixGenie now includes a comprehensive, industry-grade monitoring system that provides:

- **Real-time Metrics Collection** (Prometheus)
- **Enhanced Structured Logging** (JSON format)
- **Health Monitoring** (System, Database, AI Services)
- **Intelligent Alerting** (Slack, Email)
- **Security Audit Logging**
- **Performance Monitoring**
- **Business Intelligence Tracking**

## 📊 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FixGenie API  │───▶│  Monitoring     │───▶│   Alerting      │
│                 │    │  Middleware     │    │   Channels      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Structured    │    │   Prometheus    │    │   Slack/Email   │
│   Logs          │    │   Metrics       │    │   Notifications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Monitoring Configuration
ENABLE_METRICS=true
LOG_LEVEL=INFO

# Alerting (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
ALERT_EMAIL_SMTP_HOST=smtp.gmail.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_USERNAME=your-email@gmail.com
ALERT_EMAIL_PASSWORD=your-app-password
ALERT_EMAIL_FROM=fixgenie-alerts@yourcompany.com
ALERT_EMAIL_TO=team@yourcompany.com,ops@yourcompany.com

# Sentry (Optional)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### 2. Start the Application

```bash
# The monitoring system starts automatically
python main.py
```

### 3. Access Monitoring Endpoints

- **Health Check**: `GET /api/v1/health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Analytics**: `GET /api/v1/analytics/dashboard`

## 📈 Metrics Collection

### Available Metrics

#### HTTP Metrics
- `fixgenie_http_requests_total` - Total HTTP requests by method, endpoint, status
- `fixgenie_http_request_duration_seconds` - Request duration histogram

#### Search Metrics
- `fixgenie_search_requests_total` - Total search requests by type and status
- `fixgenie_search_duration_seconds` - Search duration histogram
- `fixgenie_search_results_count` - Number of results returned

#### AI Service Metrics
- `fixgenie_ai_requests_total` - AI service requests by service, model, status
- `fixgenie_ai_request_duration_seconds` - AI request duration
- `fixgenie_ai_tokens_total` - Token usage tracking

#### System Metrics
- `fixgenie_db_connections_active` - Active database connections
- `fixgenie_cache_hit_ratio` - Cache hit ratio
- `fixgenie_errors_total` - Error count by type and component

#### Business Metrics
- `fixgenie_feedback_submissions_total` - User feedback by rating and helpfulness
- `fixgenie_user_sessions_active` - Active user sessions

### Accessing Metrics

```bash
# View all metrics
curl http://localhost:8000/metrics

# Specific metric example
curl http://localhost:8000/metrics | grep fixgenie_search_requests_total
```

## 📝 Logging System

### Log Levels and Types

#### Application Logs
- **INFO**: Normal operations, startup/shutdown
- **WARNING**: Degraded performance, recoverable errors
- **ERROR**: Application errors, failed requests
- **CRITICAL**: System failures, unrecoverable errors

#### Security Logs
- Authentication attempts
- Authorization failures
- Suspicious activity detection
- Data access auditing

#### Business Logs
- Search events with query analysis
- User feedback submissions
- Session management
- Feature usage tracking

#### Performance Logs
- Slow request detection (>5s threshold)
- Resource usage monitoring
- Database query performance

### Log Format

All logs are structured JSON:

```json
{
  "timestamp": "2025-09-12T00:20:00.000Z",
  "level": "info",
  "event": "Search event",
  "query": "payment failed",
  "results_count": 3,
  "execution_time_ms": 1250,
  "user_id": "user123",
  "correlation_id": "req-abc-123",
  "event_type": "search"
}
```

### Log Files

Logs are automatically rotated:

```
logs/
├── fixgenie.log      # Application logs (100MB, 10 backups)
├── security.log      # Security events (50MB, 20 backups)
└── business.log      # Business metrics (100MB, 15 backups)
```

## 🏥 Health Monitoring

### Health Checks

The system monitors:

1. **System Resources**
   - CPU usage (warning >75%, critical >90%)
   - Memory usage (warning >80%, critical >90%)
   - Disk usage (warning >85%, critical >95%)

2. **Database Health**
   - Connection availability
   - Query response time
   - Connection pool status

3. **AI Services**
   - Embedding generation
   - Model availability
   - Response times

4. **Vector Database**
   - Pinecone connectivity
   - Index statistics
   - Vector count validation

5. **Cache System**
   - Redis connectivity
   - Operation performance
   - Hit/miss ratios

6. **External Dependencies**
   - AI API reachability
   - Third-party service status

### Health Endpoints

```bash
# Overall health status
curl http://localhost:8000/api/v1/health

# Detailed health information
curl http://localhost:8000/api/v1/health/detailed
```

### Health Status Levels

- **HEALTHY**: All systems operational
- **DEGRADED**: Some issues but service available
- **UNHEALTHY**: Critical issues affecting service
- **UNKNOWN**: Unable to determine status

## 🚨 Alerting System

### Default Alert Rules

1. **High Error Rate** (>5% error rate)
   - Severity: HIGH
   - Channels: Slack, Email

2. **Slow Response Time** (>5 seconds average)
   - Severity: MEDIUM
   - Channels: Slack

3. **High Memory Usage** (>85%)
   - Severity: HIGH
   - Channels: Slack, Email

4. **AI Service Failures** (>10% error rate)
   - Severity: CRITICAL
   - Channels: Slack, Email, SMS

5. **Database Connection Issues** (>5 connection errors)
   - Severity: CRITICAL
   - Channels: Slack, Email, SMS

### Alert Channels

#### Slack Integration

```python
from app.monitoring.alerts import SlackChannel, AlertManager

# Setup Slack alerts
slack_channel = SlackChannel(
    webhook_url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    channel="#alerts"
)

alert_manager = AlertManager()
alert_manager.add_channel(slack_channel)
```

#### Email Integration

```python
from app.monitoring.alerts import EmailChannel

# Setup email alerts
email_channel = EmailChannel(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-app-password",
    from_email="fixgenie-alerts@yourcompany.com",
    to_emails=["team@yourcompany.com", "ops@yourcompany.com"]
)

alert_manager.add_channel(email_channel)
```

### Custom Alert Rules

```python
from app.monitoring.alerts import AlertRule, AlertSeverity

# Create custom alert rule
custom_rule = AlertRule(
    name="High Search Latency",
    condition=lambda metrics: metrics.get("avg_search_time", 0) > 3.0,
    severity=AlertSeverity.MEDIUM,
    description="Search queries taking longer than 3 seconds",
    labels={"component": "search", "type": "performance"}
)

alert_manager.add_rule(custom_rule)
```

## 📊 Grafana Dashboard Setup

### 1. Install Grafana

```bash
# Using Docker
docker run -d \
  --name=grafana \
  -p 3000:3000 \
  grafana/grafana-enterprise

# Or using Homebrew (macOS)
brew install grafana
brew services start grafana
```

### 2. Configure Prometheus Data Source

1. Open Grafana: `http://localhost:3000`
2. Login: admin/admin
3. Add Prometheus data source: `http://localhost:9090`

### 3. Import FixGenie Dashboard

Use this dashboard configuration:

```json
{
  "dashboard": {
    "title": "FixGenie Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(fixgenie_http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(fixgenie_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Search Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(fixgenie_search_requests_total[5m])",
            "legendFormat": "Search Rate"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(fixgenie_errors_total[5m])",
            "legendFormat": "{{error_type}}"
          }
        ]
      }
    ]
  }
}
```

## 🔍 Log Analysis

### ELK Stack Setup (Optional)

#### 1. Elasticsearch

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:7.14.0
```

#### 2. Logstash Configuration

Create `logstash.conf`:

```ruby
input {
  file {
    path => "/path/to/fixgenie/logs/*.log"
    start_position => "beginning"
    codec => "json"
  }
}

filter {
  if [event_type] {
    mutate {
      add_tag => [ "%{event_type}" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "fixgenie-logs-%{+YYYY.MM.dd}"
  }
}
```

#### 3. Kibana

```bash
docker run -d \
  --name kibana \
  -p 5601:5601 \
  -e "ELASTICSEARCH_HOSTS=http://localhost:9200" \
  kibana:7.14.0
```

### Log Queries

#### Search Performance Analysis

```bash
# Find slow searches
grep "Search event" logs/business.log | jq 'select(.execution_time_ms > 5000)'

# Most common search queries
grep "Search event" logs/business.log | jq -r '.query' | sort | uniq -c | sort -nr
```

#### Error Analysis

```bash
# Error rate by component
grep "error" logs/fixgenie.log | jq -r '.component' | sort | uniq -c

# Recent critical errors
grep "critical" logs/fixgenie.log | tail -10 | jq '.'
```

## 🔧 Troubleshooting

### Common Issues

#### 1. High Memory Usage Alert

```bash
# Check memory usage
curl http://localhost:8000/api/v1/health | jq '.checks.system_resources'

# View memory metrics
curl http://localhost:8000/metrics | grep memory
```

#### 2. Slow Search Performance

```bash
# Check search metrics
curl http://localhost:8000/metrics | grep search_duration

# Analyze slow searches
grep "Search event" logs/business.log | jq 'select(.execution_time_ms > 3000)'
```

#### 3. Database Connection Issues

```bash
# Check database health
curl http://localhost:8000/api/v1/health | jq '.checks.database'

# View connection metrics
curl http://localhost:8000/metrics | grep db_connections
```

### Performance Tuning

#### 1. Optimize Search Performance

```python
# Add search result caching
from app.monitoring.metrics import track_search_metrics

@track_search_metrics
async def cached_search(query: str):
    # Implementation with caching
    pass
```

#### 2. Database Connection Pooling

```python
# Monitor connection pool
from app.monitoring.metrics import metrics_collector

# Update connection count
metrics_collector.update_active_connections(pool.size())
```

## 📋 Maintenance

### Daily Tasks

1. **Check Health Status**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. **Review Error Logs**
   ```bash
   tail -100 logs/fixgenie.log | grep -i error
   ```

3. **Monitor Resource Usage**
   ```bash
   curl http://localhost:8000/metrics | grep -E "(cpu|memory|disk)"
   ```

### Weekly Tasks

1. **Analyze Search Patterns**
   ```bash
   curl http://localhost:8000/api/v1/analytics/search-patterns
   ```

2. **Review Performance Metrics**
   ```bash
   curl http://localhost:8000/api/v1/analytics/performance-metrics
   ```

3. **Check Alert History**
   ```bash
   grep "Alert triggered" logs/fixgenie.log | tail -20
   ```

### Monthly Tasks

1. **Log Rotation Cleanup**
   ```bash
   find logs/ -name "*.log.*" -mtime +30 -delete
   ```

2. **Performance Baseline Review**
3. **Alert Rule Optimization**
4. **Dashboard Updates**

## 🎯 Best Practices

### 1. Monitoring Strategy

- **Monitor what matters**: Focus on user-impacting metrics
- **Set meaningful thresholds**: Avoid alert fatigue
- **Use correlation IDs**: Track requests across services
- **Implement gradual degradation**: Graceful failure handling

### 2. Alerting Strategy

- **Severity levels**: Critical, High, Medium, Low
- **Escalation paths**: Team → Manager → On-call
- **Alert grouping**: Prevent spam during incidents
- **Runbook links**: Include resolution steps

### 3. Log Management

- **Structured logging**: Always use JSON format
- **Sensitive data**: Never log passwords, tokens, PII
- **Log levels**: Use appropriate levels for different events
- **Retention policies**: Balance storage costs with compliance

### 4. Performance Optimization

- **Baseline metrics**: Establish performance baselines
- **Capacity planning**: Monitor growth trends
- **Bottleneck identification**: Use profiling and tracing
- **Continuous improvement**: Regular performance reviews

## 🔗 Integration Examples

### Slack Bot Integration

```python
from app.monitoring.alerts import SlackChannel

# Custom Slack formatting
class CustomSlackChannel(SlackChannel):
    async def send_alert(self, alert):
        # Custom message formatting
        payload = {
            "text": f"🚨 FixGenie Alert: {alert.title}",
            "attachments": [
                {
                    "color": "danger" if alert.severity == "critical" else "warning",
                    "fields": [
                        {"title": "Severity", "value": alert.severity, "short": True},
                        {"title": "Component", "value": alert.labels.get("component"), "short": True}
                    ]
                }
            ]
        }
        # Send to Slack
```

### PagerDuty Integration

```python
import requests

class PagerDutyChannel(AlertChannel):
    def __init__(self, integration_key):
        self.integration_key = integration_key
        
    async def send_alert(self, alert):
        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": alert.title,
                "severity": alert.severity.value,
                "source": "FixGenie"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload
            )
```

## 📞 Support

For monitoring system support:

1. **Check logs**: `logs/fixgenie.log`
2. **Health status**: `GET /api/v1/health`
3. **Metrics**: `GET /metrics`
4. **Documentation**: This guide
5. **Team contact**: monitoring-team@yourcompany.com

---

**🎉 Your FixGenie monitoring system is now fully operational!**

The system will automatically:
- ✅ Collect comprehensive metrics
- ✅ Monitor system health
- ✅ Generate structured logs
- ✅ Send intelligent alerts
- ✅ Track business metrics
- ✅ Provide performance insights

Monitor your system at: `http://localhost:8000/api/v1/health`
