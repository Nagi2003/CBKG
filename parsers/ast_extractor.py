import ast
import os

class ASTExtractor:
    def __init__(self):
        """Initialize the AST extractor"""
        pass
    
    def extract(self, code, file_path):
        """Extract functions, classes, docstrings and call relationships from code"""
        tree = ast.parse(code)
        
        # Extract module-level docstring
        module_docstring = ast.get_docstring(tree) or ""
        
        # Initialize file data
        file_data = {
            'file_path': file_path,
            'module_name': os.path.splitext(os.path.basename(file_path))[0],
            'module_docstring': module_docstring,
            'imports': [],
            'functions': [],
            'classes': [],
            'calls': []
        }
        
        # Extract imports, functions, and classes
        for node in ast.walk(tree):
            # Extract imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports = self._extract_imports(node)
                file_data['imports'].extend(imports)
            
            # Extract functions
            elif isinstance(node, ast.FunctionDef):
                function_data = self._extract_function(node)
                file_data['functions'].append(function_data)
                
                # Extract calls within this function
                calls = self._extract_calls(node)
                for call in calls:
                    call['source'] = function_data['name']
                    file_data['calls'].append(call)
            
            # Extract classes
            elif isinstance(node, ast.ClassDef):
                class_data = self._extract_class(node)
                file_data['classes'].append(class_data)
                
                # Extract calls within class methods
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        calls = self._extract_calls(method)
                        for call in calls:
                            call['source'] = f"{class_data['name']}.{method.name}"
                            file_data['calls'].append(call)
        
        return file_data
    
    def _extract_imports(self, node):
        """Extract import statements"""
        imports = []
        
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.append({
                    'module': name.name,
                    'alias': name.asname
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for name in node.names:
                imports.append({
                    'module': f"{module}.{name.name}" if module else name.name,
                    'alias': name.asname
                })
        
        return imports
    
    def _extract_function(self, node):
        """Extract function details"""
        # Get function docstring
        docstring = ast.get_docstring(node) or ""
        
        # Extract parameters
        params = []
        arguments = node.args
        
        # Process positional parameters
        for arg in arguments.args:
            params.append({
                'name': arg.arg,
                'type': self._get_annotation(arg.annotation),
                'default': None
            })
        
        # Process keyword parameters with defaults
        defaults = arguments.defaults
        if defaults:
            default_offset = len(arguments.args) - len(defaults)
            for i, default in enumerate(defaults):
                params[default_offset + i]['default'] = self._get_value_from_ast(default)
        
        # Process *args parameter
        if arguments.vararg:
            params.append({
                'name': f"*{arguments.vararg.arg}",
                'type': self._get_annotation(arguments.vararg.annotation),
                'default': None
            })
            
        # Process **kwargs parameter
        if arguments.kwarg:
            params.append({
                'name': f"**{arguments.kwarg.arg}",
                'type': self._get_annotation(arguments.kwarg.annotation),
                'default': None
            })
        
        # Extract return annotation
        return_annotation = self._get_annotation(node.returns)
        
        # Extract function body as text
        function_body = ""
        for line in node.body:
            if not isinstance(line, ast.Expr) or not isinstance(line.value, ast.Constant):
                function_body += ast.unparse(line) + "\n"
        
        function_data = {
            'name': node.name,
            'docstring': docstring,
            'parameters': params,
            'return_annotation': return_annotation,
            'body': function_body,
            'line_number': node.lineno
        }
        
        return function_data
    
    def _extract_class(self, node):
        """Extract class details"""
        # Get class docstring
        docstring = ast.get_docstring(node) or ""
        
        # Extract base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))
        
        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_data = self._extract_function(item)
                methods.append(method_data)
        
        class_data = {
            'name': node.name,
            'docstring': docstring,
            'bases': bases,
            'methods': methods,
            'line_number': node.lineno
        }
        
        return class_data
    
    def _extract_calls(self, node):
        """Extract function calls within a code block"""
        calls = []
        
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Call):
                call_data = {
                    'target': self._get_call_target(subnode.func),
                    'args': len(subnode.args),
                    'kwargs': len(subnode.keywords),
                    'line_number': subnode.lineno
                }
                calls.append(call_data)
        
        return calls
    
    def _get_call_target(self, node):
        """Get the name of the called function"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return ast.unparse(node)
        else:
            return ast.unparse(node)
    
    def _get_annotation(self, node):
        """Get type annotation as a string"""
        if node is None:
            return None
        return ast.unparse(node)
    
    def _get_value_from_ast(self, node):
        """Extract a literal value from an AST node"""
        if isinstance(node, ast.Constant):
            return node.value
        else:
            try:
                return ast.literal_eval(node)
            except (ValueError, SyntaxError):
                return ast.unparse(node)