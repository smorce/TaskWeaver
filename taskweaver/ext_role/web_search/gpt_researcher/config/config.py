# リサーチャー用の config file
# 今はないけど config.json を用意すれば上書きすることもできるし、環境変数から上書きすることもできる。
import json
import os



"""
OpenRouter の Phi-3 free を使うなら、以下で設定値を上書きする

import os
os.environ["LLM_PROVIDER"]    = "openrouter"
os.environ["FAST_LLM_MODEL"]  = "microsoft/phi-3-mini-128k-instruct:free"
os.environ["SMART_LLM_MODEL"] = "microsoft/phi-3-medium-128k-instruct:free"
"""


class Config:
    """Config class for GPT Researcher."""

    def __init__(self, config_file: str = None):
        """Initialize the config class."""
        self.config_file = os.path.expanduser(config_file) if config_file else os.getenv('CONFIG_FILE')
        self.retriever = os.getenv('RETRIEVER', "tavily")
        self.embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'openai')
        self.llm_provider = os.getenv('LLM_PROVIDER', "google")                             # openai から変更
        self.fast_llm_model = os.getenv('FAST_LLM_MODEL', "gemini-1.5-flash-latest")        # gpt-3.5-turbo-16k から変更。LangChain の ChatGoogleGenerativeAI を使っている 
        self.smart_llm_model = os.getenv('SMART_LLM_MODEL', "gemini-1.5-pro-latest")        # gpt-4o から変更。LangChain の ChatGoogleGenerativeAI を使っている
        self.fast_token_limit = int(os.getenv('FAST_TOKEN_LIMIT', 10000))                   # 適当に増やした
        self.smart_token_limit = int(os.getenv('SMART_TOKEN_LIMIT', 20000))                 # 適当に増やした
        self.browse_chunk_max_length = int(os.getenv('BROWSE_CHUNK_MAX_LENGTH', 8192))
        self.summary_token_limit = int(os.getenv('SUMMARY_TOKEN_LIMIT', 3000))              # 適当に増やした
        self.temperature = float(os.getenv('TEMPERATURE', 0.9))                             # 元は 0.55
        self.user_agent = os.getenv('USER_AGENT', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                   "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0")
        self.max_search_results_per_query = int(os.getenv('MAX_SEARCH_RESULTS_PER_QUERY', 5))
        self.memory_backend = os.getenv('MEMORY_BACKEND', "local")
        self.total_words = int(os.getenv('TOTAL_WORDS', 800))
        self.report_format = os.getenv('REPORT_FORMAT', "APA")
        self.max_iterations = int(os.getenv('MAX_ITERATIONS', 3))
        self.agent_role = os.getenv('AGENT_ROLE', None)
        self.scraper = os.getenv("SCRAPER", "bs")
        self.max_subtopics = os.getenv("MAX_SUBTOPICS", 3)

        self.load_config_file()

    def load_config_file(self) -> None:
        """Load the config file."""
        if self.config_file is None:
            return None
        with open(self.config_file, "r") as f:
            config = json.load(f)
        for key, value in config.items():
            setattr(self, key.lower(), value)

