import re

class LLMResponseHandler:
    def __init__(self):
        """Initialize the LLM response handler"""
        pass
    
    def format_response(self, raw_response):
        """Format and clean the LLM response"""
        # Remove potential artifacts or junk from the response
        cleaned_response = self._clean_response(raw_response)
        
        # Format code blocks properly
        formatted_response = self._format_code_blocks(cleaned_response)
        
        # Add citation markers for referenced code elements
        response_with_citations = self._add_citations(formatted_response)
        
        # Final polishing
        final_response = self._final_polish(response_with_citations)
        
        return final_response

    def _format_code_blocks(self, response):
        """Ensure code blocks are properly formatted"""
        parts = re.split(r'```(?:\w+)?\n.*?\n```', response, flags=re.DOTALL)
        processed_parts = []
        
        for part in parts:
            # Find code-like patterns that aren't already in code blocks
            code_pattern = r'(?:^|\n)((?:def |class |import |from |if |for |while |with ).*?(?:\n    .*?)+)(?:\n\n|\n$)'
            
            def add_code_formatting(match):
                snippet = match.group(1)
                return f"\n```python\n{snippet}\n```\n"
            
            # Add markdown code formatting where it's missing
            formatted = re.sub(code_pattern, add_code_formatting, part)
            processed_parts.append(formatted)
        
        # Rebuild the response by inserting back the code blocks
        code_blocks = re.findall(r'```(?:\w+)?\n.*?\n```', response, flags=re.DOTALL)
        result = processed_parts[0]
        for i in range(len(code_blocks)):
            if i+1 < len(processed_parts):
                result += code_blocks[i] + processed_parts[i+1]
        
        # Ensure all code blocks have language specified
        result = re.sub(r'```\s*\n', '```python\n', result)
        
        return result
    
    
    def _clean_response(self, response):
        """Clean up potential artifacts in the response"""
        # Remove any system prompts that might have been repeated
        system_pattern = r"You are a helpful code assistant that answers questions.*?ANSWER:"
        cleaned = re.sub(system_pattern, "", response, flags=re.DOTALL)
        
        # Remove any JSON artifacts (sometimes LLMs output JSON)
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                import json
                parsed = json.loads(cleaned)
                if "answer" in parsed:
                    cleaned = parsed["answer"]
                elif "response" in parsed:
                    cleaned = parsed["response"]
                elif "content" in parsed:
                    cleaned = parsed["content"]
            except:
                pass
        
        # Remove any common prefixes LLMs might add
        prefixes = [
            "I'll help you with that.",
            "Here's what I found:",
            "Based on the context provided,"
        ]
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].lstrip()
        
        return cleaned
    
    
    def _add_citations(self, response):
        """Add citation markers for code elements referenced in the response"""
        # Pattern to identify code elements (functions, classes, methods)
        code_elements = [
            r"\b([A-Za-z_][A-Za-z0-9_]*)\([^)]*\)",  # Function calls
            r"\b(class [A-Za-z_][A-Za-z0-9_]*)\b",   # Class definitions
            r"\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)",  # Method references
        ]
        
        processed_response = response
        
        for pattern in code_elements:
            # Find all matches
            matches = re.finditer(pattern, processed_response)
            
            # Skip adding citations inside code blocks
            in_code_block = False
            current_pos = 0
            new_response = ""
            
            for match in matches:
                start, end = match.span()
                
                # Check if we're inside a code block
                code_block_starts = [m.start() for m in re.finditer(r"```", processed_response[current_pos:start])]
                if len(code_block_starts) % 2 == 1:
                    # We're inside a code block, don't add citation
                    continue
                
                # Add citation
                element = match.group(1)
                new_response += processed_response[current_pos:end]
                new_response += f" (from codebase)"
                
                current_pos = end
            
            new_response += processed_response[current_pos:]
            processed_response = new_response
        
        return processed_response
    
    def _final_polish(self, response):
        """Final polishing of the response"""
        # Add a note about code references if they exist
        if "(from codebase)" in response:
            note = "\n\n*Note: Code elements marked with '(from codebase)' are directly referenced from the analyzed code.*"
            response += note
        
        # Remove any duplicate newlines
        response = re.sub(r"\n{3,}", "\n\n", response)
        
        return response