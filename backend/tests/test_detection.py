import pytest
from unittest.mock import MagicMock, patch
from app.core.detection import DetectionEngine
from app.models.scan import Scan, ScanStatus
from app.models.document import Document

@patch("app.core.detection.VectorDB")
@patch("app.core.detection.EmbeddingModel")
@patch("app.core.detection.Chunker")
def test_run_scan(mock_chunker_cls, mock_emb_cls, mock_vdb_cls):
    # Setup Mocks
    mock_chunker = MagicMock()
    mock_chunker.chunk_text.return_value = ["chunk1", "chunk2"]
    mock_chunker_cls.return_value = mock_chunker

    mock_emb = MagicMock()
    mock_emb.encode.return_value = [[0.1], [0.2]]
    mock_emb_cls.get_instance.return_value = mock_emb

    mock_vdb = MagicMock()
    # Return a match for the first chunk, no match for second
    mock_vdb.search.side_effect = [
        [{"document_id": 2, "text": "match", "score": 0.9}], # Result for chunk1
        [] # Result for chunk2
    ]
    mock_vdb_cls.return_value = mock_vdb

    # Setup DB Mock
    mock_db = MagicMock()
    mock_scan = MagicMock()
    mock_scan.id = 1
    mock_scan.document.id = 1
    mock_scan.document.extracted_text = "test text"
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_scan

    # Run Engine
    engine = DetectionEngine(mock_db)
    engine.run_scan(1)

    # Assertions
    assert mock_scan.status == ScanStatus.COMPLETED
    assert mock_scan.overall_score == 50.0 # 1 out of 2 chunks matched
    assert mock_scan.report_data["matched_chunks"] == 1
