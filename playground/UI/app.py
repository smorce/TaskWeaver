# ======================================================================

# Custom frontend with Chainlit!
# https://github.com/Chainlit/cookbook/tree/main/custom-frontend

# ======================================================================

import atexit  # プログラム終了時に特定の関数を自動で実行するためのモジュール
import functools  # 高階関数をサポートするためのモジュール
import os  # OSに依存した機能を扱うためのモジュール
import re  # 正規表現をサポートするためのモジュール
import sys  # Pythonのインタプリタや環境に関する情報にアクセスするためのモジュール
from typing import Any, Dict, List, Optional, Tuple, Union  # 型ヒントを提供するためのモジュール

import requests  # HTTPリクエストを送信するためのモジュール

# 現在のディレクトリをこのファイルが存在するディレクトリに変更します
os.chdir(os.path.dirname(__file__))

try:
    import chainlit as cl  # chainlitパッケージをインポート

    print(
        "UIが起動していない場合、`playground/UI`フォルダに移動して`chainlit run app.py`を実行してUIを起動してください。",
    )
except Exception:
    raise Exception(
        "UIを使用するにはchainlitパッケージが必要です。手動で`pip install chainlit`を実行してインストールしてから`chainlit run app.py`を実行してください。",
    )

# リポジトリのパスを設定
repo_path = os.path.join(os.path.dirname(__file__), "../../")
sys.path.append(repo_path)  # モジュール検索パスにリポジトリパスを追加
from taskweaver.app.app import TaskWeaverApp  # TaskWeaverアプリをインポート
from taskweaver.memory.attachment import AttachmentType
from taskweaver.memory.type_vars import RoleName
from taskweaver.module.event_emitter import PostEventType, RoundEventType, SessionEventHandlerBase
from taskweaver.session.session import Session

# プロジェクトのパスを設定
project_path = os.path.join(repo_path, "project")
# TaskWeaverアプリケーションをインスタンス化
app = TaskWeaverApp(app_dir=project_path, use_local_uri=True)
atexit.register(app.stop)  # アプリケーションが終了する時にapp.stopを呼び出すように設定
app_session_dict: Dict[str, Session] = {}  # セッションを格納する辞書


# ==========================================================================================================

# こちらのコードはHTML要素を動的に生成するためのヘルパー関数と、特定のHTMLタグに関するショートカットを定義しています。
def elem(name: str, cls: str = "", attr: Dict[str, str] = {}, **attr_dic: str):
    """
    指定されたHTML要素を生成する関数です。

    Parameters:
        name (str): 生成するHTML要素の名前。
        cls (str): 要素に適用するクラス名。省略可能。
        attr (Dict[str, str]): 属性とその値を持つ辞書。省略可能。
        **attr_dic (str): 任意の数の追加属性をキーワード引数として受け取ります。

    Returns:
        function: 子要素を引数として受け取り、完全なHTML要素を文字列として返す関数。
    """
    # すべての属性を統合
    all_attr = {**attr, **attr_dic}
    # クラス属性が指定されていれば追加
    if cls:
        all_attr.update({"class": cls})

    # 属性を文字列に変換
    attr_str = ""
    if len(all_attr) > 0:
        attr_str += "".join(f' {k}="{v}"' for k, v in all_attr.items())

    def inner(*children: str):
        """
        生成したHTML要素の子要素を設定する内部関数。

        Parameters:
            *children (str): 子要素の内容。

        Returns:
            str: 完全なHTML要素を表す文字列。
        """
        children_str = "".join(children)
        return f"<{name}{attr_str}>{children_str}</{name}>"

    return inner

