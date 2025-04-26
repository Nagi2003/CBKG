class GraphSchema:
    """Define the schema for the Neo4j knowledge graph"""
    
    def __init__(self):
        # Define node labels
        self.NODE_MODULE = "Module"
        self.NODE_FUNCTION = "Function"
        self.NODE_CLASS = "Class"
        self.NODE_METHOD = "Method"
        
        # Define relationship types
        self.REL_IMPORTS = "IMPORTS"
        self.REL_DEFINED_IN = "DEFINED_IN"
        self.REL_CONTAINS = "CONTAINS"
        self.REL_CALLS = "CALLS"
        self.REL_INHERITS_FROM = "INHERITS_FROM"
        self.REL_SIMILAR_TO = "SIMILAR_TO"
        
    def get_constraints_and_indexes(self):
        """Return Cypher statements for constraints and indexes"""
        constraints = [
            f"CREATE CONSTRAINT module_path IF NOT EXISTS FOR (m:{self.NODE_MODULE}) REQUIRE m.path IS UNIQUE",
            f"CREATE CONSTRAINT function_id IF NOT EXISTS FOR (f:{self.NODE_FUNCTION}) REQUIRE f.id IS UNIQUE",
            f"CREATE CONSTRAINT class_id IF NOT EXISTS FOR (c:{self.NODE_CLASS}) REQUIRE c.id IS UNIQUE",
            f"CREATE CONSTRAINT method_id IF NOT EXISTS FOR (m:{self.NODE_METHOD}) REQUIRE m.id IS UNIQUE"
        ]
        
        indexes = [
            f"CREATE INDEX module_name IF NOT EXISTS FOR (m:{self.NODE_MODULE}) ON (m.name)",
            f"CREATE INDEX function_name IF NOT EXISTS FOR (f:{self.NODE_FUNCTION}) ON (f.name)",
            f"CREATE INDEX class_name IF NOT EXISTS FOR (c:{self.NODE_CLASS}) ON (c.name)",
            f"CREATE INDEX method_name IF NOT EXISTS FOR (m:{self.NODE_METHOD}) ON (m.name)"
        ]
        
        return constraints + indexes
    
    def get_module_query(self, module_data):
        """Generate Cypher query for creating a module node"""
        query = f"""
        MERGE (m:{self.NODE_MODULE} {{path: $path}})
        SET m.name = $name,
            m.docstring = $docstring
        RETURN m
        """
        
        params = {
            "path": module_data["file_path"],
            "name": module_data["module_name"],
            "docstring": module_data["module_docstring"]
        }
        
        return query, params
    
    def get_function_query(self, function_data, module_path):
        """Generate Cypher query for creating a function node"""
        # Create a unique ID for the function
        function_id = f"{module_path}::{function_data['name']}"
        
        query = f"""
        MATCH (m:{self.NODE_MODULE} {{path: $module_path}})
        MERGE (f:{self.NODE_FUNCTION} {{id: $id}})
        SET f.name = $name,
            f.docstring = $docstring,
            f.parameters = $parameters,
            f.return_annotation = $return_annotation,
            f.body = $body,
            f.line_number = $line_number
        MERGE (f)-[:{self.REL_DEFINED_IN}]->(m)
        RETURN f
        """
        
        params = {
            "id": function_id,
            "module_path": module_path,
            "name": function_data["name"],
            "docstring": function_data["docstring"],
            "parameters": [p["name"] for p in function_data["parameters"]],
            "return_annotation": function_data["return_annotation"],
            "body": function_data["body"],
            "line_number": function_data["line_number"]
        }
        
        return query, params
    
    def get_class_query(self, class_data, module_path):
        """Generate Cypher query for creating a class node"""
        # Create a unique ID for the class
        class_id = f"{module_path}::{class_data['name']}"
        
        query = f"""
        MATCH (m:{self.NODE_MODULE} {{path: $module_path}})
        MERGE (c:{self.NODE_CLASS} {{id: $id}})
        SET c.name = $name,
            c.docstring = $docstring,
            c.bases = $bases,
            c.line_number = $line_number
        MERGE (c)-[:{self.REL_DEFINED_IN}]->(m)
        RETURN c
        """
        
        params = {
            "id": class_id,
            "module_path": module_path,
            "name": class_data["name"],
            "docstring": class_data["docstring"],
            "bases": class_data["bases"],
            "line_number": class_data["line_number"]
        }
        
        return query, params
    
    def get_method_query(self, method_data, class_id):
        """Generate Cypher query for creating a method node"""
        # Create a unique ID for the method
        method_id = f"{class_id}::{method_data['name']}"
        
        query = f"""
        MATCH (c:{self.NODE_CLASS} {{id: $class_id}})
        MERGE (m:{self.NODE_METHOD} {{id: $id}})
        SET m.name = $name,
            m.docstring = $docstring,
            m.parameters = $parameters,
            m.return_annotation = $return_annotation,
            m.body = $body,
            m.line_number = $line_number
        MERGE (m)-[:{self.REL_DEFINED_IN}]->(c)
        RETURN m
        """
        
        params = {
            "id": method_id,
            "class_id": class_id,
            "name": method_data["name"],
            "docstring": method_data["docstring"],
            "parameters": [p["name"] for p in method_data["parameters"]],
            "return_annotation": method_data["return_annotation"],
            "body": method_data["body"],
            "line_number": method_data["line_number"]
        }
        
        return query, params
    
    def get_import_query(self, import_data, module_path):
        """Generate Cypher query for creating an import relationship"""
        query = f"""
        MATCH (m:{self.NODE_MODULE} {{path: $module_path}})
        MERGE (im:{self.NODE_MODULE} {{name: $import_module}})
        MERGE (m)-[r:{self.REL_IMPORTS}]->(im)
        SET r.alias = $alias
        RETURN r
        """
        
        params = {
            "module_path": module_path,
            "import_module": import_data["module"],
            "alias": import_data["alias"]
        }
        
        return query, params
    
    def get_call_query(self, call_data, module_path):
        """Generate Cypher query for creating a call relationship"""
        # Parse source and target to handle methods
        source_parts = call_data["source"].split(".")
        target_parts = call_data["target"].split(".")
        
        # Determine if the source is a method or function
        if len(source_parts) > 1:
            # Source is a method
            source_class = source_parts[0]
            source_method = source_parts[1]
            source_id = f"{module_path}::{source_class}::{source_method}"
            source_match = f"""
            MATCH (sm:{self.NODE_METHOD} {{id: $source_id}})
            """
        else:
            # Source is a function
            source_id = f"{module_path}::{source_parts[0]}"
            source_match = f"""
            MATCH (sm:{self.NODE_FUNCTION} {{id: $source_id}})
            """
        
        # Determine query based on if target is fully qualified or not
        if "." in call_data["target"]:
            # Target might be a method or attribute
            query = f"""
            {source_match}
            MERGE (t:CodeEntity {{name: $target}})
            MERGE (sm)-[r:{self.REL_CALLS}]->(t)
            SET r.args = $args,
                r.kwargs = $kwargs,
                r.line_number = $line_number
            RETURN r
            """
        else:
            # Target is likely a function
            query = f"""
            {source_match}
            MERGE (t:{self.NODE_FUNCTION} {{name: $target}})
            MERGE (sm)-[r:{self.REL_CALLS}]->(t)
            SET r.args = $args,
                r.kwargs = $kwargs,
                r.line_number = $line_number
            RETURN r
            """
        
        params = {
            "source_id": source_id,
            "target": call_data["target"],
            "args": call_data["args"],
            "kwargs": call_data["kwargs"],
            "line_number": call_data["line_number"]
        }
        
        return query, params
    
    def get_similarity_query(self, source_id, target_id, similarity_score):
        """Generate Cypher query for creating a similarity relationship"""
        query = f"""
        MATCH (source) WHERE source.id = $source_id
        MATCH (target) WHERE target.id = $target_id
        MERGE (source)-[r:{self.REL_SIMILAR_TO}]->(target)
        SET r.score = $score
        RETURN r
        """
        
        params = {
            "source_id": source_id,
            "target_id": target_id,
            "score": similarity_score
        }
        
        return query, params