import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class PlagiarismDetector:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # We expect the trained model to be saved here by the train.py script
        self.model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ai_model"))
        
        # Fallback to the base model if the trained model isn't available yet (for development/testing)
        model_name = self.model_dir if os.path.exists(self.model_dir) else "microsoft/deberta-v3-small"
        
        try:
            print(f"Loading Plagiarism Detection Model from: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name, 
                num_labels=2, 
                ignore_mismatched_sizes=True # In case base model doesn't match 2 labels initially
            )
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()
            self.is_ready = True
        except Exception as e:
            print(f"Error loading model: {e}")
            self.is_ready = False

    def compare_texts(self, text1: str, text2: str) -> dict:
        """
        Compares two texts and returns a plagiarism score and label.
        
        Returns:
            dict containing:
                - score (float): 0-100 probability of being plagiarized
                - label (str): "Not Plagiarized", "Partially Plagiarized", or "Highly Plagiarized"
                - confidence (float): The model's confidence in its prediction
        """
        if not self.is_ready:
            return {
                "score": 0.0,
                "label": "Error: Model not loaded",
                "confidence": 0.0
            }

        # Truncate texts roughly if they are extremely long before tokenizing to save memory
        # A robust solution would chunk the documents and compare chunks. 
        # Here we do a single pass (up to 512 tokens).
        
        try:
            inputs = self.tokenizer(
                text1, 
                text2, 
                padding=True, 
                truncation=True, 
                max_length=512, 
                return_tensors="pt"
            )
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                
                # Assuming index 1 is 'Plagiarized/Semantic Equivalence'
                plagiarism_prob = probs[0][1].item() * 100 
                
            # Classify based on probability
            if plagiarism_prob < 30.0:
                label = "Not Plagiarized"
            elif plagiarism_prob < 70.0:
                label = "Partially Plagiarized"
            else:
                label = "Highly Plagiarized"
                
            return {
                "score": round(plagiarism_prob, 2),
                "label": label,
                "confidence": round(max(probs[0]).item() * 100, 2)
            }
            
        except Exception as e:
            print(f"Inference failed: {e}")
            return {
                "score": 0.0,
                "label": "Inference Error",
                "confidence": 0.0,
                "error": str(e)
            }
