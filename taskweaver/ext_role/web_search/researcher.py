# from gpt_researcher import GPTResearcher              # configディレクトリ にコンフィグファイルとして JSON で用意することもできそうだけど、ベタ書きでも OK なので一旦コンフィグファイルは不要。
from gpt_researcher.master.agent import GPTResearcher   # → 置く場所の書き方はこっちな気がする。 agent.py の中で色々 import しないといけない気がするが、一旦動かしてエラーが出たら対応する
from colorama import Fore, Style
from .utils.views import print_agent_output
# from taskweaver.module.event_emitter import PostEventProxy    # 必要ない気がする


class ResearchAgent:
    def __init__(self):
        pass

    async def research(self, query: str, research_report: str = "research_report", parent_query: str = "", verbose=True):
        # Initialize the researcher
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
        task = research_state.get("task")
        post_proxy = research_state.get("post_proxy")    # ★ post_proxy も受け取るようにした
        query = task.get("query")
        print_agent_output(f"Running initial research on the following query: {query}", agent="RESEARCHER")
        # 追加
        post_proxy.update_message(
            f"ResearchAgent: 初期計画を立案し実行中…\n"
        )
        return {"task": task, "initial_research": await self.research(query=query, verbose=task.get("verbose")), "post_proxy": post_proxy}

    async def run_depth_research(self, draft_state: dict):
        task = draft_state.get("task")
        topic = draft_state.get("topic")
        parent_query = task.get("query")
        verbose = task.get("verbose")
        print_agent_output(f"Running in depth research on the following report topic: {topic}", agent="RESEARCHER")
        research_draft = await self.run_subtopic_research(parent_query, topic, verbose)
        return {"draft": research_draft}
