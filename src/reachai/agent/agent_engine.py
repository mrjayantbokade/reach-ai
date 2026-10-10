"""The native LangGraph/LangChain tool-calling agent used by the CLI."""

from operator import add
from typing import Annotated, Any, List, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from reachai.core.config import settings
from reachai.tools.tools import (
    create_contact,
    create_outreach_event,
    create_opportunity,
    create_referral,
    get_company,
    get_company_contacts,
    get_company_emails,
    get_company_opportunities,
    get_company_phones,
    get_contact,
    get_contact_sources,
    get_outreach_history,
    get_referrals,
    get_uncontacted_company_contacts,
    list_companies,
    list_contacts,
    list_opportunities,
    list_outreach_events,
    list_referrals,
    rank_outreach_candidates,
    search_company,
    search_contact,
    search_opportunity,
)


class AgentState(TypedDict):
    """Conversation state accumulated by LangGraph."""

    input: str
    messages: Annotated[List[BaseMessage], add]
    intermediate_steps: Annotated[List[Any], add]


SYSTEM_PROMPT = """You are ReachAI, a personal outreach intelligence agent.
Use the supplied database tools whenever the user asks about saved companies,
contacts, email addresses, referrals, opportunities, or outreach history. Never
invent records or generate SQL.

CRITICAL CONTACT RULE: Before asking for a company, scan the entire latest user
message for every email address. If any address has a non-public business domain,
you already have the company signal and MUST call create_contact; never ask
which company the person belongs to. Keep a personal email in the same prompt
on that same contact. For `Person Name <person@gmail.com>,
person.name@company.com save this contact`, immediately save one Person Name
contact with both addresses at Company. A Gmail-only prompt is the only case
that needs a company clarification.

Treat the full conversation as context. A short follow-up answers the most
recent unresolved request; never discard the company, contacts, email addresses,
or phone numbers supplied earlier in the conversation. Before asking a question,
carefully inspect the current message and prior messages for the answer.

For a request to save a contact, call create_contact immediately when the
message supplies an explicit company name and at least one email address or
phone number. Extract structured fields from the message before the tool call.
When a name is not written explicitly but an email local-part is clearly a
person's name, derive it: `person@company.com` becomes `Person` and
`person.name@company.com` becomes `Person Name`. Only omit full_name
when no readable name can be derived; the application then saves "N/A". Do not
ask for a name. Pass every supplied email address in `emails` and every
supplied mobile/phone number in `phones` in the same tool call. If the company is missing, ask exactly which company the
contact belongs to only when no business email domain is available. For a
business email, infer the company from its domain: for example,
`person.name@company.com` belongs to Company, and pass that inferred company
to create_contact (or omit company_name and let the deterministic service do
the same). Never infer a company from public email domains such as Gmail. If
the company is present but there is no email or phone, ask for one contact
method.

When the user pastes several names/email addresses (including To, Cc, angle
brackets, commas, or line breaks) and then states a company such as "save these
contacts for Example Corp", that company applies to every pasted person. Extract
each person and call create_contact once per person. Do not ask which company
each person belongs to when it was already supplied. Derive readable names from
clear email local-parts when a display name is missing, and use "N/A" only when
no name can be reasonably derived.

Group multiple addresses for the same person into one create_contact call. A
personal email and a business email in the same prompt can belong to the same
named person; pass both in that person's `emails` list rather than creating two
contacts. For example, `Person Name <person@gmail.com>,
person.name@company.com` is one contact named Person Name with both
emails. Infer the company from the business address (`company.com`) when
the user did not explicitly state a company. Do not treat a Gmail address as a
separate person merely because it has a different domain.

Before asking for a company, scan every line and every comma-separated item in
the latest user message for email addresses; never inspect only the first email.
If any non-public business email occurs anywhere in that same message, do not
ask for the company. Use that business domain for company inference and attach
all accompanying personal/business emails to the same named person. For the
pattern `Person Name <person@gmail.com>, person.name@company.com save this
contact`, you MUST call create_contact once with both emails. Do not reply with
a question.

Example: for `Person One <person.one@example.com>, Person Two <person.two@example.com>; save these contacts
for Example Inc`, call create_contact once for Person One and once for Person Two,
using company_name="Example Inc" for both. Do not ask a follow-up question.

Complete a pasted batch in the same graph run. Before giving a final success
message, verify you have called create_contact for every distinct person/email
group in the user's original batch. Do not report a partial save as complete,
and never defer remaining contacts to a later user turn. After all tool results
are available, send one final summary that accounts for the entire batch.

For a request to get contacts at a company, first call search_company, then use
the returned company ID with get_company_contacts. Do not invent contact data.
If search_company returns a closest rather than exact match, use the closest
match's company ID immediately and complete the requested read query in the
same graph run. State the selected closest company in the final answer; do not
ask a confirmation question for read-only requests.

For a request asking how many companies exist or which companies are saved,
call list_companies and answer directly from its result.

For a request such as "list/show all emails for <company>", first resolve the
company if necessary, then call get_company_emails. When that tool returns one
or more email addresses, reply with exactly those addresses, one per line, and
no heading, explanation, name, phone number, or other contact detail.

Follow tool results faithfully. You decide which tools to call and whether more
than one is needed; do not describe a tool call as if it had happened unless it
actually happened."""


