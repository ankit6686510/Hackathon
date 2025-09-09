# FixGenie — AI-Powered Issue Intelligence System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5.4-blue.svg)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

> **Industry-grade AI-powered internal tool that helps Juspay engineers instantly find and reuse fixes from past production issues.**

## 🎯 Overview

FixGenie transforms tribal knowledge into AI-augmented institutional memory, reducing Mean Time To Resolve (MTTR) and preventing repeat incidents. When an engineer describes a current problem, the system:

- 🔍 **Semantic Search**: Finds similar past issues using AI embeddings
- 🤖 **AI Suggestions**: Generates actionable fix recommendations
- 📊 **Analytics**: Tracks usage patterns and effectiveness
- ⚡ **Performance**: Sub-second response times with caching
- 🔒 **Enterprise-Ready**: Authentication, rate limiting, monitoring

## 🏗️ Architecture

### Backend (FastAPI + AI)
- **FastAPI** with async/await for high performance
- **Google Gemini** for embeddings and text generation
- **Pinecone** vector database for semantic search
- **PostgreSQL** for metadata and analytics
- **Redis** for caching and session management
- **Structured logging** with request tracing
- **Prometheus metrics** and health checks

### Frontend (React + TypeScript)
- **Modern React** with hooks and TypeScript
- **Framer Motion** for smooth animations
- **Professional UI** with dark theme
- **Real-time feedback** and search suggestions
- **Responsive design** for mobile and desktop

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (recommended)
- API keys for Gemini and Pinecone

### Option 1: Docker Compose (Recommended)

1. **Clone and setup environment**:
```bash
git clone <repository>
cd fixgenie
cp .env.example .env
# Edit .env with your API keys
```

2. **Start all services**:
```bash
docker-compose up -d
```

3. **Initialize data**:
```bash
docker-compose exec api python embedder.py
```

4. **Access the application**:
- API: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

### Option 2: Local Development

1. **Backend setup**:
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database (requires PostgreSQL running)
python -c "from app.database import init_database; import asyncio; asyncio.run(init_database())"

# Generate embeddings
python embedder.py

# Start API server
uvicorn app.main:app --reload
```

2. **Frontend setup**:
```bash
cd frontend
npm install
npm run dev
```

## 📊 API Endpoints

### Core Search API
```http
POST /api/v1/search
Content-Type: application/json

{
  "query": "UPI payment failed with error 5003",
  "top_k": 3,
  "search_type": "semantic",
  "similarity_threshold": 0.7
}
```

### Health & Monitoring
- `GET /api/v1/health` - Comprehensive health check
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/metrics` - Application metrics
- `GET /api/v1/metrics/prometheus` - Prometheus format

### Search Features
- `GET /api/v1/search/suggestions` - Popular search terms
- `GET /api/v1/search/history` - Recent searches

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `PINECONE_API_KEY` | Pinecone API key | Required |
| `PINECONE_INDEX` | Pinecone index name | `juspay-issues` |
| `DATABASE_URL` | PostgreSQL connection string | Auto-generated |
| `REDIS_URL` | Redis connection string | Auto-generated |
| `SECRET_KEY` | JWT secret key | Required |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_REQUESTS` | Rate limit per window | `100` |
| `CACHE_TTL_SEARCH` | Search cache TTL (seconds) | `300` |

### Advanced Configuration

```python
# app/config.py
class Settings(BaseSettings):
    # Customize search behavior
    default_top_k: int = 3
    max_top_k: int = 10
    similarity_threshold: float = 0.7
    
    # Performance tuning
    cache_ttl_search: int = 300
    cache_ttl_embeddings: int = 3600
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
```

## 📈 Monitoring & Analytics

### Built-in Metrics
- **Search Performance**: Response times, cache hit rates
- **Usage Analytics**: Popular queries, user patterns
- **System Health**: Database, Redis, AI service status
- **Error Tracking**: Structured logging with Sentry integration

### Prometheus Metrics
```
fixgenie_searches_total - Total searches performed
fixgenie_response_time_ms - Average response time
fixgenie_cache_hits_total - Cache hit count
fixgenie_ai_requests_total - AI service requests
```

### Grafana Dashboard
Pre-configured dashboards for:
- API performance and usage
- Search analytics and trends
- System resource utilization
- Error rates and debugging

## 🔒 Security Features

### Production Security
- **Rate Limiting**: Configurable per-endpoint limits
- **Input Validation**: Pydantic models with strict validation
- **CORS Protection**: Configurable allowed origins
- **Request Tracing**: Unique request IDs for debugging
- **Error Handling**: Sanitized error responses
- **Health Checks**: Kubernetes-ready probes

### Authentication (Extensible)
```python
# Future authentication integration
from app.auth import get_current_user

