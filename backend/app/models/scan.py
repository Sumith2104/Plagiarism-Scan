from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum

class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    SCANNING = "scanning"
    COMPLETED = "completed"
    FAILED = "failed"

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    initiated_by = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(ScanStatus), default=ScanStatus.QUEUED)
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    overall_score = Column(Float, default=0.0)
    report_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    document = relationship("Document", backref="scans")
    user = relationship("User", backref="scans")

class ScanMatch(Base):
    __tablename__ = "scan_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    source_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    external_source_url = Column(String, nullable=True)
    similarity_score = Column(Float, nullable=False)
    matched_fragments = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    scan = relationship("Scan", backref="matches")
    source_document = relationship("Document")
