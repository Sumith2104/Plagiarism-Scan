import math
import torch
from typing import List, Dict, Any
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

class PerplexityAnalyzer:
    _instance = None
    _model = None
    _tokenizer = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, model_id: str = "distilgpt2"):
        self.model_id = model_id
        # Lazy load model to prevent startup lag
    
    def _load_model(self):
        if self._model is None:
            print(f"Loading Perplexity Model ({self.model_id})...")
            try:
                import gc
                gc.collect()
                self._tokenizer = GPT2TokenizerFast.from_pretrained(self.model_id)
                self._model = GPT2LMHeadModel.from_pretrained(self.model_id)
                self._model.eval()
                print("Perplexity Model loaded.")
            except Exception as e:
                print(f"Failed to load Perplexity Model: {e}")
                raise e

    def calculate_scores(self, text: str) -> Dict[str, float]:
        """
        Calculates Perplexity and Burstiness scores.
        """
        if not text or len(text.strip()) == 0:
            return {"perplexity": 0.0, "burstiness": 0.0}

        self._load_model()
        
        # 1. Calculate Perplexity
        perplexity = self._calculate_perplexity(text)
        
        # 2. Calculate Burstiness
        burstiness = self._calculate_burstiness(text)
        
        return {
            "perplexity": round(perplexity, 2),
            "burstiness": round(burstiness, 2)
        }

    def _calculate_perplexity(self, text: str) -> float:
        """
        Calculates perplexity using GPT-2.
        Lower perplexity = More likely to be AI.
        """
        encodings = self._tokenizer(text, return_tensors="pt")
        max_length = self._model.config.n_positions
        stride = 512
        seq_len = encodings.input_ids.size(1)

        nlls = []
        prev_end_loc = 0
        for begin_loc in range(0, seq_len, stride):
            end_loc = min(begin_loc + max_length, seq_len)
            trg_len = end_loc - prev_end_loc
            input_ids = encodings.input_ids[:, begin_loc:end_loc]
            target_ids = input_ids.clone()
            target_ids[:, :-trg_len] = -100

            with torch.no_grad():
                outputs = self._model(input_ids, labels=target_ids)
                neg_log_likelihood = outputs.loss

            nlls.append(neg_log_likelihood)
            prev_end_loc = end_loc
            if end_loc == seq_len:
                break

        ppl = torch.exp(torch.stack(nlls).mean())
        return float(ppl)

    def _calculate_burstiness(self, text: str) -> float:
        """
        Calculates burstiness based on sentence length variance.
        Lower burstiness = More likely to be AI (monotonous).
        """
        import re
        # Split by period, question mark, or exclamation mark followed by space or end of string
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s for s in sentences if len(s.strip()) > 0]
        
        print(f"DEBUG: Burstiness Analysis - Text Length: {len(text)}")
        print(f"DEBUG: Sentences Found: {len(sentences)}")
        if len(sentences) > 0:
            print(f"DEBUG: First Sentence: {sentences[0][:50]}...")
        
        if len(sentences) < 2:
            print("DEBUG: Fallback triggered (Low sentence count)")
            # If only one sentence, we can't calculate variance.
            # Return 1.0 (High Burstiness) to give benefit of the doubt (Human-like)
            # instead of 0.0 which would be flagged as AI.
            return 1.0
            
        lengths = [len(s.split()) for s in sentences]
        mean_length = sum(lengths) / len(lengths)
        
        if mean_length == 0:
            return 0.0
            
        variance = sum((l - mean_length) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        
        # Coefficient of Variation (Burstiness)
        burstiness = std_dev / mean_length
        return float(burstiness)
