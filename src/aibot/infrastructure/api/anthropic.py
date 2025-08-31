import anthropic
from anthropic.types import Message as AnthropicMessage

from src.aibot.model.message import ChatCollection, ChatMessage

from ._base import ParamsBase

client = anthropic.Anthropic()


async def generate_anthropic_response(
    messages: ChatMessage | list[ChatMessage],
    instruction: str,
    params: ParamsBase,
) -> AnthropicMessage:
    """Generate a response using the Anthropic API."""
    msg_list = [messages] if isinstance(messages, ChatMessage) else messages
    convo = ChatCollection(chat_msgs=[*msg_list, ChatMessage(role="assistant")]).render_messages()
    response = client.messages.create(
        model=params.model,
        messages=convo,
        max_tokens=params.max_tokens,
        system=instruction,
        temperature=params.temperature,
        top_p=params.top_p,
    )

    return response  # noqa: RET504
