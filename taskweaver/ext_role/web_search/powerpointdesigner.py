import os
from .utils.views import print_agent_output
from taskweaver.module.event_emitter import PostEventProxy
from .utils.file_formats import write_md_to_ppt

class PowerPointDesignerAgent:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def load_latest_markdown(directory):
        """
        指定されたディレクトリから最新のマークダウンファイルを読み込み、その内容を返す関数。

        Args:
        directory (str): マークダウンファイルを検索するディレクトリのパス。

        Returns:
        str: 最新のマークダウンファイルの内容。ファイルが存在しない場合は None を返す。
        """
        # ディレクトリ内の全ファイルを取得し、マークダウンファイルのみをフィルタリング
        files = [f for f in os.listdir(directory) if f.endswith('.md')]

        # ファイルが存在するかどうかのチェック
        if not files:
            print("No markdown files found in the directory.")
            return None

        # ファイルの最終更新時刻を取得し、最新のものを見つける
        latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join(directory, x)))

        # 最新のマークダウンファイルのパス
        latest_file_path = os.path.join(directory, latest_file)

        # ファイルを開いて内容を読み込む
        with open(latest_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        return content

    async def write_report_by_formats(self, md_content, output_dir):        
        await write_md_to_ppt(md_content, output_dir)           # ★Marpで実装した。他の関数と合わせて非同期にした。


    def run(self, post_proxy: PostEventProxy):
        print_agent_output(f"パワーポイントを作成中...", agent="POWERPOINTDESIGNER")
        post_proxy.update_message(
            f"ResearchAgent: パワーポイントを作成中…\n"
        )
        # mdファイルを開いて内容を読み込む
        md_content = load_latest_markdown(self.output_dir)
        # パワーポイントを作成して保存する
        await write_report_by_formats(md_content, self.output_dir)
        
        return post_proxy