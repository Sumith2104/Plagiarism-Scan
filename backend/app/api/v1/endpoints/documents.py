import shutil
import os
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.document import Document, DocStatus
from app.models.user import User
from app.worker import process_document
from app.api.deps import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=dict)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    user_id = current_user.id
    
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # Create DB record
    db_doc = Document(
        user_id=user_id,
        filename=file.filename,
        file_path=file_location,
        content_type=file.content_type,
        status=DocStatus.PENDING
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # Trigger Background Task
    background_tasks.add_task(process_document, db_doc.id)

    return {"message": "File uploaded successfully", "document_id": db_doc.id, "status": "pending"}

@router.get("/", response_model=List[dict])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "created_at": doc.created_at
        }
        for doc in docs
    ]

@router.get("/{document_id}", response_model=dict)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "extracted_text_preview": doc.extracted_text[:200] if doc.extracted_text else None
    }

@router.delete("/{document_id}", response_model=dict)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")

    # Delete file from filesystem
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass # File might already be gone

    # 1. Delete Vectors from Qdrant
    try:
        from app.db.vector import VectorDB
        vdb = VectorDB()
        vdb.delete_document(document_id)
    except Exception as e:
        print(f"Error deleting vectors: {e}")

    # 2. Delete associated Scans (Manual Cascade)
    from app.models.scan import Scan, ScanMatch
    # First, delete matches associated with scans of this document
    # (This happens automatically if we delete the scan and ScanMatch has cascade on scan_id, but let's be safe)
    
    # CRITICAL: Handle cases where THIS document is the SOURCE of a match in OTHER scans
    # We set source_document_id to NULL so the match record remains but points to nothing
    db.query(ScanMatch).filter(ScanMatch.source_document_id == document_id).update({ScanMatch.source_document_id: None})
    
    # Now delete scans for this document
    db.query(Scan).filter(Scan.document_id == document_id).delete()

    # 3. Delete Document Chunks (Manual Cascade)
    from app.models.document import DocumentChunk
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # 4. Delete Document
    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully"}
