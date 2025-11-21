# PlagiaScan

**AI-Powered Plagiarism Detection Platform**

A complete, production-ready plagiarism detection system with semantic and lexical analysis, built with FastAPI, React, and modern ML techniques.

## Features

- 🚀 **Multi-format Support**: PDF, DOCX, TXT, HTML with OCR fallback
- 🧠 **Hybrid Detection**: Semantic (embeddings) + Lexical (MinHash) matching
- 📊 **Visual Reports**: Detailed match highlighting and scoring
- 🔐 **Secure**: JWT authentication and protected routes
- ⚡ **Scalable**: Async processing with Celery workers
- 🎨 **Modern UI**: React + Tailwind CSS responsive design

## Quick Start (Local Mode)

The application is configured to run entirely locally without Docker, using SQLite and a local Vector Database.

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.10+ (for backend)

### 1. Backend Setup
Open a terminal in the `backend` folder:

```bash
cd backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize Database
python init_db.py

# 3. Start Backend Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup
Open a **new** terminal in the `frontend` folder:

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start Frontend Server
npm run dev
```

### 3. Access the App
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Architecture (Local Mode)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   React     │────▶│   FastAPI    │────▶│   SQLite    │
│  Frontend   │     │   Backend    │     │ (Local File)│
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ├────▶ Qdrant (Local Storage)
                           └────▶ Background Tasks
```

## Tech Stack

### Backend
- **FastAPI**: High-performance async API
- **Celery**: Distributed task queue
- **PostgreSQL**: Relational database
- **Qdrant**: Vector database for semantic search
- **Sentence-Transformers**: ML embeddings
- **MinHash**: Lexical fingerprinting

### Frontend
- **React**: UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **Axios**: HTTP client
- **React Router**: Navigation

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login

### Documents
- `POST /api/v1/documents/` - Upload document
- `GET /api/v1/documents/` - List documents
- `GET /api/v1/documents/{id}` - Get document

### Scans
- `POST /api/v1/scans/` - Initiate scan
- `GET /api/v1/scans/{id}` - Get scan results

## Testing

```bash
# Backend tests
cd backend
pytest

# Run specific test
pytest tests/test_ml.py
```

## Project Structure

```
plag/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Business logic
│   │   ├── db/           # Database
│   │   ├── models/       # SQLAlchemy models
│   │   └── worker.py     # Celery tasks
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/        # React pages
│       └── api.js        # API client
├── docs/
│   ├── architecture.md
│   ├── openapi.yaml
│   └── schema.sql
└── docker-compose.yml
```

## Environment Variables

Create `.env` in project root:

```env
DATABASE_URL=postgresql://plagiascan:plagiascan_dev@localhost:5432/plagiascan
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
SECRET_KEY=your-secret-key-here
```

## Development

### Add New Endpoint
1. Create route in `backend/app/api/v1/endpoints/`
2. Register in `backend/app/main.py`
3. Add tests in `backend/tests/`

### Add New Page
1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.jsx`

## Production Deployment

### Recommended Setup
- **Backend**: Deploy to cloud (AWS, GCP, Azure)
- **Database**: Managed PostgreSQL
- **Vector DB**: Qdrant Cloud or self-hosted
- **Frontend**: Vercel, Netlify, or CDN
- **Workers**: Separate worker instances

### Security Checklist
- [ ] Change `SECRET_KEY` in production
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Add rate limiting
- [ ] Set up monitoring
- [ ] Enable database backups

## License

MIT

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## Support

For issues and questions, please open a GitHub issue.
