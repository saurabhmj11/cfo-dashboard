import requests
import json
from typing import Optional, Dict, Any

class LLMClient:
    """
    Client for interacting with local LLM (Ollama).
    Falls back to deterministic logic if LLM is unavailable.
    """
    def __init__(self, model: str = "mistral"):
        self.base_url = "http://localhost:11434/api/generate"
        self.model = model
        self._is_available = None # Lazy load state
        self._cache = {} # Simple in-memory cache
        self._cache_hits = 0

    @property
    def is_available(self) -> bool:
        if self._is_available is None:
            self._is_available = self._check_availability()
        return self._is_available

    def _check_availability(self) -> bool:
        try:
            # We assume it's running on default port 11434
            requests.get("http://localhost:11434", timeout=1)
            return True
        except:
            print("[LLM WARNING] Ollama is offline. Agents will degrade to rule-based fallback.")
            return False

    def generate_text(self, system_prompt: str, user_prompt: str, use_cache: bool = True) -> Optional[str]:
        if not self.is_available:
            return None
        
        full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\nAssistant:"
        
        # Cache check
        if use_cache and full_prompt in self._cache:
            self._cache_hits += 1
            print(f"[LLM CACHE HIT] Returning cached response. Total hits: {self._cache_hits}")
            return self._cache[full_prompt]
            
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2, # Low temp for factual analysis
                "num_ctx": 4096
            }
        }
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            result = data.get("response", "").strip()
            
            # Store in cache
            if use_cache:
                self._cache[full_prompt] = result
                # Simple cache eviction to prevent memory explosion
                if len(self._cache) > 1000:
                    self._cache.pop(next(iter(self._cache)))
                    
            return result
        except Exception as e:
            print(f"[LLM ERROR] Generation failed: {e}")
            return None

    def generate_json(self, system_prompt: str, user_prompt: str, schema: Dict = None, use_cache: bool = True) -> Optional[Dict]:
        """
        Attempts to force JSON output. 
        For MVP, we just prompt for JSON and try to parse it. 
        Ollama also has 'format': 'json' in newer versions.
        """
        if not self.is_available:
            return None

        full_prompt = f"{system_prompt}\n\nIMPORTANT: Output strictly valid JSON. No markdown. No pre-amble.\n\nUser: {user_prompt}\nAssistant:"
        
        # Cache check
        if use_cache and full_prompt in self._cache:
            self._cache_hits += 1
            print(f"[LLM CACHE HIT] Returning cached JSON response. Total hits: {self._cache_hits}")
            return json.loads(self._cache[full_prompt])

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "format": "json", # Try native JSON mode if valid model
            "options": {"temperature": 0.1}
        }
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "").strip()
            
            # Store raw string in cache
            if use_cache:
                self._cache[full_prompt] = text
                if len(self._cache) > 1000:
                    self._cache.pop(next(iter(self._cache)))
                    
            return json.loads(text)
        except Exception as e:
            print(f"[LLM ERROR] JSON Generation failed: {e}")
            return None

# Singleton
llm_client = LLMClient()
