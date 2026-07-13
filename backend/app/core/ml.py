from typing import List
# from sentence_transformers import SentenceTransformer

class Chunker:
    def __init__(self, chunk_size: int = 300, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            self.encoding = None

    def chunk_text(self, text: str) -> List[str]:
        """
        Splits text into overlapping chunks using token-based chunking.
        """
        if not text:
            return []
            
        if not self.encoding:
            # Fallback to character-based if tiktoken not available
            chunks = []
            start = 0
            text_len = len(text)
            char_chunk_size = self.chunk_size * 4 # rough estimate
            char_overlap = self.overlap * 4
            
            while start < text_len:
                end = min(start + char_chunk_size, text_len)
                chunk = text[start:end]
                if end < text_len:
                    last_space = chunk.rfind(' ')
                    if last_space != -1:
                        end = start + last_space + 1
                        chunk = text[start:end]
                chunks.append(chunk.strip())
                start += char_chunk_size - char_overlap
            return chunks

        tokens = self.encoding.encode(text)
        chunks = []
        start = 0
        tokens_len = len(tokens)

        while start < tokens_len:
            end = min(start + self.chunk_size, tokens_len)
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text.strip())
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
            try:
                import gc
                gc.collect() # Free up memory before loading
                
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                print("Model loaded successfully.")
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to load ML model: {e}")
                # Fallback or re-raise? For now, let's re-raise but log it.
                raise e
            
        return self._model.encode(texts).tolist()
