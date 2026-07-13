# Celery removed for local mode
# from celery import Celery
# from app.core.config import settings

# celery_app = Celery(...)


import os
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
            # In Fluxbase mode, the file_path is the S3 Key.
            # If the local file doesn't exist, download it from S3!
            local_path = doc.file_path
            from app.core.config import settings
            if settings.use_fluxbase:
                if not os.path.exists(local_path):
                    try:
                        from app.db.fluxbase import get_fluxbase_client
                        import requests
                        
                        client = get_fluxbase_client()
                        presigned_url = client.get_file_url(doc.file_path)
                        print(f"Downloading file from Fluxbase S3: {presigned_url}")
                        resp = requests.get(presigned_url, timeout=30)
                        resp.raise_for_status()
                        
                        os.makedirs("uploads", exist_ok=True)
                        temp_path = os.path.join("uploads", doc.filename)
                        with open(temp_path, "wb") as f:
                            f.write(resp.content)
                        local_path = temp_path
                        print(f"Downloaded S3 file to local path: {local_path}")
                    except Exception as ex:
                        print(f"Failed to fetch S3 file: {ex}")

            # 1. Extraction
            print(f"DEBUG: Starting extraction for {doc.filename}...")
            raw_text = TextExtractor.extract(local_path, doc.content_type)
            print(f"DEBUG: Extraction complete. Length: {len(raw_text)}")
            
            cleaned_text = TextCleaner.clean(raw_text)
            doc.extracted_text = cleaned_text
            
            # 2. Lexical Fingerprinting (MinHash)
            print("DEBUG: Generating fingerprint...")
            fingerprinter = LexicalFingerprint()
            signature = fingerprinter.generate_fingerprint(cleaned_text)
            
            # Update metadata with signature
            meta = doc.meta_data or {}
            meta["minhash_signature"] = signature
            doc.meta_data = meta
            
            # 3. Chunking
            print("DEBUG: Chunking text...")
            chunker = Chunker()
            chunks = chunker.chunk_text(cleaned_text)
            print(f"DEBUG: Generated {len(chunks)} chunks.")
            
            if chunks:
                # 4. Embedding
                print("DEBUG: Loading Embedding Model (this might take a while)...")
                model = EmbeddingModel.get_instance()
                print("DEBUG: Model loaded. Encoding chunks...")
                embeddings = model.encode(chunks)
                print("DEBUG: Encoding complete.")
                
                # 5. Indexing
                print("DEBUG: Indexing to Qdrant...")
                vdb = VectorDB()
                vdb.upsert_chunks(doc.id, chunks, embeddings)
                print("DEBUG: Indexing complete.")
                
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
