# PlagiaScan - Quick Start Guide

## ✅ Services Running

### Frontend (React)
- **URL**: http://localhost:5173
- **Status**: ✅ Running
- **Features**: Login, Upload, Dashboard, Reports

### Backend API (FastAPI)
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Status**: ✅ Running
- **Features**: Auth, Documents, Scans

## 🚀 How to Use

### 1. Open the Application
Visit: **http://localhost:5173**

### 2. Register an Account
- Click "Don't have an account? Register"
- Enter your email, password, and name
- Click "Register"

### 3. Login
- Enter your email and password
- Click "Login"

### 4. Upload a Document
- Click the file input
- Select a document (PDF, DOCX, TXT, or HTML)
- Click "Upload"
- Wait for processing (status will change to "indexed")

### 5. Scan for Plagiarism
- Find your uploaded document in the list
- Click "Scan for Plagiarism"
- View the detailed report with:
  - Overall plagiarism score
  - Matched chunks
  - Source attribution

## ⚠️ Important Notes

### Database Services
The backend is running but **database services (PostgreSQL, Qdrant, Redis) are NOT running** because Docker Desktop appears to be off.

**To fully test the application, you need to:**

1. **Start Docker Desktop**
2. **Run database services:**
   ```bash
   cd c:\Users\sumit\Downloads\plag
   docker-compose up -d db redis qdrant
   ```
3. **Restart the backend** (it will auto-reload)

### Without Databases
Currently, the app will show errors when you try to:
- Register/Login (needs PostgreSQL)
- Upload documents (needs PostgreSQL)
- Scan documents (needs Qdrant + PostgreSQL)

## 🔧 Troubleshooting

### "Connection refused" errors
- Start Docker Desktop
- Run: `docker-compose up -d db redis qdrant`

### Backend not responding
- Check if running: http://localhost:8000/docs
- Restart: Stop the backend terminal and run again

### Frontend not loading
- Check if running: http://localhost:5173
- Restart: `cd frontend && npm run dev`

## 📝 Next Steps

1. **Start Docker Desktop**
2. **Run databases**: `docker-compose up -d db redis qdrant`
3. **Test the full workflow**:
   - Register → Login → Upload → Scan → View Report

## 🎯 API Testing (Alternative)

You can also test the API directly at:
**http://localhost:8000/docs**

This provides an interactive Swagger UI to test all endpoints.
