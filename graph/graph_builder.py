from neo4j import GraphDatabase

class GraphBuilder:
    def __init__(self, uri, user, password, schema):
        """Initialize the graph builder with Neo4j connection details"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.schema = schema
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize database schema with constraints and indexes"""
        with self.driver.session() as session:
            for statement in self.schema.get_constraints_and_indexes():
                try:
                    session.run(statement)
                except Exception as e:
                    print(f"Error creating schema constraint/index: {e}")
    
    def create_graph(self, parsed_data_list):
        """Build the knowledge graph from parsed code data"""
        with self.driver.session() as session:
            # Process each file
            for file_data in parsed_data_list:
                # Create module node
                module_query, module_params = self.schema.get_module_query(file_data)
                session.run(module_query, module_params)
                
                # Create import relationships
                for import_data in file_data["imports"]:
                    import_query, import_params = self.schema.get_import_query(
                        import_data, file_data["file_path"]
                    )
                    session.run(import_query, import_params)
                
                # Create function nodes
                for function_data in file_data["functions"]:
                    function_query, function_params = self.schema.get_function_query(
                        function_data, file_data["file_path"]
                    )
                    session.run(function_query, function_params)
                
                # Create class nodes and their methods
                for class_data in file_data["classes"]:
                    class_query, class_params = self.schema.get_class_query(
                        class_data, file_data["file_path"]
                    )
                    session.run(class_query, class_params)
                    
                    # Create class methods
                    class_id = f"{file_data['file_path']}::{class_data['name']}"
                    for method_data in class_data["methods"]:
                        method_query, method_params = self.schema.get_method_query(
                            method_data, class_id
                        )
                        session.run(method_query, method_params)
                
                # Create call relationships
                for call_data in file_data["calls"]:
                    call_query, call_params = self.schema.get_call_query(
                        call_data, file_data["file_path"]
                    )
                    session.run(call_query, call_params)
    
    def add_similarity_relationship(self, source_id, target_id, similarity_score):
        """Add a similarity relationship between two functions or methods"""
        with self.driver.session() as session:
            query, params = self.schema.get_similarity_query(
                source_id, target_id, similarity_score
            )
            session.run(query, params)
    
    def query_graph(self, query_text):
        """Query the graph using natural language query"""
        # Convert natural language query to Cypher
        cypher_query = self._convert_to_cypher(query_text)
        
        # Execute Cypher query
        with self.driver.session() as session:
            result = session.run(cypher_query)
            records = list(result)
            
        # Process and return the results
        return self._process_query_results(records)
    
    def _convert_to_cypher(self, query_text):
        """Convert natural language query to Cypher query"""
        
        query_text = query_text.lower()
        
        if "function" in query_text and "call" in query_text:
            # Query for function calls
            return f"""
            MATCH (f:{self.schema.NODE_FUNCTION})-[r:{self.schema.REL_CALLS}]->(t)
            RETURN f.name as source, t.name as target, r.args as args, r.kwargs as kwargs
            LIMIT 20
            """
        elif "similar" in query_text and "function" in query_text:
            # Query for similar functions
            return f"""
            MATCH (f1)-[r:{self.schema.REL_SIMILAR_TO}]->(f2)
            RETURN f1.name as func1, f2.name as func2, r.score as similarity
            ORDER BY r.score DESC
            LIMIT 20
            """
        elif "class" in query_text and "method" in query_text:
            # Query for class methods
            return f"""
            MATCH (c:{self.schema.NODE_CLASS})<-[:{self.schema.REL_DEFINED_IN}]-(m:{self.schema.NODE_METHOD})
            RETURN c.name as class_name, m.name as method_name, m.docstring as docstring
            LIMIT 30
            """
        elif "import" in query_text:
            # Query for imports
            return f"""
            MATCH (m:{self.schema.NODE_MODULE})-[r:{self.schema.REL_IMPORTS}]->(im)
            RETURN m.name as module, im.name as imports
            LIMIT 30
            """
        else:
            # Default query for functions and their documentation
            return f"""
            MATCH (f:{self.schema.NODE_FUNCTION})
            RETURN f.name as function_name, f.docstring as docstring, f.parameters as parameters
            LIMIT 20
            """
    
    def _process_query_results(self, records):
        """Process and format query results"""
        results = []
        
        for record in records:
            # Convert Neo4j record to dict
            result_dict = dict(record)
            results.append(result_dict)
        
        return results
    
    def close(self):
        """Close the Neo4j driver connection"""
        self.driver.close()