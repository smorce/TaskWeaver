from datetime import datetime
import json5 as json
import re
from .utils.views import print_agent_output
from .utils.llms import call_model
from taskweaver.memory.attachment import AttachmentType

sample_json = """
{
  "table_of_contents": A table of contents in markdown syntax (using '-') based on the research headers and subheaders,
  "introduction": An indepth introduction to the topic in markdown syntax and hyperlink references to relevant sources,
  "conclusion": A conclusion to the entire research based on all research data in markdown syntax and hyperlink references to relevant sources,
  "sources": A list with strings of all used source links in the entire research data in markdown syntax and apa citation format. For example: ['-  Title, year, Author [source url](source)', ...]
}
"""


class WriterAgent:
    def __init__(self):
        pass

    def get_headers(self, research_state: dict):
        return {
            "title": research_state.get("title"),
            "date": "Date",
            "introduction": "Introduction",
            "table_of_contents": "Table of Contents",
            "conclusion": "Conclusion",
            "references": "References"
        }

    def write_sections(self, research_state: dict):
        query = research_state.get("title")
        data = research_state.get("research_data")
        task = research_state.get("task")
        follow_guidelines = task.get("follow_guidelines")
        guidelines = task.get("guidelines")

        prompt = [{
            "role": "system",
            "content": "You are a research writer. Your sole purpose is to write a well-written "
                       "research reports about a "
                       "topic based on research findings and information.\n "
        }, {
            "role": "user",
            "content": f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                       f"Query or Topic: {query}\n"
                       f"Research data: {str(data)}\n"
                       f"Your task is to write an in depth, well written and detailed "
                       f"introduction and conclusion to the research report based on the provided research data. "
                       f"Do not include headers in the results.\n"
                       f"You MUST include any relevant sources to the introduction and conclusion as markdown hyperlinks -"
                       f"For example: 'This is a sample text. ([url website](url))'\n\n"
                       f"{f'You must follow the guidelines provided: {guidelines}' if follow_guidelines else ''}\n"
                       f"You MUST return nothing but a JSON in the following format (without json markdown):\n"
                       f"{sample_json}\n\n"

        }]

        response = call_model(prompt, task.get("model"), max_retries=2, response_format='json')
        # return json.loads(response)

        print("write_sections のデバッグ。JSON形式か？？  response")
        print(response)

        # 正規表現を使って{}の中身を抽出する
        match = re.search(r'\{.*\}', response, re.DOTALL)

        if match:
            json_str = match.group(0)
            # JSONをパースしてPythonの辞書型に変換する
            write_sections = json.loads(json_str)
            print("write_sections")
            print(write_sections)
        else:
            print("write_sections: JSON形式のデータが見つかりませんでした。")

        return write_sections


    def revise_headers(self, task: dict, headers: dict):
        prompt = [{
            "role": "system",
            "content": """You are a research writer.
Your sole purpose is to revise the headers data based on the given guidelines."""
        }, {
            "role": "user",
            "content": f"""Your task is to revise the given headers JSON based on the guidelines given.
You are to follow the guidelines but the values should be in simple strings, ignoring all markdown syntax.
You must return nothing but a JSON in the same format as given in headers data.
Guidelines: {task.get("guidelines")}\n
Headers Data: {headers}\n
"""

        }]

        response = call_model(prompt, task.get("model"), response_format='json')
        return {"headers": json.loads(response)}

    def run(self, research_state: dict):
        post_proxy = research_state.get("post_proxy")          # 追加
        # 追加
        post_proxy.update_attachment(
            message=f"EditorAgent: 与えられた調査結果からの序論、結論、参考文献のセクションを含む最終レポートを編集中…\n",
            type=AttachmentType.web_search_text,
        )

        print_agent_output(f"Writing final research report based on research data...", agent="WRITER")
        research_layout_content = self.write_sections(research_state)

        if research_state.get("task").get("verbose"):
            print_agent_output(research_layout_content, agent="WRITER")

        headers = self.get_headers(research_state)
        # ここでガイドラインを利用する
        if research_state.get("task").get("follow_guidelines"):
            print_agent_output("Rewriting layout based on guidelines...", agent="WRITER")
            headers = self.revise_headers(task=research_state.get("task"), headers=headers).get("headers")

        return {**research_layout_content, "headers": headers, "post_proxy": post_proxy}