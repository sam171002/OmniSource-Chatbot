import os
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai
load_dotenv()

# Default to 2.5 flash since your API access supports that; can be overridden via env.
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


def _get_client(system_instruction: str = None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")
    genai.configure(api_key=api_key)
    if system_instruction:
        return genai.GenerativeModel(GEMINI_MODEL_NAME, system_instruction=system_instruction)
    return genai.GenerativeModel(GEMINI_MODEL_NAME)


def chat_completion(system_prompt: str, messages: List[dict]) -> str:
    """
    messages: list of {"role": "user"|"assistant", "content": str}
    """
    client = _get_client(system_instruction=system_prompt)
    
    # Convert messages to Gemini format
    # Gemini uses "user" and "model" roles, not "assistant"
    history = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [m["content"]]})
    
    try:
        response = client.generate_content(history)
        if not response.text:
            raise ValueError("Empty response from Gemini API")
        return response.text
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {str(e)}") from e



