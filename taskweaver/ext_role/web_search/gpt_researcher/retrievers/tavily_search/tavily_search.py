# Tavily API Retriever

# libraries
import os
from tavily import TavilyClient
from duckduckgo_search import DDGS


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
        Searches the query
        Returns:

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
        return search_response
