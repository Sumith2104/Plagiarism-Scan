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
        "created_at": scan.created_at,
        "completed_at": scan.completed_at
    }
