"""Groq LLM adapter with retry, rate-limiting, and strict JSON schema validation."""

import json
import re
import time
from typing import Optional, Dict, Any
from src.config.settings import settings
from src.config.logger import logger
from src.models.extraction import LLMExtractionResult
from src.extraction.prompts.extraction_prompt import (
    SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
)

try:
    from groq import Groq, RateLimitError, APIError, APITimeoutError
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class GroqLLMAdapter:
    """Adapter for Groq LLM API with resilience, exponential backoff, and JSON validation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 25.0,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.max_retries = max_retries
        self.timeout = timeout
        self.client = None

        if GROQ_AVAILABLE and self.api_key:
            self.client = Groq(api_key=self.api_key, timeout=self.timeout)
        else:
            logger.warning(
                "Groq client uninitialized: API key not provided or groq package unavailable."
            )

    def extract(self, raw_record) -> Optional[LLMExtractionResult]:
        """Analyze a raw evidence record and return validated LLMExtractionResult."""
        if not self.client:
            logger.warning(
                f"Groq API key not configured. Skipping extraction for record {raw_record.id}."
            )
            return None

        user_content = EXTRACTION_USER_PROMPT.format(
            source=raw_record.source,
            source_url=raw_record.source_url,
            title=raw_record.title or "[No Title]",
            author=raw_record.author or "[Anonymous]",
            raw_text=raw_record.raw_text,
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )

                raw_content = response.choices[0].message.content
                if not raw_content:
                    raise ValueError("Received empty response from LLM")

                cleaned_json = self._clean_json_response(raw_content)
                parsed_data = json.loads(cleaned_json)
                result = LLMExtractionResult(**parsed_data)
                return result

            except RateLimitError as e:
                sleep_time = 2**attempt * 2.0
                logger.warning(
                    f"Rate limit (429) on attempt {attempt}/{self.max_retries}. Backing off for {sleep_time:.1f}s: {e}"
                )
                time.sleep(sleep_time)

            except (APITimeoutError, TimeoutError) as e:
                sleep_time = 2**attempt * 1.5
                logger.warning(
                    f"Timeout on attempt {attempt}/{self.max_retries}. Retrying in {sleep_time:.1f}s: {e}"
                )
                time.sleep(sleep_time)

            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error on attempt {attempt}/{self.max_retries} for record {raw_record.id}: {e}"
                )
                if attempt == self.max_retries:
                    return None
                time.sleep(1.0)

            except Exception as e:
                logger.error(
                    f"LLM extraction error on attempt {attempt}/{self.max_retries} for record {raw_record.id}: {e}"
                )
                if attempt == self.max_retries:
                    return None
                time.sleep(2**attempt)

        return None

    def _clean_json_response(self, text: str) -> str:
        """Strip markdown fences, leading/trailing whitespace, or artifacts from JSON response."""
        text = text.strip()
        # Remove ```json and ``` if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()