class ReachAIAgent:
    def __init__(self):
        self.local_llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0.0,
        )
        self.tools = [
            search_company,
            list_companies,
            list_contacts,
            get_company,
            search_contact,
            get_contact,
            get_company_contacts,
            get_company_emails,
            get_company_phones,
            get_contact_sources,
            create_contact,
            create_opportunity,
            search_opportunity,
            get_company_opportunities,
            list_opportunities,
            get_referrals,
            create_referral,
            list_referrals,
            get_outreach_history,
            create_outreach_event,
            list_outreach_events,
            get_uncontacted_company_contacts,
            rank_outreach_candidates,
        ]
        self.local_llm_with_tools = self.local_llm.bind_tools(self.tools)
        self._fallback_notice: str | None = None

        if settings.OPENROUTER_API_KEY:
            self.llm = ChatOpenAI(
                base_url=settings.OPENROUTER_BASE_URL,
                api_key=settings.OPENROUTER_API_KEY,
                model=settings.OPENROUTER_MODEL,
                temperature=0.0,
            )
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.provider_name = "OpenRouter"
            self.model_name = settings.OPENROUTER_MODEL
            self.using_local_fallback = False
        else:
            self.llm = self.local_llm
            self.llm_with_tools = self.local_llm_with_tools
            self.provider_name = "LM Studio"
            self.model_name = settings.LLM_MODEL
            self.using_local_fallback = True

    def _switch_to_local_fallback(self) -> None:
        self.llm = self.local_llm
        self.llm_with_tools = self.local_llm_with_tools
        self.provider_name = "LM Studio (fallback)"
        self.model_name = settings.LLM_MODEL
        self.using_local_fallback = True
        self._fallback_notice = (
            "OpenRouter was unavailable; switched to the local LM Studio model "
            f"({settings.LLM_MODEL})."
        )

    def consume_fallback_notice(self) -> str | None:
        """Return a one-time provider failover notice for the CLI."""
        notice = self._fallback_notice
        self._fallback_notice = None
        return notice

    def agent_node(self, state: AgentState) -> dict:
        """Ask the bound chat model to select tools or provide the final answer."""
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        try:
            response = self.llm_with_tools.invoke(messages)
        except Exception as error:
            if self.using_local_fallback:
                raise
            self._switch_to_local_fallback()
            response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def build_graph(self):
        """Build the standard LLM → ToolNode → LLM LangGraph loop."""
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self.agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            tools_condition,
            {"tools": "tools", END: END},
        )
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=MemorySaver())
