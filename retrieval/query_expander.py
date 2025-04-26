import re
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

class QueryExpander:
    def __init__(self):
        """Initialize the query expander"""
        # Download NLTK resources if they're not already downloaded
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('averaged_perceptron_tagger')
        
        self.lemmatizer = WordNetLemmatizer()
        
        # Common code-related terms and their synonyms
        self.code_synonyms = {
            "function": ["method", "routine", "procedure", "func", "def"],
            "class": ["object", "entity", "struct", "type"],
            "variable": ["var", "field", "attribute", "property", "member"],
            "loop": ["iteration", "cycle", "for", "while", "repeat"],
            "condition": ["if", "switch", "branch", "case", "when"],
            "import": ["require", "include", "load", "dependency"],
            "call": ["invoke", "execute", "run", "trigger"],
            "return": ["output", "result", "response", "yield"],
            "parameter": ["argument", "input", "param", "arg"],
            "initialize": ["init", "setup", "start", "create", "construct"],
            "error": ["exception", "fault", "bug", "issue", "failure"],
            "handle": ["manage", "process", "deal", "treat"],
            "check": ["verify", "validate", "test", "assert"],
            "string": ["text", "str", "char", "character"],
            "number": ["integer", "float", "numeric", "int", "double"],
            "array": ["list", "collection", "sequence", "set"],
            "dictionary": ["map", "hash", "object", "dict"],
            "file": ["document", "resource", "io", "stream"]
        }
    
    def expand(self, query):
        """Expand the user query to improve code retrieval recall"""
        # Tokenize the query
        tokens = word_tokenize(query.lower())
        
        # Part-of-speech tagging
        pos_tags = nltk.pos_tag(tokens)
        
        # Extract important terms (nouns, verbs, adjectives)
        important_terms = []
        for word, tag in pos_tags:
            if tag.startswith('N') or tag.startswith('V') or tag.startswith('J'):
                # Lemmatize the word
                if tag.startswith('N'):
                    lemma = self.lemmatizer.lemmatize(word, wordnet.NOUN)
                elif tag.startswith('V'):
                    lemma = self.lemmatizer.lemmatize(word, wordnet.VERB)
                else:
                    lemma = self.lemmatizer.lemmatize(word)
                
                important_terms.append(lemma)
        
        # Expand with synonyms from WordNet
        expanded_terms = set(important_terms)
        for term in important_terms:
            # Add code-specific synonyms
            if term in self.code_synonyms:
                expanded_terms.update(self.code_synonyms[term])
            
            # Add WordNet synonyms
            synsets = wordnet.synsets(term)
            for synset in synsets[:2]:  # Limit to top 2 synsets to avoid over-expansion
                for lemma in synset.lemmas():
                    synonym = lemma.name().replace('_', ' ')
                    if synonym != term:
                        expanded_terms.add(synonym)
        
        # Build expanded query
        expanded_query = " ".join(expanded_terms)
        
        # Extract code patterns (e.g., function names, method calls)
        code_patterns = self._extract_code_patterns(query)
        if code_patterns:
            expanded_query += " " + " ".join(code_patterns)
        
        return expanded_query
    
    def _extract_code_patterns(self, query):
        """Extract code-like patterns from the query"""
        patterns = []
        
        # Look for function/method calls: name(args)
        func_pattern = r'\b\w+\([^)]*\)'
        functions = re.findall(func_pattern, query)
        patterns.extend(functions)
        
        # Look for method access: object.method
        method_pattern = r'\b\w+\.\w+'
        methods = re.findall(method_pattern, query)
        patterns.extend(methods)
        
        # Look for variable assignments: var = value
        assign_pattern = r'\b\w+\s*='
        assigns = re.findall(assign_pattern, query)
        patterns.extend([a.strip('= ') for a in assigns])
        
        # Look for import statements
        import_pattern = r'(import|from)\s+\w+'
        imports = re.findall(import_pattern, query)
        patterns.extend(imports)
        
        return patterns