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

    def generate_text(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self.is_available:
            return None
        
        full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\nAssistant:"
        
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
            return data.get("response", "").strip()
        except Exception as e:
            print(f"[LLM ERROR] Generation failed: {e}")
            return None

    def generate_json(self, system_prompt: str, user_prompt: str, schema: Dict = None) -> Optional[Dict]:
        """
        Attempts to force JSON output. 
        For MVP, we just prompt for JSON and try to parse it. 
        Ollama also has 'format': 'json' in newer versions.
        """
        if not self.is_available:
            return None

        full_prompt = f"{system_prompt}\n\nIMPORTANT: Output strictly valid JSON. No markdown. No pre-amble.\n\nUser: {user_prompt}\nAssistant:"
        
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
            return json.loads(text)
        except Exception as e:
            print(f"[LLM ERROR] JSON Generation failed: {e}")
            return None

# Singleton
llm_client = LLMClient()
