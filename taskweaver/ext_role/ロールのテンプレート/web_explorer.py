# ----------------------------------------------------------------------
# Twitterから情報収集できそう
# ----------------------------------------------------------------------
# WebExplorerは、Webブラウジング・タスクを実行できます。
# WebExplorerはWebページに移動し、Webページのコンテンツを見ることができます。
# WebExplorerはその視覚能力を使用してWebページを表示し、そこから情報を抽出することができます。
# WebExplorerは、クリック、タイプなど、Webページ上でさまざまなアクションを実行することもできます。
# この役割は、単純なウェブ・ブラウジング・タスクを処理することができます。そのため、タスクが複雑すぎる場合は
# タスクをいくつかの単純なタスクに分解し、WebExplorer
# その後、WebExplorer でステップバイステップでタスクを完了します。

import os

from injector import inject

from taskweaver.logging import TelemetryLogger
from taskweaver.memory import Memory, Post
from taskweaver.module.event_emitter import SessionEventEmitter
from taskweaver.module.tracing import Tracing
from taskweaver.role import Role
from taskweaver.role.role import RoleConfig, RoleEntry
from taskweaver.utils import read_yaml

from taskweaver.llm import LLMApi

class WebExplorerConfig(RoleConfig):
    def _configure(self):
        self.config_file_path = self._get_str(
            "config_file_path",
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "web_explorer_config.yaml",
            ),
        )
        # 追加
        self._set_name("web_search")  # これが config で設定する名前なので、 taskweaver_config には "web_search.llm_alias": "llm_C" と書けばOK

        self.gpt4v_key = self._get_str("gpt4v_key", "")                 # GPT4 V → Haiku で良さそう
        self.gpt4v_endpoint = self._get_str("gpt4v_endpoint", "")
        self.chrome_driver_path = self._get_str("chrome_driver_path", "")
        self.chrome_executable_path = self._get_str("chrome_executable_path", "")


class WebExplorer(Role):
    @inject
    def __init__(
        self,
        config: WebExplorerConfig,
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,   # 多分、event_emitter がイベントをハンドラに送り(イベントの発火)、イベントハンドラーがイベントを検知して、フロントエンドに表示するという流れだと思う
        llm_api: LLMApi,          # 追加
        role_entry: RoleEntry,
    ):
        super().__init__(config, logger, tracing, event_emitter, role_entry)
        # 追加
        self.alias = "WebSearch"    # これは web_search.role.yaml の alias。命名はスネークケースというルールがある。
        self.llm_api = llm_api

        self.logger = logger
        self.config = config
        self.vision_planner = None
        self.driver = None

    def initialize(self):
        try:
            from taskweaver.ext_role.web_explorer.driver import SeleniumDriver　　★ここで同じディレクトリにあるクラスを呼び出す。これがロールの役割になっている
            from taskweaver.ext_role.web_explorer.planner import VisionPlanner　　★ここで同じディレクトリにあるクラスを呼び出す。これがロールの役割になっている

            config = read_yaml(self.config.config_file_path)
            GPT4V_KEY = self.config.gpt4v_key
            GPT4V_ENDPOINT = self.config.gpt4v_endpoint

            ★クラスをインスタンス化
            ★厳密にはタスクウィーバーでいうロールではないので、SeleniumDriverクラス の引数は自由に設計して良い
            self.driver = SeleniumDriver(
                chrome_driver_path=self.config.chrome_driver_path,
                chrome_executable_path=self.config.chrome_executable_path,
                mobile_emulation=False,
                js_script=config["js_script"],
            )

            ★クラスをインスタンス化
            ★厳密にはタスクウィーバーでいうロールではないので、VisionPlannerクラス の引数は自由に設計して良い
            self.vision_planner = VisionPlanner(
                api_key=GPT4V_KEY,
                endpoint=GPT4V_ENDPOINT,
                driver=self.driver,
                prompt=config["prompt"],
            )
        except Exception as e:
            if self.driver is not None:
                self.driver.quit()
            raise Exception(f"Failed to initialize the plugin due to: {e}")

    def reply(self, memory: Memory, **kwargs) -> Post:
        if self.vision_planner is None:　　　★ロールがなければ初期化する
            self.initialize()

        # ===========================================================================
        # 定型文 開始
        # ===========================================================================
        rounds = memory.get_role_rounds(
            role=self.alias,
            include_failure_rounds=False,
        )
        last_post = rounds[-1].post_list[-1]
        post_proxy = self.event_emitter.create_post_proxy(self.alias)
        post_proxy.update_send_to(last_post.send_from)
        # ===========================================================================
        # 定型文 終了
        # ===========================================================================

        try:

            post_proxy.update_send_to(vision_planner alias) みたいなことを書いたら、 web_explorer -> vision_planner に渡ったように見えるかも。
            その代わり、post_proxy.end() をリターンする直前に post_proxy.update_send_to(last_post.send_from) して、宛先をユーザーに戻すのを忘れないように。

            self.vision_planner.get_objective_done(
                objective=last_post.message,
                post_proxy=post_proxy,　　　　　★vision_planner はロールの役割なので post_proxy を渡すことができる。ここでロールを呼び出しているのと同義
            )

        except Exception as e:
            self.logger.error(f"Failed to reply due to: {e}")


        # LLM の使い方
        try:

            # ===========================================================================
            # TaskWeaver/project/taskweaver_config.json で設定した LLM はこうやって使う
            # ===========================================================================
            # ざっくり以下のイメージ。 chat_history とかは taskweaver/planner/planner.py を参考に。
            llm_stream = self.llm_api.chat_completion_stream(
                chat_history,
                use_smoother=True,
                llm_alias=self.config.llm_alias,   # ココで llm_C を設定している。上記の self._set_name で設定した LLM が使われる
            )

        except Exception as e:
            self.logger.error(f"Failed to calling LLM: {e}")





        # ===========================================================================
        # 定型文 開始
        # ===========================================================================
        # vision_planner の方に post_proxy を渡しているので、そっちでメッセージを更新している場合は、ここはコメントアウトしても良い。実際に vision_planner の方でメッセージを更新しているので、ここは本来は不要
        post_proxy.update_message("ここも定型文。～～諸々終了したよ～～")

        return post_proxy.end()
        # ===========================================================================
        # 定型文 終了
        # ===========================================================================





    def close(self) -> None:
        if self.driver is not None:
            self.driver.quit()
        super().close()
