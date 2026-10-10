import typer
import re
from rich.console import Console
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from reachai.core.config import settings
from reachai.services.ingestion_service import IngestionService

console = Console()

# Shared DB session factory
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_service() -> IngestionService:
    session = SessionLocal()
    try:
        return IngestionService(session), session
    finally:
        pass  # Caller manages session


app = typer.Typer(name="reachai", help="Personal outreach intelligence agent")

@app.command()
def version():
    console.print("ReachAI v0.1.0")

@app.command()
def company():
    console.print("[bold blue]Company commands:[/bold blue] list, show, add")

@app.command()
def show():
    pass

@app.callback()
def main(ctx: typer.Context):
    pass

@app.command()
def agent():
    from reachai.agent.agent_engine import ReachAIAgent
    from langchain_core.messages import HumanMessage
    console.print("[bold green]ReachAI Agent Mode (LangGraph + Native Tools)[/bold green]")
    console.print("Type your request. Type 'exit' to quit.\n")

    reach_agent = ReachAIAgent()
    graph = reach_agent.build_graph()
    console.print(
        f"[dim]LLM: {reach_agent.provider_name} / {reach_agent.model_name}[/dim]"
    )

    session = SessionLocal()
    try:
        while True:
            try:
                user_input = input("> ")
            except EOFError:
                break
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break
            if not user_input.strip():
                continue

            initial_state = {
                "input": user_input,
                "messages": [HumanMessage(content=user_input)],
                "intermediate_steps": [],
            }
            try:
                result = graph.invoke(
                    initial_state,
                    {
                        "configurable": {"thread_id": "reachai_session"},
                        # Multiple create_contact calls from one LLM response
                        # must not race to create the same company.
                        "max_concurrency": 1,
                    },
                )
                if notice := reach_agent.consume_fallback_notice():
                    console.print(f"[yellow]{notice}[/yellow]")
                messages = result.get("messages", [])
                final_response = None
                for msg in reversed(messages):
                    if isinstance(msg, SystemMessage) or isinstance(msg, ToolMessage):
                        continue
                    if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                        continue
                    if hasattr(msg, "content") and msg.content:
                        final_response = msg.content
                        break
                if final_response:
                    console.print(f"[bold cyan]Agent:[/bold cyan] {final_response}")
                else:
                    last_msg = messages[-1] if messages else None
                    if last_msg and hasattr(last_msg, "content"):
                        console.print(f"[dim]Agent (last message): {last_msg.content}[/dim]")
                    else:
                        console.print("[yellow]Agent processed request (no final text response).[/yellow]")
            except Exception as e:
                console.print(f"[red]Agent error:[/red] {e}")
                session.rollback()
    finally:
        session.close()



@app.command()
def contact():
    console.print("[bold cyan]Contact commands:[/bold cyan] add (via agent mode)")


@app.command()
def opportunity():
    console.print("[bold magenta]Opportunity commands:[/bold magenta] create (via agent mode)")


@app.command()
def referrals():
    console.print("[bold cyan]Referral commands:[/bold cyan] query (via agent mode)")


@app.command()
def outreach():
    console.print("[bold green]Outreach commands:[/bold green] history (via agent mode)")
