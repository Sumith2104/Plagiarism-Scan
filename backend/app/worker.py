# Celery removed for local mode
# from celery import Celery
# from app.core.config import settings

# celery_app = Celery(...)


from app.db.session import SessionLocal
from app.models.document import Document, DocStatus
from app.core.ingestion import TextExtractor
from app.core.cleaning import TextCleaner
from app.core.fingerprint import LexicalFingerprint
from app.core.ml import Chunker, EmbeddingModel
from app.db.vector import VectorDB

# @celery_app.task(name="app.worker.process_document")
def process_document(document_id: int):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            print(f"Document {document_id} not found")
            return False

        doc.status = DocStatus.PROCESSING
        db.commit()

        print(f"Extracting text for {doc.filename}...")
        try:
            # 1. Extraction
            raw_text = TextExtractor.extract(doc.file_path, doc.content_type)
            cleaned_text = TextCleaner.clean(raw_text)
            doc.extracted_text = cleaned_text
            
            # 2. Lexical Fingerprinting (MinHash)
            fingerprinter = LexicalFingerprint()
            signature = fingerprinter.generate_fingerprint(cleaned_text)
            
            # Update metadata with signature
            meta = doc.meta_data or {}
            meta["minhash_signature"] = signature
            doc.meta_data = meta
            
            # 3. Chunking
            chunker = Chunker()
            chunks = chunker.chunk_text(cleaned_text)
            
            if chunks:
                # 4. Embedding
                model = EmbeddingModel.get_instance()
                embeddings = model.encode(chunks)
                
                # 5. Indexing
                vdb = VectorDB()
                vdb.upsert_chunks(doc.id, chunks, embeddings)
                
                doc.status = DocStatus.INDEXED
            else:
                print("No text chunks to index.")
                doc.status = DocStatus.INDEXED 
                
        except Exception as e:
            print(f"Processing failed: {e}")
            doc.status = DocStatus.FAILED
            doc.meta_data = {"error": str(e)}
            import traceback
            traceback.print_exc()
        
        db.commit()
        return True
    finally:
        db.close()

from app.core.detection import DetectionEngine

# # @celery_app.task(name="app.worker.run_scan_task")
def run_scan_task(scan_id: int):
    db = SessionLocal()
    try:
        engine = DetectionEngine(db)
        engine.run_scan(scan_id)
        return True
    finally:
        db.close()
