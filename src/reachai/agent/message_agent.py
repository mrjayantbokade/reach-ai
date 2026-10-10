from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from reachai.core.config import settings


class MessageDraftAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0.3,
        )
        self.parser = StrOutputParser()

    def draft_for_contact(self, contact_name: str, company_name: str, opportunity_title: str) -> str:
        prompt = ChatPromptTemplate.from_template(
            """
Draft a brief, professional outreach message for {contact_name} at {company_name}
regarding the opportunity: {opportunity_title}.
Keep it concise (2-3 sentences). Be direct and respectful.
"""
        )
        chain = prompt | self.llm | self.parser
        try:
            return chain.invoke({
                "contact_name": contact_name,
                "company_name": company_name,
                "opportunity_title": opportunity_title,
            })
        except Exception as e:
            return f"Draft generation unavailable (LLM connection error): {e}"
