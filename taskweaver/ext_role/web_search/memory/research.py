from typing import TypedDict, List, Annotated
import operator
from taskweaver.module.event_emitter import PostEventProxy

class ResearchState(TypedDict):
    task: dict
    initial_research: str
    sections: List[str]
    research_data: List[dict]
    # Report layout
    title: str
    headers: dict
    date: str
    table_of_contents: str
    introduction: str
    conclusion: str
    sources: List[str]
    report: str
    # [追加] PostProxyオブジェクト
    # LangGraph 内で扱いたいので追加した
    post_proxy: PostEventProxy


