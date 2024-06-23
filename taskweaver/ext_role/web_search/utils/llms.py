from langchain.adapters.openai import convert_openai_messages
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser


# pip install pyyaml
import yaml
with open("../web_search_config.yaml", 'r') as file:
    config = yaml.safe_load(file)


# OpenRouter にする
class ChatOpenRouter(ChatOpenAI):
    openai_api_base: str
    openai_api_key: str
    model_name: str

    def __init__(self,
                model_name: str,
                openai_api_key: Optional[str] = None,
                openai_api_base: str = "https://openrouter.ai/api/v1",
                **kwargs):
        openai_api_key = openai_api_key or config.get('openrouter_api_key')
        super().__init__(openai_api_base=openai_api_base,
                        openai_api_key=openai_api_key,
                        model_name=model_name, **kwargs)


def call_model(prompt: list, model: str, max_retries: int = 2, response_format: str = None) -> str:

    optional_params = {}
    if response_format == 'json':
        optional_params = {
            "response_format": {"type": "json_object"}
        }

    lc_messages = convert_openai_messages(prompt)
    # response = ChatOpenAI(model=model, max_retries=max_retries, model_kwargs=optional_params).invoke(lc_messages).content

    # LCEL の書き方にする
    # llm = ChatOpenAI(model=model, max_retries=max_retries, model_kwargs=optional_params)

    # OpenRouter にする。これはリサーチャー以外のマルチエージェントが使うモデル。以下は task.json の値
    # model: "openai/gpt-4o"
    # model: "openai/gpt-3.5-turbo-0125"  # 16k
    # model: "google/gemini-flash-1.5"    # 本家APIじゃないので有料だけど一旦これで。ただし、ChatGoogleGenerativeAI を使えば本家APIを使える。
    # model: "anthropic/claude-3-haiku"
    llm = ChatOpenRouter(model_name=model, max_retries=max_retries, **optional_params)

    # 「StrOutputParser」は、文字列として出力するパーサーです。
    parser = StrOutputParser()

    chain = llm | parser
    response = chain.invoke(lc_messages)

    return response





