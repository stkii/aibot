from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse

from src.aibot.model.message import ChatCollection, ChatMessage

from ._base import ParamsBase

client = genai.Client()


async def generate_gemini_response(
    messages: ChatMessage | list[ChatMessage],
    instruction: str,
    params: ParamsBase,
) -> GenerateContentResponse:
    """Generate a response using the Gemini API."""
    msg_list = [messages] if isinstance(messages, ChatMessage) else messages
    convo = ChatCollection(chat_msgs=[*msg_list, ChatMessage(role="assistant")]).render_messages()
    contents = "\n".join([msg["content"] for msg in convo if msg["content"]])
    response = client.models.generate_content(
        model=params.model,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=params.temperature,
            top_p=params.top_p,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
        contents=contents,
    )

    return response  # noqa: RET504
