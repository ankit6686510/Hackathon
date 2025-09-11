# SherlockAI - AI-Powered Issue Intelligence System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://www.typescriptlang.org/)

> **SherlockAI** is an industry-grade AI-powered issue intelligence system designed for engineering teams. It helps engineers instantly find and reuse fixes from past production issues using semantic search and AI-generated solutions.

## 🎯 Project Overview

SherlockAI transforms tribal knowledge into AI-augmented institutional memory, reducing Mean Time To Resolve (MTTR) and preventing repeat incidents. When an engineer describes a current problem, the system:

- 🔍 **Searches** through historical resolved tickets using semantic similarity
- 📊 **Returns** the 3 most similar past issues with metadata and similarity scores
- 🤖 **Generates** AI-powered fix suggestions using Google Gemini
- 💬 **Provides** a ChatGPT-like interface for seamless interaction
- 📈 **Tracks** analytics and feedback for continuous improvement

## ✨ Key Features

### 🔧 Core Functionality
- **Semantic Search Engine**: Vector-based similarity search using Google Gemini embeddings
- **AI Fix Summarizer**: Context-aware solution generation with Google Gemini 1.5 Flash
- **Smart Query Classification**: Automatically handles greetings, capability queries, and technical issues
- **Fallback AI Solutions**: Generates comprehensive troubleshooting guides when no historical matches exist

### 🎨 User Experience
- **ChatGPT-like Interface**: Modern, responsive chat UI with dark theme
- **Multi-line Input**: Shift+Enter support for complex queries
- **Real-time Typing Indicators**: Visual feedback during AI processing
- **Share & Export**: Copy conversations to clipboard
- **Conversation Management**: Delete chat history with confirmation
- **Responsive Design**: Works seamlessly on desktop and mobile

### 🏗️ Enterprise Features
- **Analytics Dashboard**: Search patterns, performance metrics, and user feedback
- **Feedback System**: Rate solutions and provide comments for improvement
- **Caching Layer**: Redis-based caching for improved performance
- **Rate Limiting**: Protect against abuse with configurable limits
- **Structured Logging**: Comprehensive logging with request tracing
- **Health Monitoring**: Service health checks and metrics
- **Error Tracking**: Sentry integration for production monitoring

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **AI/ML**: Google Gemini (text-embedding-004, gemini-1.5-flash)
- **Vector Database**: Pinecone
- **Database**: PostgreSQL with SQLAlchemy
- **Cache**: Redis
- **Monitoring**: Sentry, Structured Logging
- **Security**: Rate limiting, CORS, input validation

### Frontend
- **Framework**: React 18 with TypeScript
- **Styling**: CSS3 with modern features (backdrop-filter, gradients)
- **Animations**: Framer Motion
- **Build Tool**: Vite
- **State Management**: React Hooks

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Development**: Hot reload, auto-formatting
- **Production**: Environment-based configuration

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose (optional)
- Google AI API key
- Pinecone API key

### 1. Clone Repository
```bash
git clone https://github.com/your-org/SherlockAI.git
cd SherlockAI
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 3. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
# Configure frontend environment variables
```

### 4. Database Setup
```bash
# Start PostgreSQL and Redis (using Docker)
docker-compose up -d postgres redis

# Run database migrations
python -m alembic upgrade head
```

### 5. Train the Model
```bash
# Load sample data and generate embeddings
python train_model.py
```

### 6. Start Services
```bash
# Terminal 1: Start backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### 7. Access Application
- **Frontend**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## 📁 Project Structure

```
SherlockAI/
├── app/                          # Backend application
│   ├── api/                      # API endpoints
│   │   ├── search.py            # Search functionality
│   │   ├── health.py            # Health checks
│   │   └── analytics.py         # Analytics & feedback
│   ├── services/                # Business logic
│   │   └── ai_service.py        # AI/ML operations
│   ├── models.py                # Database models
│   ├── database.py              # Database configuration
│   ├── config.py                # Application settings
│   └── main.py                  # FastAPI application
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── App.tsx              # Main application component
│   │   ├── styles.css           # Global styles
│   │   └── main.tsx             # Application entry point
│   ├── package.json             # Dependencies
│   └── vite.config.ts           # Build configuration
├── issues.json                  # Sample training data
├── train_model.py               # Model training script
├── docker-compose.yml           # Docker services
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```bash
# Application
DEBUG=true
ENVIRONMENT=development

# AI Services
GEMINI_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=juspay-issues

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/SherlockAI
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your_secret_key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Monitoring (optional)
SENTRY_DSN=your_sentry_dsn
```

