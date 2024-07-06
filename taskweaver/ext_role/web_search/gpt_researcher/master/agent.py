import asyncio
import time

from gpt_researcher.config import Config
from gpt_researcher.context.compression import ContextCompressor
from gpt_researcher.master.functions import *
from gpt_researcher.memory import Memory
from gpt_researcher.utils.enum import ReportType

"""アップデート案:
・scrape_sites_by_query メソッド
search_results["body"] は ペガサス で取得した マークダウンコンテンツ になっているので、このコンテンツを全て Gemini Flash に入れて、サブクエリに関係のありそうな内容を要約として作成してもらう。なければNoneを返してもらう。
こうすれば、埋め込みモデルを使わずに全部のコンテンツを利用できる。
高精度・低コスト・高コンテキストウィンドウ の Gemini Flash だからできる案。

# Gemini Flash プロンプト
=============================================
### 指示
Contextを踏まえてSub Queryに対しての要約を提示してください。余計なことは言わずに与えられた情報だけを使って要約を提示してください。
また、ContextとSub Queryに関連がなければ None と出力してください。

### Sub Query
{あああ}

### Context
{search_results["body"]}  ←  [メモ]全コンテンツを使用

理解できたら開始してください！
=============================================

search_results["body"] は複数あるはずなので、For文を回して複数の要約を生成して、生成した全ての要約を改行で連結させて1つの文字列(all_content)にする。
scrape_sites_by_query メソッドから返ってきたものが all_content 。
そして、 process_sub_query メソッドの get_similar_content_by_query は使わないようにして、代わりに process_sub_query では all_content を return させる。
"""


