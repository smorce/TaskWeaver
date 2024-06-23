# ========================================================
# メモ
# ========================================================
# 定型のタスクを実行するWebリサーチャーロールを作成中
# 定型のタスク = マスターエージェントのランググラフ
# つまり、Webリサーチャーロール = マスターエージェント


# とりあえず完成したので、あとは Tavily のAPIキーを用意して TaskWeaver を GitHub にあげて、ローカルで動かしてみる
# → Tavily のAPIキー は用意したので、GitHub にアップする
# クイックスタート：https://github.com/microsoft/TaskWeaver
# Web UI 起動方法
# pip install -U chainlit
# cd playground/UI/
# chainlit run app.py



# API キーの入力はmainで実行するときに以下のように入力すればOK
# import os
# os.environ["OPENAI_API_KEY"] = "～～～"
# os.environ["GEMINI_API_KEY"] = "～～～"    # GEMINI_API_KEY でOK
# os.environ["TAVILY_API_KEY"] = "～～～"    # Free のキーを入手した
# os.environ["LANGCHAIN_API_KEY"] = "～～～"



import asyncio
from dotenv import load_dotenv
import asyncio
import json
import os
from uuid import uuid4
import time

# Run with LangSmith if API key is set
is_LangSmith = True
if is_LangSmith:
    unique_id = uuid4().hex[0:8]
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = f"Tracing Walkthrough - {unique_id}"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = ""   # ★APIキーを入れる
load_dotenv()

from injector import inject

from taskweaver.logging import TelemetryLogger
from taskweaver.memory import Memory, Post
from taskweaver.module.event_emitter import SessionEventEmitter
from taskweaver.module.tracing import Tracing
from taskweaver.role import Role
from taskweaver.role.role import RoleConfig, RoleEntry
from taskweaver.utils import read_yaml


# 元のコード。一旦消してみる。
# suppress asyncio runtime warning
# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# # suppress tqdm message
# os.environ["TQDM_DISABLE"] = "True"


# GPT-researcher に変えたので使っていないが、残しておく
class WebSearchConfig(RoleConfig):
    def _configure(self):
        self.api_provider = self._get_str("api_provider", "duckduckgo")
        self.result_count = self._get_int("result_count", 3)
        self.google_api_key = self._get_str("google_api_key", "")
        self.google_search_engine_id = self._get_str("google_search_engine_id", "")
        self.bing_api_key = self._get_str("bing_api_key", "")


# 使用例
# WebSearchConfig = WebSearchConfig('web_search_config.yaml')
# aaa = WebSearch(WebSearchConfig, logger, tracing, event_emitter, role_entry)


