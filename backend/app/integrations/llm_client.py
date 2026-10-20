
import os
import json
import logging

from dotenv import load_dotenv
from google import genai

load_dotenv()
logging.basicConfig(level=logging.INFO)

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL")

if not api_key or not model_name:
    raise ValueError(
        "Gemini API key or model name is missing in .env"
    )

client = genai.Client(api_key=api_key)


async def llmAnalysis(prompt: str) -> dict:
    if not prompt or not prompt.strip():
        return {
            "status": "error",
            "message": "Prompt is empty."
        }

    for attempt in range(3):
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )

            if not response.text:
                raise ValueError("LLM returned an empty response")

            result = json.loads(response.text)

            if not isinstance(result, dict):
                raise ValueError("LLM response must be a JSON object")

            logging.info("LLM response received successfully")

            return {
                "status": "success",
                "data": result
            }

        except Exception as e:
            logging.warning(
                "LLM attempt %s failed: %s",
                attempt + 1,
                e
            )

            if attempt == 2:
                return {
                    "status": "error",
                    "message": "LLM request or response processing failed."
                }

    return {"status": "error", "message": "Unexpected failure"}
