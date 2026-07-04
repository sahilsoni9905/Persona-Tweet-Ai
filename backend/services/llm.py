import json
import os
import random
from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def generate_tweet(
        self, style_examples: list[str], n: int = 3, feedback: str | None = None
    ) -> list[dict]: ...

    @abstractmethod
    def generate_reply(self, mention_text: str, style_examples: list[str]) -> dict: ...


class MockLLMClient(LLMClient):
    def generate_tweet(
        self, style_examples: list[str], n: int = 3, feedback: str | None = None
    ) -> list[dict]:
        templates = [
            {"text": "some days you ship, some days you fix what you shipped yesterday 🚀", "hashtags": ["#Dev", "#BuildInPublic"]},
            {"text": "the best code is the code you don't have to write", "hashtags": ["#Engineering"]},
            {"text": "freelance life: 90% waiting for feedback, 10% shipping in a panic", "hashtags": ["#Freelance"]},
            {"text": "stopped chasing job titles. started chasing interesting problems 💪", "hashtags": ["#Career"]},
            {"text": "your commit history is the most honest version of you", "hashtags": ["#Dev", "#Reality"]},
        ]
        if feedback:
            templates = [
                {"text": "ok that last one was too corporate. here's the real me: i just ship and figure it out 🚀", "hashtags": ["#BuildInPublic"]},
                {"text": "nobody talks about the 3am debugging sessions that made you who you are", "hashtags": ["#Dev"]},
                {"text": "growth is just solving problems you couldn't solve last year", "hashtags": ["#Life"]},
            ]
        random.shuffle(templates)
        return templates[:n]

    def generate_reply(self, mention_text: str, style_examples: list[str]) -> dict:
        return {"text": "appreciate this! honestly same energy 💯", "hashtags": []}


class RealLLMClient(LLMClient):
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def generate_tweet(
        self, style_examples: list[str], n: int = 3, feedback: str | None = None
    ) -> list[dict]:
        prompt = (
            "You are a social media ghostwriter. Study this person's exact writing voice:\n"
            + "\n".join(f"- {t}" for t in style_examples)
            + f"\n\nWrite {n} original tweets they could post today. Match their tone, vocabulary, "
            + "humour, and typical topics exactly. Each must feel authentically theirs — not generic.\n"
            + "Respond with ONLY a JSON array of objects with keys: text, hashtags."
        )
        if feedback:
            prompt += f"\n\nPrevious attempt feedback: {feedback}"
        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text)

    def generate_reply(self, mention_text: str, style_examples: list[str]) -> dict:
        prompt = (
            "You are replying on behalf of a tech person on Twitter. This is their writing voice:\n"
            + "\n".join(f"- {t}" for t in style_examples)
            + f"\n\nTweet to reply to: \"{mention_text}\"\n\n"
            + "Write a short reply that is:\n"
            + "- Humble and genuine (not trying to show off)\n"
            + "- Lightly funny or witty — dry humour, not cringe\n"
            + "- Anchored in tech/dev/startup world even if the tweet isn't directly about tech\n"
            + "- Conversational, like a real person not a brand\n"
            + "- Under 200 characters\n"
            + "Respond with ONLY a JSON object with keys: text, hashtags."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text)


class GroqLLMClient(LLMClient):
    def __init__(self):
        from groq import Groq
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    def generate_tweet(
        self, style_examples: list[str], n: int = 3, feedback: str | None = None
    ) -> list[dict]:
        prompt = (
            "You are a social media ghostwriter. Study this person's exact writing voice:\n"
            + "\n".join(f"- {t}" for t in style_examples)
            + f"\n\nWrite {n} original tweets they could post today. Match their tone, vocabulary, "
            + "humour, and typical topics exactly. Each must feel authentically theirs — not generic.\n"
            + "Respond with ONLY a JSON array of objects with keys: text, hashtags. No other text."
        )
        if feedback:
            prompt += f"\n\nPrevious attempt feedback: {feedback}"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.content)

    def generate_reply(self, mention_text: str, style_examples: list[str]) -> dict:
        prompt = (
            "You are replying on behalf of a tech person on Twitter. This is their writing voice:\n"
            + "\n".join(f"- {t}" for t in style_examples)
            + f"\n\nTweet to reply to: \"{mention_text}\"\n\n"
            + "Write a short reply that is:\n"
            + "- Humble and genuine (not trying to show off)\n"
            + "- Lightly funny or witty — dry humour, not cringe\n"
            + "- Anchored in tech/dev/startup world even if the tweet isn't directly about tech\n"
            + "- Conversational, like a real person not a brand\n"
            + "- Under 200 characters\n"
            + "Respond with ONLY a JSON object with keys: text, hashtags. No other text."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.content)


def get_llm_client() -> LLMClient:
    use_mock = os.environ.get("USE_MOCK_LLM", "true").lower() == "true"
    if use_mock:
        return MockLLMClient()
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    if provider == "groq":
        return GroqLLMClient()
    return RealLLMClient()
