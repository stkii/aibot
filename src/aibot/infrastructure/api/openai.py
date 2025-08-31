from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.moderation_create_response import ModerationCreateResponse

from src.aibot.model.message import ChatCollection, ChatMessage

from ._base import ParamsBase

_client = OpenAI()


async def generate_openai_response(
    messages: ChatMessage | list[ChatMessage],
    instruction: str,
    params: ParamsBase,
) -> ChatCompletion:
    """Generate a response using theOpenAI API."""
    msg_list = [messages] if isinstance(messages, ChatMessage) else messages
    convo = ChatCollection(chat_msgs=[*msg_list, ChatMessage(role="assistant")]).render_messages()
    full_prompt = [{"role": "developer", "content": instruction}, *convo]
    response = _client.chat.completions.create(
        model=params.model,
        messages=full_prompt,
        max_tokens=params.max_tokens,
        temperature=params.temperature,
        top_p=params.top_p,
    )

    return response  # noqa: RET504


async def get_openai_moderation_result(content: str) -> ModerationCreateResponse:
    """Get detailed moderation results from OpenAI.

    Parameters
    ----------
    content : str
        Content to moderate

    Returns
    -------
    ModerationCreateResponse
        Detailed moderation result including categories and scores

    """
    moderation_response = _client.moderations.create(
        model="omni-moderation-latest",
        input=content,
    )
    return moderation_response  # noqa: RET504