def txt(content: str, br: bool = True):
    """
    特殊文字をエスケープし、必要に応じて改行をHTMLの<br>または改行コードに変換する関数。

    Parameters:
        content (str): 変換するテキスト。
        br (bool): Trueの場合は改行を<br>に、Falseの場合は改行を改行コードに変換します。

    Returns:
        str: 変換後のテキスト。
    """
    content = content.replace("<", "&lt;").replace(">", "&gt;")
    if br:
        content = content.replace("\n", "<br>")
    else:
        content = content.replace("\n", "&#10;")
    return content

# HTMLのdiv要素を作成するためのショートカット関数
div = functools.partial(elem, "div")
# HTMLのspan要素を作成するためのショートカット関数
span = functools.partial(elem, "span")
# 点滅するカーソルを表すspan要素を生成
blinking_cursor = span("tw-end-cursor")()


# ==========================================================================================================


def file_display(files: List[Tuple[str, str]], session_cwd_path: str):
    """
    指定されたファイルリストを適切な形式で表示する関数です。

    Parameters:
        files (List[Tuple[str, str]]): ファイル名とファイルパスのタプルのリスト。
        session_cwd_path (str): セッションのカレントディレクトリパス。

    Returns:
        List[cl.Element]: 表示用の要素リスト。
    """
    elements: List[cl.Element] = []
    for file_name, file_path in files:
        # 画像ファイルの場合
        if file_path.endswith((".png", ".jpg", ".jpeg", ".gif")):
            image = cl.Image(
                name=file_path,
                display="inline",
                path=file_path if os.path.isabs(file_path) else os.path.join(session_cwd_path, file_path),
                size="large",
            )
            elements.append(image)
        # 音声ファイルの場合
        elif file_path.endswith((".mp3", ".wav", ".flac")):
            audio = cl.Audio(
                name="converted_speech",
                display="inline",
                path=file_path if os.path.isabs(file_path) else os.path.join(session_cwd_path, file_path),
            )
            elements.append(audio)
        # CSVファイルの場合
        elif file_path.endswith(".csv"):
            data = (
                pd.read_csv(file_path)
                if os.path.isabs(file_path)
                else pd.read_csv(os.path.join(session_cwd_path, file_path))
            )
            row_count = len(data)
            table = cl.Text(
                name=file_path,
                content=f"There are {row_count} in the data. The top {min(row_count, 5)} rows are:\n"
                        + data.head(n=5).to_markdown(),
                display="inline",
            )
            elements.append(table)
        else:
            print(f"Unsupported file type: {file_name} for inline display.")
        # ファイルのダウンロードリンクを追加
        file = cl.File(
            name=file_name,
            display="inline",
            path=file_path if os.path.isabs(file_path) else os.path.join(session_cwd_path, file_path),
        )
        elements.append(file)
    return elements

def is_link_clickable(url: str):
    """
    与えられたURLがクリック可能かどうかを確認する関数です。

    Parameters:
        url (str): 検証するURL。

    Returns:
        bool: URLがクリック可能ならTrue、そうでなければFalse。
    """
    if url:
        try:
            response = requests.get(url)
            # ステータスコードが200ならクリック可能
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    else:
        return False


# ==========================================================================================================


