import asyncio
import httpx
from app.config import settings


class LLMClientError(Exception):
    pass


class LLMClient:
    def __init__(self):
        # Default model and endpoint (can be overridden via settings)
        self.model = getattr(settings, "LLM_MODEL", "llama-3.3-70b-versatile")
        self.base_url = getattr(settings, "LLM_BASE_URL", "https://api.groq.com/openai/v1")
        self.api_key = getattr(settings, "LLM_API_KEY", None)

        # If no API key configured, operate in mock mode for local development.
        self.mock = not bool(self.api_key)

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_retries: int = 3,
    ) -> str:
        # If in mock mode, return a deterministic mock JSON helpful for testing the parser.
        if self.mock:
            # Try to detect parse intent and return a simple structured JSON
            text = "\n\n".join([m.get("content", "") for m in messages if m.get("role") == "user"]).lower()
            import json as _json
            if "parse" in text or "document" in text:
                return _json.dumps({
                    "document_type": "Mock Document",
                    "title": "Mock Title",
                    "summary": "This is a mock summary generated because no LLM key is configured.",
                    "elements": [],
                    "relationships": []
                })
            return _json.dumps({"document_type": "mock", "title": None, "summary": "", "elements": [], "relationships": []})
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]

                except httpx.HTTPStatusError as exc:
                    # 429 = rate limit, 502/503/504 = transient
                    if exc.response.status_code in (429, 502, 503, 504):
                        if attempt < max_retries - 1:
                            wait = 2 ** attempt
                            await asyncio.sleep(wait)
                            continue
                    raise LLMClientError(
                        f"LLM HTTP error {exc.response.status_code}: {exc.response.text[:200]}"
                    ) from exc

                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise LLMClientError(f"LLM connection failed after retries: {exc}") from exc

        raise LLMClientError("Failed to get LLM response after all retries")


llm_client = LLMClient()