"""
Shared Runtime Model Adapter for STOPReplay.
Owned by Shaurya (integration) and consumed by Anushree (analysis) and Gary (reporting).

Defaults to Qwen2.5-72B-Instruct via OpenRouter (or DashScope / OpenAI compatible).
Includes:
- generate_completion(): free-form text generation
- generate_structured(): strict JSON schema validation
- runtime metadata generation for Cem's analysis_results.runtime JSONB
- deterministic mock fallback for offline testing without spending API credits
"""

from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Type, Union

DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "qwen/qwen-2.5-72b-instruct"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
SCHEMA_VERSION = "analysis-proposal-v1.1"


class LLMRuntimeError(Exception):
    """Raised when the LLM provider fails, times out, or returns invalid output."""
    def __init__(self, message: str, error_code: str = "PROVIDER_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class ModelAdapter:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        mock_mode: bool = False
    ):
        self.provider = provider or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)
        self.model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
        self.mock_mode = mock_mode or (not self.api_key and not os.getenv("FORCE_REAL_LLM"))
        self._mock_responses: Dict[str, str] = {}

    def get_runtime_metadata(self, temperature: float, top_p: float = 0.9) -> Dict[str, Any]:
        """Returns the exact metadata needed by Cem's analysis_results.runtime column."""
        return {
            "provider": self.provider if not self.mock_mode else "deterministic_mock",
            "model": self.model,
            "schema_version": SCHEMA_VERSION,
            "temperature": temperature,
            "top_p": top_p
        }

    def set_mock_response(self, prompt_keyword: str, response: str) -> None:
        """Register a canned mock response for local integration tests."""
        self._mock_responses[prompt_keyword.lower()] = response

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        stop: Optional[list] = None
    ) -> str:
        """Standard text generation."""
        if self.mock_mode:
            for kw, resp in self._mock_responses.items():
                if kw in prompt.lower() or (system_prompt and kw in system_prompt.lower()):
                    return resp
            return f"[Mock Qwen response for prompt: {prompt[:40]}...]"

        if not self.api_key:
            raise LLMRuntimeError("No API key configured for LLM provider.", "MISSING_API_KEY")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
        if stop:
            payload["stop"] = stop

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        if "openrouter" in self.base_url:
            headers["HTTP-Referer"] = "https://github.com/shaur/STOPReplay"
            headers["X-Title"] = "STOPReplay Hackathon Agent"

        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            raise LLMRuntimeError(f"HTTP Error {e.code} from LLM provider: {err_body}", "HTTP_ERROR")
        except urllib.error.URLError as e:
            raise LLMRuntimeError(f"Network timeout / unreachable provider: {e.reason}", "NETWORK_ERROR")
        except Exception as e:
            raise LLMRuntimeError(f"Unexpected error in LLM generation: {str(e)}", "UNKNOWN_ERROR")

    def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        top_p: float = 0.9,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Generates strict JSON dictionary matching requested schema.
        Ideal for Anushree's findings and Shaurya's action planner.
        """
        sys_instructions = (system_prompt or "") + "\n\nCRITICAL: Respond ONLY with valid, raw JSON. Do not include markdown codeblocks or commentary."
        if schema:
            sys_instructions += f"\nRequired JSON Schema:\n{json.dumps(schema, indent=2)}"

        raw = self.generate_completion(
            prompt=prompt,
            system_prompt=sys_instructions,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )

        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            raise LLMRuntimeError(f"Failed to parse LLM structured output as JSON: {raw[:150]}... Error: {e}", "JSON_PARSE_ERROR")


# Module-level singleton instance for convenience
default_adapter = ModelAdapter()

def generate_completion(prompt: str, **kwargs) -> str:
    return default_adapter.generate_completion(prompt, **kwargs)

def generate_structured(prompt: str, **kwargs) -> Dict[str, Any]:
    return default_adapter.generate_structured(prompt, **kwargs)

def get_runtime_metadata(temperature: float = 0.1) -> Dict[str, Any]:
    return default_adapter.get_runtime_metadata(temperature=temperature)
