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
    payload: dict,
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
        initiated_by=getattr(current_user, "id", None) or doc.user_id,
        status=ScanStatus.QUEUED,
        scan_mode="standard",
        current_step="Queued for analysis..."
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Trigger Background Task
    background_tasks.add_task(run_scan_task, scan.id)

    return {
        "message": "Plagiarism scan initiated successfully",
        "scan_id": scan.id,
        "scan_mode": "standard",
        "status": "queued"
    }

@router.get("/{scan_id}", response_model=dict)
def get_scan_result(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    rep = dict(scan.report_data or {})
    doc = scan.document or db.query(Document).filter(Document.id == scan.document_id).first()
    
    # Auto-generate or expand line_analysis and readability on the fly
    if scan.status == ScanStatus.COMPLETED and doc and doc.extracted_text:
        stored_lines = rep.get("line_analysis") or []
        doc_lines_approx = len(doc.extracted_text.splitlines())
        needs_full_lines = not stored_lines or (len(stored_lines) < 250 and doc_lines_approx > 250)

        if needs_full_lines:
            try:
                from app.core.detection import generate_line_analysis
                lines = generate_line_analysis(
                    full_text=doc.extracted_text,
                    web_matches=rep.get("web_matches", []),
                    internal_matches=rep.get("matches", []),
                    evidence_matches=rep.get("matches", []),
                    ai_detection=rep.get("ai_detection", {})
                )
                rep["line_analysis"] = lines
            except Exception as e:
                print(f"Fallback line_analysis generation error for scan {scan_id}: {e}")

        if not rep.get("readability"):
            try:
                from app.core.readability import compute_readability_metrics
                rep["readability"] = compute_readability_metrics(doc.extracted_text)
            except Exception as e:
                print(f"Fallback readability generation error for scan {scan_id}: {e}")

    return {
        "id": scan.id,
        "document_id": scan.document_id,
        "status": scan.status,
        "scan_mode": getattr(scan, "scan_mode", "standard"),
        "score": scan.overall_score,
        "report": rep,
        "agent_trace": getattr(scan, "agent_trace", None) or [],
        "citations_detected": getattr(scan, "citations_detected", None) or [],
        "progress": scan.progress,
        "current_step": scan.current_step,
        "created_at": scan.created_at,
        "completed_at": scan.completed_at
    }

@router.get("/{scan_id}/verify", response_model=dict)
def verify_scan_report(scan_id: int, db: Session = Depends(get_db)):
    """
    Publicly accessible endpoint for independent verification of document integrity and authenticity.
    """
    import hashlib
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan audit record not found")

    doc = scan.document or db.query(Document).filter(Document.id == scan.document_id).first()
    doc_text = doc.extracted_text if doc else ""
    doc_hash = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()[:16] if doc_text else "unavailable"

    rep = scan.report_data or {}
    ai_det = rep.get("ai_detection", {})
    readability = rep.get("readability", {})

    return {
        "scan_id": scan.id,
        "document_id": scan.document_id,
        "verified": True,
        "status": str(scan.status),
        "document_name": doc.filename if doc else "Document",
        "sha256_hash": f"SHA256:{doc_hash}",
        "document_hash": f"SHA256:{doc_hash}",
        "overall_score": scan.overall_score,
        "plagiarism_score": scan.overall_score,
        "ai_probability": ai_det.get("ai_probability", 0),
        "ai_label": ai_det.get("label", "N/A"),
        "verbatim_score": rep.get("verbatim_score", rep.get("internal_score", 0)),
        "paraphrase_score": rep.get("paraphrase_score", 0),
        "web_score": rep.get("web_score", 0),
        "readability": readability if isinstance(readability, dict) else {},
        "reading_level": readability.get("reading_level", "Standard") if isinstance(readability, dict) else "Standard",
        "created_at": str(scan.created_at),
        "completed_at": str(scan.completed_at) if scan.completed_at else None,
        "verification_seal": f"PLAGIASCAN-VERIFIED-AUTH-{scan.id:06d}",
        "engine_version": "PlagiaScan Forensic v3.2-DualEngine",
        "issuer": "PlagiaScan Authenticity Trust Authority"
    }

@router.post("/collusion-matrix", response_model=dict)
def get_collusion_matrix(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes pairwise cross-comparison similarity matrix across multiple documents to detect collusion.
    """
    import numpy as np
    document_ids = payload.get("document_ids", [])
    if not document_ids or len(document_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 document_ids for collusion analysis")

    docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
    if len(docs) < 2:
        raise HTTPException(status_code=400, detail="Not enough valid documents found")

    from app.core.ml import EmbeddingModel
    embedder = EmbeddingModel.get_instance()
    
    doc_vectors = []
    doc_infos = []
    for d in docs:
        text = d.extracted_text or ""
        vec = embedder.encode([text[:3000]])[0]
        doc_vectors.append(vec)
        doc_infos.append({
            "id": d.id,
            "filename": d.filename,
            "word_count": len(text.split())
        })

    matrix = []
    flagged_pairs = []
    n = len(docs)
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                sim = 100.0
            else:
                v1 = np.array(doc_vectors[i])
                v2 = np.array(doc_vectors[j])
                cos_sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
                sim = round(max(0.0, min(100.0, cos_sim * 100)), 1)
                if i < j and sim >= 40.0:
                    flagged_pairs.append({
                        "doc1_id": doc_infos[i]["id"],
                        "doc1_name": doc_infos[i]["filename"],
                        "doc2_id": doc_infos[j]["id"],
                        "doc2_name": doc_infos[j]["filename"],
                        "similarity": sim
                    })
            row.append(sim)
        matrix.append(row)

    return {
        "documents": doc_infos,
        "matrix": matrix,
        "flagged_pairs": flagged_pairs
    }

@router.get("/{scan_id}/trace", response_model=dict)
def get_scan_trace(scan_id: int, db: Session = Depends(get_db)):
    """
    Live stream / polling endpoint for the Agent's thought and action traces.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    return {
        "scan_id": scan.id,
        "status": scan.status,
        "progress": scan.progress,
        "current_step": scan.current_step,
        "agent_trace": getattr(scan, "agent_trace", None) or []
    }

@router.get("/{scan_id}/pdf")
def download_scan_pdf(
    scan_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate and download a certified PDF report for the scan.
    Publicly accessible so anyone scanning the verification QR code or viewing the certificate can download the audit report.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

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



