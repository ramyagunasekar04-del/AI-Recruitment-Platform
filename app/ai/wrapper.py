import json

from google import genai

from app.core.config import settings


class LLMWrapper:

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        self.model = settings.GEMINI_MODEL

    # ========================================================
    # GENERATE TEXT
    # ========================================================

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.2,
    ) -> str:

        response = (
            self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": temperature,
                },
            )
        )

        return response.text

    # ========================================================
    # GENERATE STRUCTURED OUTPUT
    # ========================================================

    def generate_structured(
        self,
        prompt: str,
        response_schema=None,
        temperature: float = 0.1,
    ):

        last_error = None

        for attempt in range(2):

            try:

                response = (
                    self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config={
                            "temperature": temperature,
                            "response_mime_type":
                                "application/json",
                        },
                    )
                )

                data = json.loads(
                    response.text
                )

                if response_schema:
                    return response_schema.model_validate(
                        data
                    )

                return data

            except Exception as exc:

                last_error = exc

                if attempt == 0:
                    prompt = f"""
The previous response was invalid.

Return ONLY valid JSON.

Do not add markdown.
Do not add explanations.
Do not add code fences.

Original task:

{prompt}
"""

        raise ValueError(
            f"Structured AI response failed: {last_error}"
        )

    # ========================================================
    # HEALTH CHECK
    # ========================================================

    def health_check(self) -> bool:

        try:

            response = (
                self.client.models.generate_content(
                    model=self.model,
                    contents="Reply with the word OK.",
                )
            )

            return bool(response.text)

        except Exception:
            return False


llm = LLMWrapper()