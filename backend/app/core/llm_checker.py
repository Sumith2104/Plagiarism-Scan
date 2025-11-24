import logging
import os
from huggingface_hub import hf_hub_download
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

logger = logging.getLogger(__name__)

class LLMChecker:
    _instance = None
    _model = None
    
    # Model details
    REPO_ID = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
    FILENAME = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if Llama is None:
            logger.warning("llama-cpp-python not installed. LLM Check disabled.")
            return

        try:
            logger.info(f"Downloading/Loading LLM: {self.FILENAME}...")
            model_path = hf_hub_download(repo_id=self.REPO_ID, filename=self.FILENAME)
            
            # Load model
            # n_gpu_layers=-1 tries to offload all to GPU. 
            # If no GPU support compiled, it ignores it.
            # n_ctx=2048 is standard context window.
            self._model = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_gpu_layers=0, # Force CPU to avoid GGML assertion failures on some Windows setups
                verbose=False
            )
            logger.info("LLM loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            self._model = None

    def analyze_text(self, text: str) -> dict:
        """
        Analyzes text using Mistral-7B to detect AI generation.
        """
        if not self._model:
            return {"error": "LLM not loaded"}

        # Truncate text to fit context (approx 1500 tokens to leave room for prompt)
        truncated_text = text[:6000] 

        prompt = f"""[INST] You are an expert AI detection system. Analyze the following text and determine if it was written by an AI or a Human.
        
        Text: "{truncated_text}"
        
        Provide your analysis in JSON format with two keys:
        1. "is_ai": boolean (true/false)
        2. "reason": string (brief explanation)
        
        JSON Response: [/INST]"""

        try:
            output = self._model(
                prompt,
                max_tokens=200,
                stop=["</s>"],
                echo=False
            )
            
            response_text = output['choices'][0]['text'].strip()
            logger.info(f"LLM Response: {response_text}")
            
            # Simple parsing (robustness improvement needed for prod)
            is_ai = "true" in response_text.lower()
            
            return {
                "is_ai": is_ai,
                "analysis": response_text
            }
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {"error": str(e)}
