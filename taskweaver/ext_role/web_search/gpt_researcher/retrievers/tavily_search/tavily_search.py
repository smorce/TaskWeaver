# Tavily API Retriever

# libraries
import os
from tavily import TavilyClient
from duckduckgo_search import DDGS



# HTMLをマークダウン化させる
import requests
import markdownify
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import logging
# from art import tprint
import unicodedata
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PegasusRevision:
    """
    PegasusRevisionクラス: ウェブページをダウンロードしてMarkdownに変換するクラス。Pegasusクラスを少し改良した。
    """

    def __init__(self, output_dir=None, exclude_selectors=None,
                 exclude_keywords=None, output_extension=".md",
                 user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15'
                 ):
        """
        初期化メソッド

        :param output_dir: 出力ディレクトリ
        :param exclude_selectors: 除外するCSSセレクタのリスト
        :param exclude_keywords: 除外するキーワードのリスト
        :param output_extension: 出力ファイルの拡張子
        :param user_agent: リクエスト時のユーザーエージェント
        """
        self.output_dir = output_dir
        self.exclude_selectors = exclude_selectors
        self.exclude_keywords = exclude_keywords
        self.visited_urls = set()
        self.output_extension = output_extension
        self.user_agent = user_agent

        # アスキーアートでPegasusを表示
        # tprint("  Pegasus  ", font="rnd-xlarge")
        # 初期化パラメータをログに出力
        # logger.info("初期化パラメータ:")
        # logger.info(f"  output_dir: {output_dir}")
        # logger.info(f"  exclude_selectors: {exclude_selectors}")
        # logger.info(f"  exclude_keywords: {exclude_keywords}")
        # logger.info(f"  output_extension: {output_extension}")
        # logger.info(f"  user_agent: {user_agent}")

    def download_and_convert(self, url):
        """
        URLからコンテンツをダウンロードし、Markdownに変換する

        :param url: ダウンロードするURL
        """
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        try:
            # ユーザーエージェントを設定してリクエスト
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 除外セレクタに該当する要素を削除
            if self.exclude_selectors:
                for selector in self.exclude_selectors:
                    for element in soup.select(selector):
                        element.decompose()

            # HTMLをMarkdownに変換
            markdown_content = markdownify.markdownify(str(soup))
            # 過剰な改行を削除
            markdown_content = re.sub(r'\n{5,}', '\n\n\n\n', markdown_content)

            # テキストの有効性をチェック
            if not self.is_valid_text(markdown_content):
                logger.warning(f"無効なテキストを検出したため除外: {url}")
                return

            # 保存する必要はないのでコメントアウト
            # 出力ディレクトリを作成
            # parsed_url = urlparse(url)
            # domain = parsed_url.netloc
            # domain_dir = os.path.join(self.output_dir, domain)
            # os.makedirs(domain_dir, exist_ok=True)

            # 安全なファイル名を生成
            # safe_filename = self.get_safe_filename(parsed_url.path)
            # output_file = f"{domain_dir}/{safe_filename}{self.output_extension}"

            # Markdownをファイルに書き込み
            # with open(output_file, 'w', encoding='utf-8') as file:
                # file.write(markdown_content)

            return markdown_content

        except requests.exceptions.RequestException as e:
            logger.error(f"ダウンロードエラー: {url}: {e}")
        except IOError as e:
            logger.error(f"書き込みエラー: {output_file}: {e}")

    def is_valid_text(self, text):
        """
        テキストが有効かどうかをチェック（非ASCII文字の比率で判断）

        :param text: チェックするテキスト
        :return: テキストが有効な場合True、そうでない場合False
        """
        non_ascii_chars = re.findall(r'[^\x00-\x7F]', text)
        non_ascii_ratio = len(non_ascii_chars) / len(text)

        return non_ascii_ratio <= 0.3

    def get_safe_filename(self, path):
        """
        安全なファイル名を生成

        :param path: 元のファイルパス
        :return: 安全なファイル名
        """
        # ファイル名に使用できない文字を置換
        filename = path.strip('/').replace('/', '_')
        # Unicode正規化
        filename = unicodedata.normalize('NFKC', filename)
        # ASCII文字、数字、一部の記号以外を削除
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        filename = ''.join(c for c in filename if c in valid_chars)
        # 最大長を制限（例：255文字）
        return filename[:255]



class TavilySearch():
    """
    Tavily API Retriever
    """
    def __init__(self, query, topic="general"):
        """
        Initializes the TavilySearch object
        Args:
            query:
        """
        self.query = query
        self.api_key = self.get_api_key()
        self.client = TavilyClient(self.api_key)
        self.topic = topic

    def get_api_key(self):
        """
        Gets the Tavily API key
        Returns:

        """
        # Get the API key
        try:
            api_key = os.environ["TAVILY_API_KEY"]
        except:
            raise Exception("Tavily API key not found. Please set the TAVILY_API_KEY environment variable. "
                            "You can get a key at https://app.tavily.com")
        return api_key

    def search(self, max_results=7):
        """
        2024/07/06: [memo]現状はマークダウン化したコンテンツは使っていなくて、URL だけ使っているが、一旦このまま。gpt_researcher/master/agent.py の scrape_sites_by_query メソッドに関連あり。

        Searches the query
        Returns:
            「URLとマークダウン化したコンテンツの辞書」のリスト
        """
        try:
            # Search the query

            # Tavily の精度向上テクニック：https://zenn.dev/sekitobatech/articles/343fbaac1b3da9
            # メモ：search_depth="advanced" とすると、フォローアップクエスチョン(=サジェスト)が表示される
            # results = self.client.search(self.query, search_depth="basic", max_results=max_results, topic=self.topic)
            # sources = results.get("results", [])


            # JavaScriptのような動的な内容も含めて全て取得する
            results = self.client.search(query=self.query, max_results=max_results, search_depth="advanced", include_raw_content=True, topic=self.topic)
            sources = results.get("results", [])
            # 余計なヘッダーやフッターがあれば削除
            for obj in sources:
                if obj['content'][-3:]:
                    obj['content'] = obj['raw_content']
                    obj['raw_content'] = None


            if not sources:
                raise Exception("No results found with Tavily API search.")
            # Return the results
            search_response = [{"href": obj["url"], "body": obj["content"]} for obj in sources]
        except Exception as e: # Fallback in case overload on Tavily Search API
            print(f"Error: {e}. Fallback to DuckDuckGo Search API...")
            ddg = DDGS()
            search_response = ddg.text(self.query, region='wt-wt', max_results=max_results)


        # print("デバッグ search関数")
        # print("クエリー:", self.query)
        # try:
        #     for d in search_response:
        #         print('----------------------')
        #         print(d["body"])
        # except Exception as e:
        #     print("search_response")
        #     print(search_response)


        # print("デバッグ ペガサスでHTMLをマークダウン化")
        pegasus = PegasusRevision()
        try:
            for d in search_response:
                url = d["href"]
                # print("url:", url)
                d["body"] = pegasus.download_and_convert(url)   # コンテンツを上書きする
                # print("マークダウン化したファイル")
                # print(d["body"])
        except Exception as e:
            print(f"Error: {e}.")


        return search_response
