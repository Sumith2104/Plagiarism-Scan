from unittest.mock import patch

def test_upload_file(client):
    # Mock Celery task to avoid actual execution
    with patch("app.worker.process_document.delay") as mock_task:
        file_content = b"This is a test document."
        files = {"file": ("test.txt", file_content, "text/plain")}
        
        response = client.post("/api/v1/documents/", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["status"] == "pending"
        
        mock_task.assert_called_once()

def test_get_document_404(client):
    response = client.get("/api/v1/documents/9999")
    assert response.status_code == 404
