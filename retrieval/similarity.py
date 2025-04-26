import difflib
import hashlib
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

class FunctionSimilarity:
    def __init__(self):
        """Initialize the function similarity calculator"""
        self.embedding_cache = {}
        self.threshold = 0.7  # Similarity threshold
        
        # Load CodeBERT model and tokenizer
        print("Loading CodeBERT model and tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        self.model = AutoModel.from_pretrained("microsoft/codebert-base")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        print(f"CodeBERT model loaded on {self.device}")
    
    def compute_similarities(self, parsed_data_list):
        """Compute similarities between functions"""
        # Extract all functions from parsed data
        all_functions = []
        
        for file_data in parsed_data_list:
            file_path = file_data["file_path"]
            
            # Add standalone functions
            for func in file_data["functions"]:
                func_id = f"{file_path}::{func['name']}"
                all_functions.append({
                    "id": func_id,
                    "name": func["name"],
                    "body": func["body"],
                    "docstring": func["docstring"],
                    "parameters": func["parameters"]
                })
            
            # Add class methods
            for cls in file_data["classes"]:
                class_name = cls["name"]
                for method in cls["methods"]:
                    method_id = f"{file_path}::{class_name}::{method['name']}"
                    all_functions.append({
                        "id": method_id,
                        "name": f"{class_name}.{method['name']}",
                        "body": method["body"],
                        "docstring": method["docstring"],
                        "parameters": method["parameters"]
                    })
        
        # Compare all functions pairwise
        similarities = []
        
        for i, func1 in enumerate(all_functions):
            for j, func2 in enumerate(all_functions):
                # Skip self-comparison and already processed pairs
                if i >= j:
                    continue
                
                # Calculate similarity score
                structural_sim = self._ast_similarity(func1, func2)
                semantic_sim = self._semantic_similarity(func1, func2)
                
                # Combined similarity score
                combined_sim = 0.6 * structural_sim + 0.4 * semantic_sim
                
                # Only store if above threshold
                if combined_sim >= self.threshold:
                    similarities.append({
                        "source_id": func1["id"],
                        "target_id": func2["id"],
                        "score": combined_sim
                    })
        
        return similarities
    
    def _ast_similarity(self, func1, func2):
        """Calculate structural similarity between two functions"""
        # Use function body for comparison
        similarity = difflib.SequenceMatcher(None, func1["body"], func2["body"]).ratio()
        
        # Adjust based on parameter similarity
        param_sim = self._parameter_similarity(func1["parameters"], func2["parameters"])
        
        # Final structural similarity is weighted average
        return 0.8 * similarity + 0.2 * param_sim
    
    def _parameter_similarity(self, params1, params2):
        """Calculate similarity between function parameters"""
        if not params1 and not params2:
            return 1.0  # Both have no parameters
        
        if not params1 or not params2:
            return 0.0  # One has parameters, other doesn't
        
        # Get parameter names
        names1 = [p["name"] for p in params1]
        names2 = [p["name"] for p in params2]
        
        # Compute Jaccard similarity
        intersection = set(names1).intersection(set(names2))
        union = set(names1).union(set(names2))
        
        return len(intersection) / len(union) if union else 0.0
    
    def _semantic_similarity(self, func1, func2):
        """Calculate semantic similarity using CodeBERT embeddings"""
        # Combine function name, docstring and body for semantic meaning
        text1 = f"{func1['name']} {func1['docstring']} {func1['body']}"
        text2 = f"{func2['name']} {func2['docstring']} {func2['body']}"
        
        # Get embeddings (cache to avoid redundant computation)
        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)
        
        # Calculate cosine similarity
        similarity = self._cosine_similarity(emb1, emb2)
        return similarity
    
    def _get_embedding(self, text):
        """Get CodeBERT embedding for text (cached)"""
        # Use a hash of the text as cache key
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        # Generate embedding using CodeBERT
        embedding = self._generate_codebert_embedding(text)
        
        # Cache the embedding
        self.embedding_cache[text_hash] = embedding
        return embedding
    
    def _generate_codebert_embedding(self, text):
        """Generate embedding using CodeBERT model"""
        # Truncate text if too long
        max_length = self.tokenizer.model_max_length
        
        # Tokenize the text
        inputs = self.tokenizer(
            text, 
            return_tensors="pt", 
            padding=True, 
            truncation=True, 
            max_length=max_length
        )
        
        # Move inputs to the same device as the model
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get model output
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        # Use the [CLS] token embedding as the code embedding
        embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
        
        # Normalize the embedding
        normalized_embedding = embedding / np.linalg.norm(embedding)
        
        return normalized_embedding
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        return np.dot(vec1, vec2)