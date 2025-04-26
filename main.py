import os
import requests
import zipfile
import io
import shutil
from parsers.ast_extractor import ASTExtractor
from graph.graph_builder import GraphBuilder
from graph.graph_schema import GraphSchema
from retrieval.similarity import FunctionSimilarity
from retrieval.query_expander import QueryExpander
from llm.llm_prompt import LLMPromptGenerator
from llm.llm_response import LLMResponseHandler
import subprocess
import json

class GitHubCodeProcessor:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        
        # Initialize components
        self.graph_schema = GraphSchema()
        self.graph_builder = GraphBuilder(neo4j_uri, neo4j_user, neo4j_password, self.graph_schema)
        self.ast_extractor = ASTExtractor()
        self.function_similarity = FunctionSimilarity()
        self.query_expander = QueryExpander()
        self.llm_prompt_generator = LLMPromptGenerator()
        self.llm_response_handler = LLMResponseHandler()
        
        # Create temp directory for downloaded code
        self.temp_dir = "temp_repo"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Create extracted code directory
        self.extracted_code_dir = "extracted_code"
        os.makedirs(self.extracted_code_dir, exist_ok=True)
    
    def download_github_repo(self, repo_url):
        """Download a GitHub repository as a zip file"""
        if not repo_url.endswith('/'):
            repo_url += '/'
            
        zip_url = repo_url.replace('github.com', 'api.github.com/repos') + 'zipball/main'
        
        try:
            response = requests.get(zip_url)
            if response.status_code == 404:
                # Try master branch if main doesn't exist
                zip_url = repo_url.replace('github.com', 'api.github.com/repos') + 'zipball/master'
                response = requests.get(zip_url)
                
            response.raise_for_status()
            
            # Extract the zip file
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(self.temp_dir)
                
            print(f"Repository downloaded and extracted to {self.temp_dir}")
            return True
        except Exception as e:
            print(f"Error downloading repository: {e}")
            return False

    def process_repo(self, repo_url):
        """Process a GitHub repository end to end"""
        # Step 1: Download the repository
        if not self.download_github_repo(repo_url):
            return False
        
        # Step 2: Extract all Python files
        python_files = []
        for root, _, files in os.walk(self.temp_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    python_files.append(file_path)
                    
                    # Copy to extracted code directory
                    relative_path = os.path.relpath(file_path, self.temp_dir)
                    target_path = os.path.join(self.extracted_code_dir, relative_path)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(file_path, target_path)
        
        print(f"Found {len(python_files)} Python files")
        
        # Step 3: Parse code and extract AST information
        parsed_data = []
        for file_path in python_files:
            try:
                relative_path = os.path.relpath(file_path, self.temp_dir)
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                file_data = self.ast_extractor.extract(code, relative_path)
                parsed_data.append(file_data)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        
        # Step 4: Build knowledge graph
        self.graph_builder.create_graph(parsed_data)
        
        # Step 5: Calculate function similarities
        self.function_similarity.compute_similarities(parsed_data)
        
        print("Knowledge graph built successfully")
        return True
    
    def query(self, user_query):
        """Process a user query against the knowledge graph and return a response"""
        # Step 1: Expand the query using NLP techniques
        expanded_query = self.query_expander.expand(user_query)
        
        # Step 2: Retrieve relevant code snippets from graph
        results = self.graph_builder.query_graph(expanded_query)
        
        # Step 3: Generate a prompt for the LLM
        prompt = self.llm_prompt_generator.generate_prompt(user_query, results)
        
        # Step 4: Call the LLM (phi4-mini through Ollama)
        response = self.call_ollama(prompt)
        
        # Step 5: Format and return the response
        formatted_response = self.llm_response_handler.format_response(response)
        
        return formatted_response
    
    
    def call_ollama(self, prompt):
        """Call the Ollama API with phi4-mini model"""
        try:
            command = ["curl", "-X", "POST", "http://localhost:11434/api/generate", 
                        "-d", json.dumps({"model": "phi4-mini", "prompt": prompt})]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            # Ollama returns streaming JSON responses, each line is a separate JSON object
            # We need to process each line separately and collect responses
            lines = result.stdout.strip().split('\n')
            full_response = ""
            
            for line in lines:
                try:
                    # Parse each line as a separate JSON object
                    response_data = json.loads(line)
                    if "response" in response_data:
                        full_response += response_data["response"]
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON response line: {e}")
                    continue
            
            return full_response if full_response else f"Error: No valid response from Ollama"
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return f"Error: {str(e)}"
    
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            shutil.rmtree(self.temp_dir)
            print(f"Temporary directory {self.temp_dir} removed")
        except Exception as e:
            print(f"Error removing temporary directory: {e}")
            
# if __name__ == "__main__":
#     # Example usage
#     NEO4J_URI='neo4j+s://aa266ada.databases.neo4j.io'
#     NEO4J_USERNAME='neo4j'
#     NEO4J_PASSWORD='aQC5NqEvPzAfNKF4bs5RVc4OH0NukplLpICPDg2aGF4'
        
#     processor = GitHubCodeProcessor(NEO4J_URI,NEO4J_USERNAME,NEO4J_PASSWORD)
    
#     # Process a GitHub repository
#     repo_url = input("Enter GitHub repository URL: ")
#     if processor.process_repo(repo_url):
#         print("Repository processed successfully")
        
#         # Query example
#         while True:
#             user_query = input("Enter your query (or 'quit' to exit): ")
#             if user_query.lower() == 'quit':
#                 break
            
#             response = processor.query(user_query)
#             print("\nResponse:")
#             print(response)
#             print("\n" + "-"*50 + "\n")
    
#     processor.cleanup()

if __name__ == "__main__":
    # Example usage
    NEO4J_URI='neo4j+s://aa266ada.databases.neo4j.io'
    NEO4J_USERNAME='neo4j'
    NEO4J_PASSWORD='aQC5NqEvPzAfNKF4bs5RVc4OH0NukplLpICPDg2aGF4'
        
    processor = GitHubCodeProcessor(NEO4J_URI,NEO4J_USERNAME,NEO4J_PASSWORD)
    
    # Ask the user if they want to create a new knowledge graph
    create_new = input("Do you want to create a new knowledge graph? (y/n): ").lower()
    
    if create_new == 'y':
        # Process a GitHub repository
        repo_url = input("Enter GitHub repository URL: ")
        if not processor.process_repo(repo_url):
            print("Failed to process repository. Exiting.")
            processor.cleanup()
            exit(1)
        print("Repository processed successfully")
    else:
        print("Using existing knowledge graph...")
    
    # Query example
    while True:
        user_query = input("Enter your query (or 'quit' to exit): ")
        if user_query.lower() == 'quit':
            break
        
        response = processor.query(user_query)
        print("\nResponse:")
        print(response)
        print("\n" + "-"*50 + "\n")

    processor.cleanup()