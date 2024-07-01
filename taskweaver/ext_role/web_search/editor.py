from datetime import datetime
from .utils.views import print_agent_output
from .utils.llms import call_model
from langgraph.graph import StateGraph, END
import asyncio
import json
import re
from taskweaver.memory.attachment import AttachmentType

import sys
import os
# memory を読み込めるようにするため、現在のスクリプトのディレクトリを取得
project_root = os.path.dirname(os.path.abspath(__file__))

# プロジェクトのルートディレクトリを取得
sys.path.append(project_root)

from memory.draft import DraftState
try:
    from .researcher import ResearchAgent
    from .reviewer import ReviewerAgent
    from .reviser import ReviserAgent
except ImportError as e:
    print(f"editor.pyのエラー: Failed to import: {e}")
    # 代替処理やエラーハンドリングをここに追加


class EditorAgent:
    def __init__(self, task: dict):
        self.task = task

    def plan_research(self, research_state: dict):
        """
        Curate relevant sources for a query
        :param summary_report:
        :return:
        :param total_sub_headers:
        :return:
        """

        initial_research = research_state.get("initial_research")
        post_proxy       = research_state.get("post_proxy")          # 追加
        max_sections = self.task.get("max_sections")
        # 追加
        post_proxy.update_attachment(
            message=f"EditorAgent: 初期調査に基づいてレポートの概要と構成を計画中…\n",
            type=AttachmentType.web_search_text,
        )

        prompt = [{
            "role": "system",
            "content": "You are a research director. Your goal is to oversee the research project"
                       " from inception to completion.\n "
        }, {
            "role": "user",
            "content": f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                       f"Research summary report: '{initial_research}'\n\n"
                       f"Your task is to generate an outline of sections headers for the research project"
                       f" based on the research summary report above.\n"
                       f"You must generate a maximum of {max_sections} section headers.\n"
                       f"You must focus ONLY on related research topics for subheaders and do NOT include introduction, conclusion and references.\n"
                       f"You must return nothing but a JSON with the fields 'title' (str) and "
                       f"'sections' (maximum {max_sections} section headers) with the following structure: "
                       f"'{{title: string research title, date: today's date, "
                       f"sections: ['section header 1', 'section header 2', 'section header 3' ...]}}.\n "
        }]

        print_agent_output(f"Planning an outline layout based on initial research...", agent="EDITOR")
        response = call_model(prompt=prompt, model=self.task.get("model"), response_format="json")
        print("デバッグ。JSON形式か？？  response")
        print(response)

        # 正規表現を使って{}の中身を抽出する
        match = re.search(r'\{.*\}', response, re.DOTALL)

        if match:
            json_str = match.group(0)
            # JSONをパースしてPythonの辞書型に変換する
            plan = json.loads(json_str)
            print(plan)
        else:
            print("plan_research: JSON形式のデータが見つかりませんでした。")

        return {
            "title": plan.get("title"),
            "date": plan.get("date"),
            "sections": plan.get("sections"),
            "post_proxy": post_proxy                  # 追加
        }

    async def run_parallel_research(self, research_state: dict):
        """サブグラフを並列かつ独立して動かす"""
        # --------------------------------------------
        # サブグラフで動かすエージェント3つ
        ##### 研究者 (gpt-researcher) - サブトピックについて詳細な調査を行い、草稿を書きます。
        ##### レビュー担当者           - 一連の条件に基づいて下書きの正確性を検証し、フィードバックを提供します。
        ##### 校閲者                  - 校閲者のフィードバックに基づいて満足のいく内容になるまで下書きを修正します。
        # --------------------------------------------
        research_agent = ResearchAgent()
        reviewer_agent = ReviewerAgent()
        reviser_agent = ReviserAgent()
        # --------------------------------------------
        queries = research_state.get("sections")
        title = research_state.get("title")
        post_proxy = research_state.get("post_proxy")          # 追加
        # 追加
        post_proxy.update_attachment(
            message=f"EditorAgent: 各アウトライントピックについて並行してリサーチ中…\n",
            type=AttachmentType.web_search_text,
        )
        workflow = StateGraph(DraftState)

        workflow.add_node("researcher", research_agent.run_depth_research)
        workflow.add_node("reviewer", reviewer_agent.run)
        workflow.add_node("reviser", reviser_agent.run)

        # set up edges researcher->reviewer->reviser->reviewer...
        workflow.set_entry_point("researcher")
        workflow.add_edge('researcher', 'reviewer')
        workflow.add_edge('reviser', 'reviewer')
        # 条件付きエッジ。レビュー担当者によるレビューメモが存在する場合、グラフは修正担当者に指示されます。そうでない場合、サイクルは最終草案で終了します。
        workflow.add_conditional_edges('reviewer',
                                       (lambda draft: "accept" if draft['review'] is None else "revise"),
                                       {"accept": END, "revise": "reviser"})

        chain = workflow.compile()

        # Execute the graph for each query in parallel
        print_agent_output(f"Running the following research tasks in parallel: {queries}...", agent="EDITOR")
        # ainvoke なので複数のクエリーに対して非同期かつ並列で実行。各アウトライン トピックについて並行して実行する
        final_drafts = [chain.ainvoke({"task": research_state.get("task"), "topic": query, "title": title})
                        for query in queries]
        # asyncio.gather なので全部のタスクが終了するまで次には行かない
        research_results = [result['draft'] for result in await asyncio.gather(*final_drafts)]

        # リターンするときに、ResearchState に対応する Kye の Value が更新される
        return {"research_data": research_results, "post_proxy":post_proxy}
