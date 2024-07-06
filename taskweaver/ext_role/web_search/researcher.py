from gpt_researcher.master.agent import GPTResearcher
from colorama import Fore, Style
from .utils.views import print_agent_output
# from taskweaver.module.event_emitter import PostEventProxy    # 必要ない気がする
from taskweaver.memory.attachment import AttachmentType


class ResearchAgent:
    def __init__(self):
        pass

    async def research(self, query: str, research_report: str = "research_report", parent_query: str = "", verbose=True):
        """初期計画を立案"""
        # gpt_researcher/master/agent.py
        researcher = GPTResearcher(query=query, report_type=research_report, parent_query=parent_query, verbose=verbose)
        # Conduct research on the given query
        await researcher.conduct_research()
        # Write the report
        report = await researcher.write_report()

        return report

    async def run_subtopic_research(self, parent_query: str, subtopic: str, verbose: bool = True):
        try:
            report = await self.research(parent_query=parent_query, query=subtopic,
                                         research_report="subtopic_report", verbose=verbose)
        except Exception as e:
            print(f"{Fore.RED}Error in researching topic {subtopic}: {e}{Style.RESET_ALL}")
            report = None
        return {subtopic: report}

    async def run_initial_research(self, research_state: dict):
        task       = research_state.get("task")
        query      = task.get("query")
        post_proxy = research_state.get("post_proxy")    # ★ post_proxy も受け取るようにした
        print_agent_output(f"Running initial research on the following query: {query}", agent="RESEARCHER")
        # 追加[ update_attachment に修正]
        post_proxy.update_attachment(
            message=f"ResearchAgent: 初期計画を立案中…\n",
            type=AttachmentType.web_search_text,
        )
        return {"task": task, "initial_research": await self.research(query=query, verbose=task.get("verbose")), "post_proxy": post_proxy}

    async def run_depth_research(self, draft_state: dict):
        """サブトピックの調査"""
        task = draft_state.get("task")     # task.json
        topic = draft_state.get("topic")   # サブトピック
        parent_query = task.get("query")   # プランナーから渡されたクエリ
        verbose = task.get("verbose")
        print_agent_output(f"Running in depth research on the following report topic: {topic}", agent="RESEARCHER")
        # print("デバッグ run_depth_research関数。3秒間スリープする")
        # import asyncio
        # print("task")
        # print(task)
        # #→ {'query': 'Claude 3.5 Soonet', 'max_sections': 3, 'publish_formats': {'markdown': True, 'pdf': True, 'docx': True}, 'follow_guidelines': False, 'model': 'google/gemini-flash-1.5', 'guidelines': ['The report MUST be written in APA format', 'Each sub section MUST include supporting sources using hyperlinks. If none exist, erase the sub section or rewrite it to be a part of the previous section', 'The report MUST be written in spanish'], 'verbose': True}
        # print("サブトピック")
        # print(topic)             # ちゃんと、サブトピック(アウトライントピック)のリストの中身になっていた
        # print("parent_query")
        # print(parent_query)      # プランナーから渡されたクエリー「Claude 3.5 Soonet」になっていた
        # await asyncio.sleep(3)
        research_draft = await self.run_subtopic_research(parent_query, topic, verbose)
        return {"draft": research_draft}
