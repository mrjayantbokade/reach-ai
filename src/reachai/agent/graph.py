from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from operator import add


class AgentStateDict(TypedDict):
    user_input: str
    resolved_company_id: Optional[int]
    resolved_company_name: Optional[str]
    resolved_opportunity_id: Optional[int]
    current_workflow: Optional[str]
    extracted_data: Dict[str, Any]
    tool_results: Annotated[List[Dict[str, Any]], add]
    messages: Annotated[List[str], add]