class GPTResearcher:
    """
    GPT Researcher
    """

    def __init__(
        self,
        query: str,
        report_type: str = ReportType.ResearchReport.value,
        source_urls=None,
        config_path=None,
        websocket=None,
        agent=None,
        role=None,
        parent_query: str = "",
        subtopics: list = [],
        visited_urls: set = set(),
        verbose: bool = True,
    ):
        """
        Initialize the GPT Researcher class.
        Args:
            query: str,
            report_type: str
            source_urls
            config_path
            websocket
            agent
            role
            parent_query: str
            subtopics: list
            visited_urls: set
        """
        self.query = query
        self.report_type = report_type
        self.agent = agent
        self.role = role
        self.report_prompt = get_prompt_by_report_type(self.report_type)  # this validates the report type
        self.websocket = websocket
        self.cfg = Config(config_path)  # config_path は None でも問題ない。config ディレクトリに config.json があれば上書きされる。
        self.retriever = get_retriever(self.cfg.retriever)   # tavily
        self.context = []
        self.source_urls = source_urls
        self.memory = Memory(self.cfg.embedding_provider)
        self.visited_urls = visited_urls
        self.verbose = verbose

        # Only relevant for DETAILED REPORTS
        # --------------------------------------

        # Stores the main query of the detailed report
        self.parent_query = parent_query

        # Stores all the user provided subtopics
        self.subtopics = subtopics

    async def conduct_research(self):
        """
        Runs the GPT Researcher to conduct research
        """
        if self.verbose:
            await stream_output("logs", f"🔎 Starting the research task for '{self.query}'...", self.websocket)

        # Generate Agent
        if not (self.agent and self.role):
            print("デバッグ choose_agent 前")
            self.agent, self.role = await choose_agent(self.query, self.cfg, self.parent_query)
            print("デバッグ self.agent", self.agent)
            print("デバッグ self.role", self.role)

        if self.verbose:
            print("デバッグ stream_output 前")
            # この関数の目的は、出力をWebSocketを通じてストリームすることです。また、条件に応じてログに出力することもできます。
            # websocket オブジェクトの send_json メソッドを使用して、type と output を含むJSONデータを非同期で送信します。WebSocket通信が完了するまで待機します。
            await stream_output("logs", self.agent, self.websocket)
            print("デバッグ stream_output done!")    # ここは確認できた

        # If specified, the researcher will use the given urls as the context for the research.
        if self.source_urls:
            print("デバッグ1 source_urls YES")    # こっちはないっぽい
            self.context = await self.get_context_by_urls(self.source_urls)
            print("デバッグ1 source_urls done!")
        else:
            print("デバッグ2 source_urls NO")    # ここは確認できた
            self.context = await self.get_context_by_search(self.query)
            print("デバッグ2 source_urls done!")    # ここは確認できた

        time.sleep(2)

        return self.context

    async def write_report(self, existing_headers: list = []):
        """
        Writes the report based on research conducted

        Returns:
            str: The report
        """
        if self.verbose:
            await stream_output("logs", f"✍️ Writing summary for research task: {self.query}...", self.websocket)   # ここは確認できた

        if self.report_type == "custom_report":
            self.role = self.cfg.agent_role if self.cfg.agent_role else self.role
            # 最新版のファイルはココらへんに変更が入っている
        elif self.report_type == "subtopic_report":
            report = await generate_report(
                query=self.query,
                context=self.context,
                agent_role_prompt=self.role,
                report_type=self.report_type,
                websocket=self.websocket,
                cfg=self.cfg,
                main_topic=self.parent_query,
                existing_headers=existing_headers
            )
        else:
            report = await generate_report(
                query=self.query,              # ★ 初期計画とサブクエリが一致しなければ、インスタンス変数として self.sub_queries を作成して get_context_by_search メソッドで sub_queries を self.sub_queries に変更し self.query の代わりに self.sub_queries を渡せば良い。self.sub_queries の中にオリジナルクエリも入っているから。 → 多分、なるべく元のクエリに沿ったレポートを作成したい、サブクエリの影響力を下げたいという意図で、ここはオリジナルクエリしか渡していない気がする。一旦、このままで。
                context=self.context,          # これはリスト
                agent_role_prompt=self.role,
                report_type=self.report_type,
                websocket=self.websocket,
                cfg=self.cfg
            )

        return report

    async def get_context_by_urls(self, urls):
        """
            Scrapes and compresses the context from the given urls
        """
        new_search_urls = await self.get_new_urls(urls)
        if self.verbose:
            await stream_output("logs",
                            f"🧠 I will conduct my research based on the following urls: {new_search_urls}...",
                            self.websocket)
        scraped_sites = scrape_urls(new_search_urls, self.cfg)
        return await self.get_similar_content_by_query(self.query, scraped_sites)

    async def get_context_by_search(self, query):
        """
           Generates the context for the research task by searching the query and scraping the results
        Returns:
            context: List of context
        """
        context = []
        print("デバッグ get_context_by_search関数 前1")
        # Generate Sub-Queries including original query
        sub_queries = await get_sub_queries(query, self.role, self.cfg, self.parent_query, self.report_type)
        print("デバッグ get_context_by_search関数 後1")

        print("デバッグ get_context_by_search関数 前2")
        # If this is not part of a sub researcher, add original query to research for better results
        if self.report_type != "subtopic_report":
            sub_queries.append(query)

        if self.verbose:
            await stream_output("logs",
                                f"🧠 I will conduct my research based on the following queries: {sub_queries}...",
                                self.websocket)
        print("デバッグ get_context_by_search関数 後2")

        print("デバッグ get_context_by_search関数 前3")
        # Using asyncio.gather to process the sub_queries asynchronously
        # context(list) とは TAVILY.search(sub_query) を使って URL を取得 → BeautifulSoup を使ってクリーンな文字列(Webページの生テキスト)を取得し、そこからサブクエリに関係のありそうなコンテンツを抜き出したもの
        context = await asyncio.gather(*[self.process_sub_query(sub_query) for sub_query in sub_queries])
        print("デバッグ get_context_by_search関数 後3")
        return context

    async def process_sub_query(self, sub_query: str):
        """Takes in a sub query and scrapes urls based on it and gathers context.

        Args:
            sub_query (str): The sub-query generated from the original query

        Returns:
            str: The context gathered from search
        """
        print("デバッグ process_sub_query関数 前1")
        if self.verbose:
            await stream_output("logs", f"\n🔎 Running research for '{sub_query}'...", self.websocket)
        print("デバッグ process_sub_query関数 後1")

        print("デバッグ process_sub_query関数 前2")
        scraped_sites = await self.scrape_sites_by_query(sub_query)   # scraped_sites は コンテンツ(辞書)のリスト。[content1, content2, content3 …]
        content = await self.get_similar_content_by_query(sub_query, scraped_sites)
        print("デバッグ process_sub_query関数 後2")

        if content and self.verbose:
            await stream_output("logs", f"📃 {content}", self.websocket)
        elif self.verbose:
            await stream_output("logs", f"🤷 No content found for '{sub_query}'...", self.websocket)
        return content

    async def get_new_urls(self, url_set_input):
        """ Gets the new urls from the given url set.
        Args: url_set_input (set[str]): The url set to get the new urls from
        Returns: list[str]: The new urls from the given url set
        """

        new_urls = []
        for url in url_set_input:
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                new_urls.append(url)
                if self.verbose:
                    await stream_output("logs", f"✅ Added source url to research: {url}\n", self.websocket)

        return new_urls

    async def scrape_sites_by_query(self, sub_query):
        """
        Runs a sub-query
        Args:
            sub_query:

        Returns:
            scraped_content_results:
                辞書のリスト。[{"url": link1, "raw_content": content1}, {"url": link2, "raw_content": content2}, {"url": link3, "raw_content": content3}, …]
                raw_content は url から BeautifulSoup で取得したクリーンな文字列(サマリーではなくWebページの生テキスト。これはマークダウン化していない。)。
                → JavaScriptのような動的なコンテンツは BeautifulSoup じゃ取得できない気がするので、search_results["body"] の方を使った方が良いかも。
        """
        # Get Urls
        retriever = self.retriever(sub_query)
        # ペガサスで search_results["body"] はマークダウンコンテンツにしたけど、使ってないっぽい。search_results["href"] は コンテンツの URL のリスト
        # search_results["href"] で RAG するために、埋め込みモデルを使って query に関係のありそうなコンテンツを取得している。
        search_results = retriever.search(
            max_results=self.cfg.max_search_results_per_query)
        new_search_urls = await self.get_new_urls([url.get("href") for url in search_results])

        # Scrape Urls
        if self.verbose:
            await stream_output("logs", f"🤔 Researching for relevant information...\n", self.websocket)
        # scraped_content_results は コンテンツ(辞書)のリスト。[content1, content2, content3 …]
        # content1 は {"url": link, "raw_content": content} という辞書で、url は new_search_urls のうちの1番目。content は その url から BeautifulSoup で取得したクリーンな文字列で、サマリーじゃないし、マークダウン化したものでもなく、Webページの生テキスト。
        scraped_content_results = scrape_urls(new_search_urls, self.cfg)
        return scraped_content_results

    async def get_similar_content_by_query(self, query, pages):
        """
        埋め込みモデルを使って query に関係のありそうなコンテンツを取得している。コンテンツ全部を使っている訳では無い
        pages は BeautifulSoup で取得したクリーンな文字列でサマリーじゃないし、マークダウン化したものでもなく、Webページの生テキスト。
        """
        if self.verbose:
            await stream_output("logs", f"📝 Getting relevant content based on query: {query}...", self.websocket)
        # Summarize Raw Data
        context_compressor = ContextCompressor(
            documents=pages, embeddings=self.memory.get_embeddings())   # multilingual-e5-XXX を使っている
        # Run Tasks
        return context_compressor.get_context(query, max_results=8)

    ########################################################################################

    # DETAILED REPORT

    async def write_introduction(self):
        # 本題調査から報告書序文を構成する
        introduction = await get_report_introduction(self.query, self.context, self.role, self.cfg, self.websocket)

        return introduction

    async def get_subtopics(self):
        """
        This async function generates subtopics based on user input and other parameters.

        Returns:
          The `get_subtopics` function is returning the `subtopics` that are generated by the
        `construct_subtopics` function.
        """
        if self.verbose:
            await stream_output("logs", f"🤔 Generating subtopics...", self.websocket)

        subtopics = await construct_subtopics(
            task=self.query,
            data=self.context,
            config=self.cfg,
            # This is a list of user provided subtopics
            subtopics=self.subtopics,
        )

        if self.verbose:
            await stream_output("logs", f"📋Subtopics: {subtopics}", self.websocket)

        return subtopics