#### Frontend (frontend/.env)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=SherlockAI
```

## 📊 API Documentation

### Search Endpoints
- `POST /api/v1/search` - Semantic search for issues
- `GET /api/v1/search/capabilities` - Get system capabilities
- `GET /api/v1/search/suggestions` - Get search suggestions
- `GET /api/v1/search/history` - Get search history

### Analytics Endpoints
- `POST /api/v1/analytics/feedback` - Submit feedback
- `GET /api/v1/analytics/dashboard` - Analytics dashboard
- `GET /api/v1/analytics/search-patterns` - Search patterns analysis
- `GET /api/v1/analytics/performance-metrics` - Performance metrics

### Health & Monitoring
- `GET /api/v1/health` - Service health check
- `GET /api/v1/info` - API information
- `GET /` - Root endpoint with basic info

## 🎯 Usage Examples

### Basic Search
```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "UPI payment failed with error 5003",
    "top_k": 3,
    "search_type": "semantic"
  }'
```

### Submit Feedback
```bash
curl -X POST "http://localhost:8000/api/v1/analytics/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "API timeout error",
    "result_id": "JSP-1234",
    "rating": 5,
    "helpful": true,
    "feedback_text": "Very helpful solution!"
  }'
```

## 🔍 Sample Queries

Try these example queries in the chat interface:

**Payment Issues:**
- "UPI payment failed with error 5003"
- "Payment gateway timeout after 30 seconds"
- "Webhook retries exhausted"

**API Problems:**
- "API returning 500 internal server error"
- "Database connection timeout"
- "SSL certificate validation failed"

**General Queries:**
- "What can you help with?"
- "Show me your capabilities"
- "Hello" (for greeting response)

## 📈 Analytics & Monitoring

### Performance Metrics
- Search execution times (P50, P90, P95, P99)
- Success/failure rates
- Popular search terms
- User feedback scores

### Dashboard Features
- Real-time search analytics
- Performance trends
- Feedback summary
- Error rate monitoring

## 🧪 Testing

### Backend Tests
```bash
# Run API tests
python -m pytest tests/

# Test specific endpoints
python debug_api_search.py
python test_api_issue.py
```

### Frontend Testing
```bash
cd frontend
npm test
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build and start all services
docker-compose up --build

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment
1. Set production environment variables
2. Build frontend: `npm run build`
3. Start backend with production WSGI server
4. Configure reverse proxy (nginx)
5. Set up SSL certificates
6. Configure monitoring and logging

## 🔒 Security Considerations

- **API Keys**: Store securely in environment variables
- **Rate Limiting**: Configured to prevent abuse
- **Input Validation**: All inputs validated and sanitized
- **CORS**: Properly configured for production
- **Error Handling**: No sensitive information in error responses
- **Logging**: Structured logging without sensitive data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Add tests for new features
- Update documentation
- Ensure all tests pass

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google AI** for Gemini API
- **Pinecone** for vector database
- **FastAPI** for the excellent web framework
- **React** and **Framer Motion** for the frontend
- **Juspay** for the inspiration and use case

## 📞 Support

For support and questions:
- 📧 Email: support@SherlockAI.dev
- 💬 Slack: #SherlockAI-support
- 📖 Documentation: [docs.SherlockAI.dev](https://docs.SherlockAI.dev)
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/SherlockAI/issues)

---

**Built with ❤️ for engineering teams who want to learn from the past and solve problems faster.**
