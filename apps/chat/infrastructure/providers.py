import anthropic
import openai
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langsmith import tracing_context

from apps.chat.application.errors import ChatTimeout, ChatUnavailable
from apps.chat.infrastructure.settings import load_config


class LangChainChat:
    def __init__(self, config):
        self.config = config

    def answer(self, system, messages):
        roles = {"user": HumanMessage, "assistant": AIMessage}
        prompt = [SystemMessage(content=system)]
        prompt.extend(roles[message.role](content=message.content) for message in messages)
        try:
            # Explicit context also disables legacy environment-driven tracing by default.
            with tracing_context(enabled=self.config.tracing):
                response = self.build_model().invoke(prompt)
        except (openai.APITimeoutError, anthropic.APITimeoutError) as exc:
            raise ChatTimeout() from exc
        except (openai.APIError, anthropic.APIError) as exc:
            raise ChatUnavailable() from exc
        return response_text(response.content)

    def build_model(self):
        factories = {"openai": ChatOpenAI, "anthropic": ChatAnthropic}
        try:
            return factories[self.config.provider](
                model=self.config.model,
                api_key=self.config.api_key,
                timeout=self.config.timeout,
                max_tokens=self.config.max_tokens,
                # One attempt keeps timeout and cost predictable; never switch providers.
                max_retries=0,
            )
        except ValueError as exc:
            raise ChatUnavailable() from exc


def response_text(content):
    if isinstance(content, list):
        content = "".join(block_text(block) for block in content)
    if not isinstance(content, str) or not content.strip():
        raise ChatUnavailable()
    return content


def block_text(block):
    if isinstance(block, str):
        return block
    if isinstance(block, dict) and block.get("type") == "text":
        return block.get("text", "")
    return ""


def create_provider():
    return LangChainChat(load_config())