@router.post("/search")
async def search_issues(
    request: SearchRequest,
    user: User = Depends(get_current_user)
):
    # Authenticated search with user context
```

## 🧪 Testing

### Run Tests
```bash
# Backend tests
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Load Testing
```bash
# Install k6
brew install k6  # macOS
# or download from https://k6.io

# Run load tests
k6 run tests/load/search_test.js
```

## 📦 Deployment

### Docker Production Build
```bash
# Build optimized image
docker build -t fixgenie:latest .

# Run with production settings
docker run -d \
  --name fixgenie-api \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DEBUG=false \
  fixgenie:latest
```

### Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fixgenie-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fixgenie-api
  template:
    metadata:
      labels:
        app: fixgenie-api
    spec:
      containers:
      - name: api
        image: fixgenie:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
```

## 🔄 Data Management

### Issue Data Format
```json
{
  "id": "JSP-1234",
  "title": "UPI Payment Failed with Error 5003",
  "description": "User reported UPI payment stuck in processing state...",
  "resolution": "Increased timeout from 10s to 30s for Axis Bank API...",
  "tags": ["UPI", "Timeout", "AxisBank", "PaymentFlow"],
  "created_at": "2024-03-12T10:30:00Z",
  "resolved_by": "john.doe@juspay.in",
  "status": "resolved",
  "priority": "high"
}
```

### Data Pipeline
```bash
# 1. Export from Jira/Zendesk
python scripts/export_jira.py --project JSP --status resolved

# 2. Anonymize sensitive data
python scripts/anonymize.py --input raw_issues.json --output issues.json

# 3. Generate embeddings
python embedder.py

# 4. Verify data quality
python scripts/validate_data.py
```

## 🛠️ Development

### Code Structure
```
├── app/                    # Main application
│   ├── api/               # API routes
│   ├── services/          # Business logic
│   ├── models.py          # Data models
│   ├── config.py          # Configuration
│   └── main.py            # FastAPI app
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   └── styles.css     # Styling
│   └── package.json
├── tests/                 # Test suites
├── scripts/               # Utility scripts
├── monitoring/            # Grafana/Prometheus config
└── docker-compose.yml     # Development environment
```

### Adding New Features

1. **New API Endpoint**:
```python
# app/api/new_feature.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["feature"])

@router.post("/new-endpoint")
async def new_feature():
    return {"status": "success"}
```

2. **New Service**:
```python
# app/services/new_service.py
class NewService:
    async def process(self, data):
        # Business logic here
        return result
```

3. **Database Migration**:
```python
# Use Alembic for database migrations
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

## 📋 Roadmap

### Phase 1: Core Features ✅
- [x] Semantic search with AI embeddings
- [x] AI-powered fix suggestions
- [x] Professional React frontend
- [x] Caching and performance optimization
- [x] Health checks and monitoring

### Phase 2: Enterprise Features 🚧
- [ ] User authentication and authorization
- [ ] Advanced analytics dashboard
- [ ] Slack/Teams integration
- [ ] Feedback learning system
- [ ] Multi-tenant support

### Phase 3: Advanced AI 🔮
- [ ] Knowledge graph construction
- [ ] Automated issue categorization
- [ ] Predictive incident detection
- [ ] Custom model fine-tuning
- [ ] Multi-modal search (code, logs, images)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Write tests for new features
- Update documentation
- Ensure Docker builds pass

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Juspay Engineering Team** for domain expertise
- **Google Gemini** for powerful AI capabilities
- **Pinecone** for vector database infrastructure
- **FastAPI** for the excellent web framework
- **React** and **TypeScript** communities

---

**Built with ❤️ for Juspay Engineers**

For questions or support, please open an issue or contact the development team.
