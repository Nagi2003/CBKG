class LLMPromptGenerator:
    def __init__(self):
        """Initialize the LLM prompt generator"""
        self.max_context_length = 4000  # Maximum tokens for context
    
    def generate_prompt(self, user_query, retrieval_results):
        """Generate a structured prompt for the LLM based on retrieved code elements"""
        # Base system prompt
        system_prompt = """You are a helpful code assistant that answers questions about a codebase.
Answer the user's question based on the code context provided below.
Provide specific examples from the code when relevant.
If the information in the context is insufficient, say so clearly.
"""
        
        # Format the code context
        code_context = self._format_context(retrieval_results)
        
        # Ensure we don't exceed context limits
        code_context = self._truncate_context(code_context)
        
        # Final prompt assembly
        full_prompt = f"{system_prompt}\n\nCODE CONTEXT:\n{code_context}\n\nUSER QUERY: {user_query}\n\nANSWER:"
        
        return full_prompt
    
    def _format_context(self, retrieval_results):
        """Format the retrieved code elements into a structured context"""
        context_sections = []
        
        # First, organize results by their type
        functions = []
        classes = []
        methods = []
        calls = []
        imports = []
        similarities = []
        
        for result in retrieval_results:
            # Determine result type based on keys
            if "function_name" in result and "docstring" in result:
                functions.append(result)
            elif "class_name" in result and "method_name" in result:
                methods.append(result)
            elif "source" in result and "target" in result and "args" in result:
                calls.append(result)
            elif "module" in result and "imports" in result:
                imports.append(result)
            elif "func1" in result and "func2" in result and "similarity" in result:
                similarities.append(result)
        
        # Format Functions
        if functions:
            functions_section = "## Functions\n\n"
            for func in functions:
                functions_section += f"### {func['function_name']}\n"
                if func.get('docstring'):
                    functions_section += f"Docstring: {func['docstring']}\n"
                if func.get('parameters'):
                    param_str = ", ".join(func['parameters'])
                    functions_section += f"Parameters: {param_str}\n"
                functions_section += "\n"
            context_sections.append(functions_section)
        
        # Format Class Methods
        if methods:
            methods_section = "## Class Methods\n\n"
            class_methods = {}
            for method in methods:
                class_name = method['class_name']
                if class_name not in class_methods:
                    class_methods[class_name] = []
                class_methods[class_name].append(method)
            
            for class_name, cls_methods in class_methods.items():
                methods_section += f"### Class: {class_name}\n"
                for method in cls_methods:
                    methods_section += f"Method: {method['method_name']}\n"
                    if method.get('docstring'):
                        methods_section += f"Docstring: {method['docstring']}\n"
                methods_section += "\n"
            context_sections.append(methods_section)
        
        # Format Function Calls
        if calls:
            calls_section = "## Function Calls\n\n"
            for call in calls:
                calls_section += f"{call['source']} calls {call['target']}"
                if call.get('args') or call.get('kwargs'):
                    args_info = f" with {call.get('args', 0)} positional args and {call.get('kwargs', 0)} keyword args"
                    calls_section += args_info
                calls_section += "\n"
            context_sections.append(calls_section)
        
        # Format Imports
        if imports:
            imports_section = "## Module Imports\n\n"
            for imp in imports:
                imports_section += f"{imp['module']} imports {imp['imports']}\n"
            context_sections.append(imports_section)
        
        # Format Similar Functions
        if similarities:
            similarities_section = "## Similar Functions\n\n"
            for sim in similarities:
                similarities_section += f"{sim['func1']} is similar to {sim['func2']} (score: {sim['similarity']:.2f})\n"
            context_sections.append(similarities_section)
        
        # Combine all sections
        return "\n\n".join(context_sections)
    
    def _truncate_context(self, context):
        """Ensure context doesn't exceed token limits"""
        # Simple approximation: 1 token ≈ 4 characters
        approx_tokens = len(context) / 4
        
        if approx_tokens <= self.max_context_length:
            return context
        
        # Truncate to fit within limits
        # This is a simple character-based truncation
        # A more sophisticated approach would preserve complete sections
        truncation_ratio = self.max_context_length / approx_tokens
        truncation_length = int(len(context) * truncation_ratio * 0.95) 
        
        truncated_context = context[:truncation_length]
        truncated_context += "\n\n[Context truncated due to length limitations]"
        
        return truncated_context
    