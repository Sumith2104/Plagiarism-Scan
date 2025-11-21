from typing import List
from sentence_transformers import SentenceTransformer

class Chunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        """
        Splits text into overlapping chunks.
        Simple character-based chunking for now. 
        TODO: Implement token-based chunking for better precision.
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk = text[start:end]
            
            # Adjust end to nearest whitespace to avoid splitting words
            if end < text_len:
                last_space = chunk.rfind(' ')
                if last_space != -1:
                    end = start + last_space + 1
                    chunk = text[start:end]
            
            chunks.append(chunk.strip())
            start += self.chunk_size - self.overlap
            
        return chunks

class EmbeddingModel:
    _instance = None
    _model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        # Do NOT load model here to prevent blocking startup
        # self._model is already None from class attribute

    def encode(self, texts: List[str]) -> List[List[float]]:
        if self._model is None:
            print(f"Lazy loading embedding model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            print("Model loaded.")
            
        return self._model.encode(texts).tolist()
