from datasketch import MinHash
from typing import List
import re

class LexicalFingerprint:
    def __init__(self, num_perm: int = 128):
        self.num_perm = num_perm

    def generate_fingerprint(self, text: str) -> List[int]:
        """
        Generates a MinHash signature for the given text.
        """
        m = MinHash(num_perm=self.num_perm)
        
        # Simple shingling (3-grams)
        # Normalize first
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        
        for i in range(len(words) - 2):
            shingle = " ".join(words[i:i+3])
            m.update(shingle.encode('utf8'))
            
        return m.hashvalues.tolist() # Convert numpy array to list for JSON serialization