class ChainLitMessageUpdater(SessionEventHandlerBase):
    """
    ChainLitアプリケーションでのメッセージ更新を管理するクラスです。
    セッションクラスのイベントハンドラー: https://microsoft.github.io/TaskWeaver/docs/concepts/session

    Attributes:
        root_step (cl.Step): 最初のステップを表すChainLitのStepオブジェクト。
    """

    def __init__(self, root_step: cl.Step):
        """
        初期化メソッドです。

        Parameters:
            root_step (cl.Step): セッションのルートとなるStepオブジェクト。
        """
        self.root_step = root_step
        self.reset_cur_step()

    def reset_cur_step(self):
        """
        現在のステップと関連データをリセットします。
        """
        self.cur_step: Optional[cl.Step] = None
        self.cur_attachment_list: List[Tuple[str, AttachmentType, str, bool]] = []
        self.cur_post_status: str = "Updating"
        self.cur_send_to: RoleName = "Unknown"
        self.cur_message: str = ""
        self.cur_message_is_end: bool = False
        self.cur_message_sent: bool = False

    def handle_round(
        self,
        type: RoundEventType,
        msg: str,
        extra: Any,
        round_id: str,
        **kwargs: Any,
    ):
        """
        ラウンドイベントを処理するメソッドです。

        Parameters:
            type (RoundEventType): ラウンドイベントのタイプ。
            msg (str): メッセージ内容。
            extra (Any): 追加データ。
            round_id (str): ラウンドのID。
            **kwargs (Any): その他の任意のキーワード引数。
        """
        if type == RoundEventType.round_error:
            self.root_step.is_error = True
            self.root_step.output = msg
            cl.run_sync(self.root_step.update())

    def handle_post(
        self,
        type: PostEventType,
        msg: str,
        extra: Any,
        post_id: str,
        round_id: str,
        **kwargs: Any,
    ):
        """
        ポストイベントを処理するためのメソッドです。
        各イベントタイプに応じて異なるアクションを実行します。

        Parameters:
            type: イベントの種類を指定するPostEventTypeです。
            msg: イベントに関連するメッセージや内容。
            extra: イベントに関連する追加データ。
            post_id: ポストの一意識別子。
            round_id: 関連するラウンドのID。
            **kwargs: 追加の任意のキーワード引数。


        メソッドのパラメータ
            type: PostEventType の値で、イベントのタイプ（開始、終了、エラーなど）を示します。
            msg: イベントに関連するメッセージや内容を持つ文字列です。
            extra: イベントに関連する追加データを持ち、辞書形式で提供されます。
            post_id: ポストの一意識別子です。
            round_id: 関連するラウンドのIDです。
            **kwargs: その他の任意のキーワード引数で、特定のシナリオで使用される追加情報を含むことができます。

        イベントタイプに基づく処理
            post_start: ポストの開始イベント。現在のステップをリセットし、新しいcl.Stepを初期化します。このステップは入力表示が可能で、ルートではありません。
            post_end: ポストの終了イベント。現在のステップの情報をストリーミングし、その後ステップを終了します。最後に、現在のステップをリセットします。
            post_error: ポストにおけるエラーイベント。この場合、具体的なエラー処理は実装されていません（passが使われています）。
            post_attachment_update: 添付ファイルの更新イベント。新しい添付情報をリストに追加するか、既存の情報を更新します。
            post_send_to_update: メッセージ送信先の更新イベント。送信先役割を更新します。
            post_message_update: メッセージ内容の更新イベント。メッセージを累積し、メッセージの終了フラグが立っているかどうかをチェックします。
            post_status_update: ポストのステータス更新イベント。ステータスメッセージを更新します。

        最後の更新処理
            ステップが有効であれば（cur_step is not None）、現在のポストの本文をフォーマットしてストリームします。
            メッセージが終了しており、まだ送信されていない場合、メッセージをステップの要素に追加して、ステップを更新します。

        """

        print("デバッグ1")
        try:
            print("cur_step")
            print(self.cur_step)
            print()
        except Exception:
            print("cur_step はなかった")
            print()

        try:
            print("extra")
            print(extra)
            print()
        except Exception:
            print("extra はなかった")
            print()


        if type == PostEventType.post_start:
            # ポスト開始イベントの処理
            self.reset_cur_step()
            # self.cur_step = cl.Step(name=extra["role"], show_input=True, root=False)
            self.cur_step = cl.Step(name=extra["role"], show_input=True)    # [破壊的変更に対応] root が False だったので単純に消した
            cl.run_sync(self.cur_step.__aenter__())
        elif type == PostEventType.post_end:
            # ポスト終了イベントの処理
            assert self.cur_step is not None
            content = self.format_post_body(True)
            # ストリーミング表示？
            cl.run_sync(self.cur_step.stream_token(content, True))
            cl.run_sync(self.cur_step.__aexit__(None, None, None))  # type: ignore
            self.reset_cur_step()
        elif type == PostEventType.post_error:
            # ポストエラーイベントの処理（現在は何も実行しない）
            pass
        elif type == PostEventType.post_attachment_update:
            # 添付ファイル更新イベントの処理
            assert self.cur_step is not None, "cur_step should not be None"
            id: str = extra["id"]
            a_type: AttachmentType = extra["type"]
            is_end: bool = extra["is_end"]
            # a_extra: Any = extra["extra"]
            if len(self.cur_attachment_list) == 0 or id != self.cur_attachment_list[-1][0]:
                self.cur_attachment_list.append((id, a_type, msg, is_end))
            else:
                prev_msg = self.cur_attachment_list[-1][2]
                self.cur_attachment_list[-1] = (id, a_type, prev_msg + msg, is_end)

        elif type == PostEventType.post_send_to_update:
            # 送信先更新イベントの処理
            self.cur_send_to = extra["role"]
        elif type == PostEventType.post_message_update:
            # メッセージ更新イベントの処理
            self.cur_message += msg
            if extra["is_end"]:
                self.cur_message_is_end = True
        elif type == PostEventType.post_status_update:
            # ステータス更新イベントの処理
            self.cur_post_status = msg

        if self.cur_step is not None:
            # ステップが存在する場合、内容を更新
            content = self.format_post_body(False)
            # ストリーミング表示？
            cl.run_sync(self.cur_step.stream_token(content, True))
            if self.cur_message_is_end and not self.cur_message_sent:
                # メッセージが完了し、まだ送信されていない場合、更新を行う
                # 次のStepに進むということかも？
                self.cur_message_sent = True
                self.cur_step.elements = [
                    *(self.cur_step.elements or []),
                    cl.Text(
                        content=self.cur_message,
                        display="inline",
                    ),
                ]
                cl.run_sync(self.cur_step.update())


    def get_message_from_user(self, prompt: str, timeout: int = 120) -> Optional[str]:
        """
        ユーザーにプロンプトを表示し、入力されたメッセージを表示します。

        Parameters:
            prompt (str): ユーザーに表示するプロンプト。
            timeout (int): ユーザーの入力を待つ最大秒数。デフォルトは120秒。

        Returns:
            Optional[str]: ユーザーが入力したメッセージ、またはタイムアウト時にNone。
        """
        ask_user_msg = cl.AskUserMessage(content=prompt, author=" ", timeout=timeout)  # ユーザーに問いかけるメッセージを作成
        res = cl.run_sync(ask_user_msg.send())  # メッセージを同期的に送信し、結果を取得
        cl.run_sync(ask_user_msg.remove())  # メッセージをUIから削除
        if res is not None:
            res_msg = cl.Message.from_dict(res)  # 結果からメッセージオブジェクトを生成
            msg_txt = res_msg.content  # メッセージの内容を取得
            cl.run_sync(res_msg.remove())  # メッセージをUIから削除
            return msg_txt
        return None

    def get_confirm_from_user(
        self,
        prompt: str,
        actions: List[Union[Tuple[str, str], str]],
        timeout: int = 120,
    ) -> Optional[str]:
        """
        ユーザーに確認用のプロンプトと選択肢を表示し、選択されたアクションを取得します。

        Parameters:
            prompt (str): ユーザーに表示する確認用プロンプト。
            actions (List[Union[Tuple[str, str], str]]): ユーザーに提供するアクションのリスト。
            timeout (int): ユーザーの入力を待つ最大秒数。デフォルトは120秒。

        Returns:
            Optional[str]: ユーザーが選択したアクションの値、またはタイムアウト時にNone。
        """
        cl_actions: List[cl.Action] = []  # cl.Actionオブジェクトのリストを初期化
        for arg_action in actions:
            if isinstance(arg_action, str):
                cl_actions.append(cl.Action(name=arg_action, value=arg_action))
            else:
                name, value = arg_action
                cl_actions.append(cl.Action(name=name, value=value))
        ask_user_msg = cl.AskActionMessage(content=prompt, actions=cl_actions, author=" ", timeout=timeout)
        res = cl.run_sync(ask_user_msg.send())  # アクションメッセージを送信し、結果を取得
        cl.run_sync(ask_user_msg.remove())  # メッセージをUIから削除
        if res is not None:
            for action in cl_actions:
                if action.value == res["value"]:
                    return action.value
        return None


    def format_post_body(self, is_end: bool) -> str:
        """
        ポストの本文をフォーマットして返すメソッド。

        Parameters:
            is_end (bool): このポストが最後のものかどうか。

        Returns:
            str: フォーマットされたポストの本文。
        """
        content_chunks: List[str] = []  # 本文を格納するリスト

        # 添付ファイルを処理する
        for attachment in self.cur_attachment_list:
            a_type = attachment[1]  # 添付ファイルのタイプ

            # アーティファクトパスは常にスキップ
            if a_type in [AttachmentType.artifact_paths]:
                continue

            # 最終結果でPythonコードはスキップ
            if is_end and a_type in [AttachmentType.python]:
                continue

            # 添付ファイルをフォーマットしてリストに追加
            content_chunks.append(self.format_attachment(attachment))

        # 現在のメッセージが空でない場合、内容を追加
        if self.cur_message != "":
            if self.cur_send_to == "Unknown":
                content_chunks.append("**Message**:")
            else:
                content_chunks.append(f"**Message To {self.cur_send_to}**:")

            if not self.cur_message_sent:
                content_chunks.append(
                    self.format_message(self.cur_message, self.cur_message_is_end),
                )

        # エンドフラグが立っていない場合、更新中のステータスを表示
        if not is_end:
            content_chunks.append(
                div("tw-status")(
                    span("tw-status-updating")(
                        elem("svg", viewBox="22 22 44 44")(elem("circle")()),
                    ),
                    span("tw-status-msg")(txt(self.cur_post_status + "...")),
                ),
            )

        return "\n\n".join(content_chunks)  # 本文のチャンクを改行で結合して返す


    def format_attachment(
        self,
        attachment: Tuple[str, AttachmentType, str, bool],
    ) -> str:
        """
        アタッチメント情報をフォーマットしてHTML形式の文字列として返します。

        Parameters:
            attachment (Tuple[str, AttachmentType, str, bool]): アタッチメント情報
                - ID
                - アタッチメントのタイプ
                - メッセージ内容
                - 終了フラグ

        Returns:
            str: フォーマットされたHTML文字列
        """
        id, a_type, msg, is_end = attachment
        # ヘッダー部分の作成
        header = div("tw-atta-header")(
            div("tw-atta-key")(
                " ".join([item.capitalize() for item in a_type.value.split("_")]),
            ),
            div("tw-atta-id")(id),
        )
        atta_cnt: List[str] = []

        # アタッチメントのタイプに応じたコンテンツの生成
        if a_type in [AttachmentType.plan, AttachmentType.init_plan]:
            items: List[str] = []
            lines = msg.split("\n")
            for idx, row in enumerate(lines):
                item = row
                if "." in row and row.split(".")[0].isdigit():
                    item = row.split(".", 1)[1].strip()
                items.append(
                    div("tw-plan-item")(
                        div("tw-plan-idx")(str(idx + 1)),
                        div("tw-plan-cnt")(
                            txt(item),
                            blinking_cursor if not is_end and idx == len(lines) - 1 else "",
                        ),
                    ),
                )
            atta_cnt.append(div("tw-plan")(*items))
        elif a_type == AttachmentType.execution_result:
            atta_cnt.append(
                elem("pre", "tw-execution-result")(
                    elem("code")(txt(msg)),
                ),
            )
        elif a_type in [AttachmentType.python, AttachmentType.sample]:
            atta_cnt.append(
                elem("pre", "tw-python", {"data-lang": "python"})(
                    elem("code", "language-python")(txt(msg, br=False)),
                ),
            )
        else:
            atta_cnt.append(txt(msg))
            if not is_end:
                atta_cnt.append(blinking_cursor)

        # 最終的なアタッチメントのHTMLを返す
        return div("tw-atta")(
            header,
            div("tw-atta-cnt")(*atta_cnt),
        )



    def format_message(self, message: str, is_end: bool) -> str:
        """
        与えられたメッセージをHTML形式にフォーマットします。
        メッセージにコードブロックが含まれている場合、それを適切なHTML <pre> と <code> タグで囲み、
        指定された言語に基づいてシンタックスハイライトが適用できるようにするためのものです。
        コードブロックが終了する場所には、適切にタグを閉じ、さらには点滅カーソルを追加するオプションも含まれています。

        Parameters:
            message (str): フォーマットするメッセージ。
            is_end (bool): メッセージが最終メッセージかどうか。

        Returns:
            str: HTML形式に変換されたメッセージ。
        """
        # 特殊文字をエスケープし、改行を含まない形でテキストを準備
        content = txt(message, br=False)
        # プリフォーマットテキストの開始を示す正規表現
        begin_regex = re.compile(r"^```(\w*)$\n", re.MULTILINE)
        # プリフォーマットテキストの終了を示す正規表現
        end_regex = re.compile(r"^```$\n?", re.MULTILINE)

        # メッセージの終端に特定のタグを追加
        if not is_end:
            end_tag = " " + blinking_cursor  # 点滅カーソルを追加
        else:
            end_tag = ""  # 何も追加しない

        # メッセージ内のプリフォーマットセクションをHTMLに変換
        while True:
            start_label = begin_regex.search(content)
            if not start_label:
                break
            start_pos = content.index(start_label[0])
            lang_tag = start_label[1]  # 言語タグを取得
            content = "".join(
                [
                    content[:start_pos],
                    f'<pre data-lang="{lang_tag}"><code class="language-{lang_tag}">',
                    content[start_pos + len(start_label[0]):],
                ],
            )

            end_pos = end_regex.search(content)
            if not end_pos:
                content += end_tag + "</code></pre>"
                end_tag = ""
                break
            end_pos_pos = content.index(end_pos[0])
            content = f"{content[:end_pos_pos]}</code></pre>{content[end_pos_pos + len(end_pos[0]):]}"

        content += end_tag
        return content