class WebSearch(Role):
    @inject
    def __init__(
        self,
        config: WebSearchConfig,
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,
        role_entry: RoleEntry,
    ):
        super().__init__(config, logger, tracing, event_emitter, role_entry)

        # --------------------------------------------------------
        # GPT-researcher に変えたので使っていないが、残しておく
        self.api_provider = config.api_provider
        self.result_count = config.result_count
        self.google_api_key = config.google_api_key
        self.google_search_engine_id = config.google_search_engine_id
        self.bing_api_key = config.bing_api_key
        # --------------------------------------------------------


        self.logger = logger  # https://microsoft.github.io/TaskWeaver/docs/advanced/telemetry。デフォルトはFalse
        self.writer = None
        self.editor = None
        self.researcher = None    # GPT-researcher を使っている。元々あった Agent がこれで、そこにその他のマルチエージェントが足された。マルチエージェントで使うモデルは task.json に書かれ、self.researcher の設定は config に書かれている
        self.publisher = None
        self.powerpointdesigner = None
        self.output_dir = None
        self.task = None



    def init_research_team(self):
        try:
            from taskweaver.ext_role.web_search.writer import WriterAgent
            from taskweaver.ext_role.web_search.editor import EditorAgent
            from taskweaver.ext_role.web_search.researcher import ResearchAgent
            from taskweaver.ext_role.web_search.publisher import PublisherAgent

            from langgraph.graph import StateGraph, END
            from .utils.views import print_agent_output
            from memory.research import ResearchState


            with open('task.json', 'r') as f:
                task = json.load(f)

            self.task_id = int(time.time()) # Currently time based, but can be any unique identifier
            self.output_dir = f"./outputs/run_{self.task_id}_{task.get('query')[0:40]}"
            self.task = task
            os.makedirs(self.output_dir, exist_ok=True)

            # エージェントの初期化
            self.writer = WriterAgent()
            self.editor = EditorAgent(self.task)
            self.researcher = ResearchAgent()
            self.publisher = PublisherAgent(self.output_dir)


            # ResearchState を持つ Langchain StateGraph を定義
            workflow = StateGraph(ResearchState)

            # Add nodes for each agent
            workflow.add_node("browser",    self.researcher.run_initial_research)
            workflow.add_node("planner",    self.editor.plan_research)
            workflow.add_node("researcher", self.editor.run_parallel_research)
            workflow.add_node("writer",     self.writer.run)
            workflow.add_node("publisher",  self.publisher.run)

            workflow.add_edge('browser',    'planner')
            workflow.add_edge('planner',    'researcher')
            workflow.add_edge('researcher', 'writer')
            workflow.add_edge('writer',     'publisher')

            # set up start and end nodes
            workflow.set_entry_point("browser")
            workflow.add_edge('publisher', END)

            return workflow

        except Exception as e:
            raise Exception(f"Failed to initialize the plugin due to: {e}")

    def reply(self, memory: Memory, **kwargs) -> Post:           # [2024/06/23] マルチエージェントは順番に実行して結果を繋げていく設計なので、 reply メソッドは同期関数でないといけない
        if self.writer is None:
            research_team = self.init_research_team()

        rounds = memory.get_role_rounds(
            role=self.alias,
            include_failure_rounds=False,
        )
        last_post = rounds[-1].post_list[-1]
        post_proxy = self.event_emitter.create_post_proxy(self.alias)
        post_proxy.update_send_to(last_post.send_from)

        async def async_research(chain, task, post_proxy):
            """
            非同期でリサーチグラフを実行する関数。

            Args:
                chain: GPTリサーチャーの LangGraph オブジェクト。
                task: タスク情報を含む辞書。
                post_proxy: PostProxyオブジェクト。

            Returns:
                リサーチグラフを実行した結果
            """
            # リサーチグラフの実行
            # Publisher の generate_layout で作成した layout が result["report"] に格納されている
            result = await chain.ainvoke({"task": task, "post_proxy": post_proxy})          # ★ research_agent.run_initial_research に {"task": self.task} という辞書を渡している。ココで初期計画が立案される。
                                                                                            # ★ post_proxy も渡せるように改造する。
            return result


        def run_async_in_loop(coro):
            """
            既存のイベントループ内で非同期コルーチンを実行する関数。
                1. asyncio.get_event_loop を使って現在のイベントループを取得します。
                2. イベントループが既に走っているかどうかを確認します (loop.is_running()).
                3. 走っている場合、asyncio.ensure_future を使って非同期コルーチンをタスクとしてスケジュールし、その結果を loop.run_until_complete を使って待機します。
                4. 走っていない場合、そのまま loop.run_until_complete を使って非同期コルーチンを実行します。

            Args:
                coro: 実行する非同期コルーチン。

            Returns:
                任意: コルーチンの実行結果。
            """
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 既存のイベントループが実行中の場合、コルーチンをタスクとしてスケジュールし、完了を待機
                future = asyncio.ensure_future(coro)
                loop.run_until_complete(future)
                return future.result()
            else:
                # 既存のイベントループが実行中でない場合、そのままコルーチンを実行
                return loop.run_until_complete(coro)


        try:
            # グラフをコンパイルする
            chain = research_team.compile()

            print_agent_output(f"Starting the research process for query '{self.task.get('query')}'...", "MASTER")

            # 非同期処理を実行
            result = run_async_in_loop(async_research(chain, self.task, post_proxy))

            # post_proxy のアップデート
            post_proxy = result.get("post_proxy")

            # 調査が完了した後にパワーポイントデザイナーを呼び出す
            from taskweaver.ext_role.web_search.powerpointdesigner import PowerPointDesignerAgent
            powerpointdesigner = PowerPointDesignerAgent(self.output_dir)
            post_proxy = powerpointdesigner.run(post_proxy)                                  # output_dir からマークダウンファイルを読み込む。

        except Exception as e:
            self.logger.error(f"Failed to reply due to: {e}")


        return post_proxy.end()



    # def close(self) -> None:
    #     if self.driver is not None:
    #         self.driver.quit()
    #     super().close()