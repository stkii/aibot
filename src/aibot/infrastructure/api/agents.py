from agents import Runner

from src.aibot.service.agents import get_all_agents


async def generate_agents_response(user_msg: str) -> str:
    """Generate response using triage agent."""
    triage_agent = get_all_agents()
    result = await Runner.run(triage_agent, input=user_msg)
    return result.final_output
