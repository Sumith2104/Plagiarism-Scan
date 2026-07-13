from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.scan import Scan, ScanStatus
from app.models.document import Document
from app.api.deps import get_current_user
from app.models.user import User
from app.worker import run_scan_task

router = APIRouter()

@router.post("/", response_model=dict)
def initiate_scan(
    payload: dict, # {document_id: int}
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document_id = payload.get("document_id")
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Create Scan record
    scan = Scan(
        document_id=document_id,
        initiated_by=doc.user_id, # Assuming same user for now
        status=ScanStatus.QUEUED
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Trigger Background Task
    background_tasks.add_task(run_scan_task, scan.id)

    return {"message": "Scan initiated", "scan_id": scan.id, "status": "queued"}

@router.get("/{scan_id}", response_model=dict)
def get_scan_result(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return {
        "id": scan.id,
        "document_id": scan.document_id,
        "status": scan.status,
        "score": scan.overall_score,
        "report": scan.report_data,
        "progress": scan.progress,
        "current_step": scan.current_step,
        "created_at": scan.created_at,
        "completed_at": scan.completed_at
    }

@router.get("/{scan_id}/pdf")
def download_scan_pdf(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate and download a PDF report for the scan.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    # Check authorization (assuming user can only see their own scans or is admin)
    # Note: initiated_by is stored on scan
    if scan.initiated_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to access this scan")

    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Scan is not completed yet")

    try:
        from app.core.pdf_generator import PDFGenerator
        from fastapi.responses import StreamingResponse
        import io
        
        pdf_gen = PDFGenerator(scan)
        pdf_bytes = pdf_gen.generate()
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=plagiascan_report_{scan_id}.pdf"
            }
        )
    except Exception as e:
        print(f"PDF Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

import os
import tempfile
import shutil
from fastapi import File, UploadFile
from app.core.ingestion import TextExtractor
from app.core.hf_inference import PlagiarismDetector

@router.post("/compare", response_model=dict)
def compare_documents(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...)
):
    """
    Directly compares two uploaded documents using the fine-tuned Hugging Face transformer model
    and returns a plagiarism probability score and label.
    """
    
    detector = PlagiarismDetector.get_instance()
    
    def extract_text_from_upload(upload_file: UploadFile) -> str:
        # Create a temporary file to leverage existing TextExtractor
        suffix = os.path.splitext(upload_file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            tmp_path = tmp.name
            
        try:
            text = TextExtractor.extract(tmp_path, upload_file.content_type)
            return text
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    try:
        text1 = extract_text_from_upload(file1)
        text2 = extract_text_from_upload(file2)
        
        if not text1 or not text2:
            raise HTTPException(status_code=400, detail="Could not extract text from one or both files.")
            
        # Run inference
        result = detector.compare_texts(text1, text2)
        
        return {
            "file1": file1.filename,
            "file2": file2.filename,
            "prediction": result
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

