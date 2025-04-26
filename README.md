# Code Base Knowledge Graph

This project builds a knowledge graph from a GitHub repository's code, enabling semantic code search and understanding through a Neo4j graph database and LLM integration.

## Overview

The system:
1. Downloads a GitHub repository
2. Parses Python code using AST
3. Builds a Neo4j knowledge graph of code elements and relationships
4. Provides query capabilities using natural language
5. Uses phi4-mini from Ollama for responses

## Components

- **AST Extractor**: Parses Python code to extract functions, classes, and relationships
- **Graph Builder**: Converts parsed code into Neo4j nodes and relationships
- **Graph Schema**: Defines the knowledge graph structure
- **Function Similarity**: Calculates code similarity through AST comparison and embeddings  
- **Query Expander**: Improves natural language queries with code-specific terms
- **LLM Integration**: Processes queries and generates responses using phi4-mini

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Install Ollama and the phi4-mini model:
   ```
   # Install Ollama (instructions vary by OS)
   # https://ollama.ai/download
   
   # Pull the phi4-mini model
   ollama pull phi4-mini
   ```

3. Set up Neo4j AuraDB:
   - Create a free account at https://neo4j.com/cloud/aura/
   - Create a new database instance
   - Get your connection URI, username, and password

4. Update the Neo4j credentials in `main.py`

## Usage

Run the main script:
```
python main.py
```

You'll be prompted to:
1. Enter a GitHub repository URL
2. Ask questions about the code once processing is complete

## Example Queries

- "Find functions that call the database"
- "What does the authentication module do?"
- "Show me similar functions to the login function"
- "How are users validated in the system?"

## Project Structure

```
├── extracted_code/        # Directory for extracted code files
├── main.py                # Main entry point
├── parsers/
│   └── ast_extractor.py   # Code parsing using AST
├── graph/
│   ├── graph_builder.py   # Neo4j graph construction
│   └── graph_schema.py    # Graph schema definitions
├── retrieval/
│   ├── similarity.py      # Function similarity calculation
│   └── query_expander.py  # Query expansion for better results
└── llm/
    ├── llm_prompt.py      # LLM prompt generation
    └── llm_response.py    # LLM response handling
```