@cl.on_chat_start  # チャットセッションが開始するときにこのデコレータ下の関数を実行
async def start():
    """
    チャットセッションが開始された際に呼ばれる関数です。

    この関数では、新しいセッションが開始されたことをログに出力し、
    セッションをアプリケーションのセッション辞書に保存します。
    """
    user_session_id = cl.user_session.get("id")  # ユーザーのセッションIDを取得
    app_session_dict[user_session_id] = app.get_session()  # 新しいアプリケーションセッションを取得して保存
    print("Starting new session")  # ログに新しいセッション開始を出力


@cl.on_chat_end  # チャットセッションが終了するときにこのデコレータ下の関数を実行
async def end():
    """
    チャットセッションが終了された際に呼ばれる関数です。

    この関数では、セッションの終了をログに出力し、セッションを停止して
    アプリケーションのセッション辞書から削除します。
    """
    user_session_id = cl.user_session.get("id")  # ユーザーのセッションIDを取得
    app_session = app_session_dict[user_session_id]  # 対応するアプリケーションセッションを取得
    print(f"Stopping session {app_session.session_id}")  # ログにセッション終了を出力
    app_session.stop()  # セッションを停止
    app_session_dict.pop(user_session_id)  # セッション辞書からセッションIDを削除


# メッセージが来たときに実行される関数を定義
@cl.on_message
async def main(message: cl.Message):
    # ユーザーセッションからIDを取得
    user_session_id = cl.user_session.get("id")  # type: ignore
    # セッションIDに基づいてセッションオブジェクトを取得
    session: Session = app_session_dict[user_session_id]  # type: ignore
    # セッションで使用する作業ディレクトリのパスを取得
    session_cwd_path = session.execution_cwd

    # ローダーを表示しながらメッセージを送信
    # async with cl.Step(name="", show_input=True, root=True) as root_step:
    #     response_round = await cl.make_async(session.send_message)(
    #         message.content,
    #         files=[
    #             {
    #                 "name": element.name if element.name else "file",
    #                 "path": element.path,
    #             }
    #             for element in message.elements
    #             if element.type == "file" or element.type == "image"
    #         ],
    #         event_handler=ChainLitMessageUpdater(root_step),      # これがイベントハンドラー
    #     )

    # メッセージを作成して送信
    # cl.Messageのインスタンスを作成し、cl.Message を使用してルートレベルのメッセージを送信し、cl.Step をネストする必要がある
    root_message = cl.Message(content=message.content)
    await root_message.send()

    # 以下の Step クラスから root が削除される破壊的変更に対応した
    # https://github.com/Chainlit/chainlit/releases/tag/1.1.300rc0
    # ステップを実行
    async with cl.Step(name="", show_input=True) as root_step:
        response_round = await cl.make_async(session.send_message)(
            message.content,
            files=[
                {
                    "name": element.name if element.name else "file",
                    "path": element.path,
                }
                for element in message.elements
                if element.type == "file" or element.type == "image"
            ],
            event_handler=ChainLitMessageUpdater(root_step),      # これがイベントハンドラー
        )

    # 応答からアーティファクトのパスを抽出
    artifact_paths = [
        p
        for p in response_round.post_list
        for a in p.attachment_list
        if a.type == AttachmentType.artifact_paths
        for p in a.content
    ]

    # ユーザーに送信する投稿を処理
    for post in [p for p in response_round.post_list if p.send_to == "User"]:
        files: List[Tuple[str, str]] = []
        # アーティファクトのパスがあれば、それらのファイル名とパスをリストに追加
        if len(artifact_paths) > 0:
            for file_path in artifact_paths:
                file_name = os.path.basename(file_path)
                files.append((file_name, file_path))

        # メッセージ内のファイルパスを抽出して表示
        user_msg_content = post.message
        pattern = r"(!?)\[(.*?)\]\((.*?)\)"
        matches = re.findall(pattern, user_msg_content)
        for match in matches:
            img_prefix, file_name, file_path = match
            if "://" in file_path:
                if not is_link_clickable(file_path):
                    user_msg_content = user_msg_content.replace(
                        f"{img_prefix}[{file_name}]({file_path})",
                        file_name,
                    )
                continue
            files.append((file_name, file_path))
            user_msg_content = user_msg_content.replace(
                f"{img_prefix}[{file_name}]({file_path})",
                file_name,
            )
        elements = file_display(files, session_cwd_path)
        # ユーザーにメッセージとともにファイルや画像を送信
        await cl.Message(
            author="TaskWeaver",
            content=f"{user_msg_content}",
            elements=elements if len(elements) > 0 else None,
        ).send()


# このスクリプトが直接実行された場合の処理を記述します。
# スクリプトがモジュールとして他のファイルからインポートされたときには、このブロック内のコードが実行されないようにしています。
if __name__ == "__main__":
    # chainlitのコマンドラインインターフェースからrun_chainlitをインポート
    from chainlit.cli import run_chainlit

    # このファイルをchainlitアプリケーションとして起動する関数を呼び出します。
    # __file__は現在のスクリプトファイルの名前を指します。
    run_chainlit(__file__)
