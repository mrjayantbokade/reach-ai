from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class AgentState:
    user_input: str = ""
    resolved_company_id: Optional[int] = None
    resolved_company_name: Optional[str] = None
    resolved_opportunity_id: Optional[int] = None
    current_workflow: Optional[str] = None  # ingestion, opportunity_lookup, etc.
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, str]] = field(default_factory=list)
