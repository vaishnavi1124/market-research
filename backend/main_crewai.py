import os
os.environ["CREWAI_TELEMETRY_DISABLED"] = "1"
import sys
import asyncio
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import tool
# ---------------- UPDATED: import DB tools additively ----------------
from mcp_server import tavily_search, get_tavily_schema, rag_mcp_tool, rag_upsert, \
    db_insert_writer_report, db_update_writer_report, db_delete_writer_report, db_get_reports
from langchain_core.prompts import ChatPromptTemplate
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
 
# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
 
# -------------------------------
# LLM Configuration
# -------------------------------
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)
 
# -------------------------------
# CrewAI Tools (Tavily replacing Serper)
# -------------------------------
@tool
def tavily_tool(query: str) -> str:
    """Perform market research using Tavily API for web search results"""
    return tavily_search(query)
 
@tool
def tavily_schema_tool() -> str:
    """Get the schema for Tavily API response structure"""
    return get_tavily_schema()
 
@tool
def rag_tool(query: str) -> str:
    """Retrieve relevant research from the vector database"""
    return rag_mcp_tool(query)
 
# -------------------------------
# Research Agents
# -------------------------------
research_agent = Agent(
    role="Market Research",
    goal="Collect comprehensive market research data using Tavily API also web.",
    backstory="""You are an expert at gathering market research data from the web.
    You specialize in finding the most relevant and up-to-date information from company websites,
    news sources, and market reports. Your focus is on breadth and completeness of data collection.""",
    llm=llm,
    tools=[tavily_tool, tavily_schema_tool],
    memory=True,
    verbose=True,
    allow_delegation=True
)
 
research_analyst = Agent(
    role="Market Research Analyst",
    goal="Analyze collected market research data and provide actionable insights.",
    backstory="""You are a senior market research analyst with years of experience interpreting data.
    You take raw research data and transform it into strategic insights, identifying trends,
    competitive advantages, and market opportunities. You're meticulous in your analysis and
    always cross-reference multiple data points.
    Process data into insights, trends, and visualizations for reports or query responses.""",
    llm=llm,
    memory=True,
    verbose=True,
    allow_delegation=True
)
 
research_writer = Agent(
    role="Research Writer",
    goal="Summarize and present market research analysis in a clear, concise, and visually appealing report for customers.Create tables.",
    backstory="""You are a skilled business report writer who specializes in making complex research data
    understandable and engaging for clients. You focus on clarity, professional tone, and formatting.""",
    llm=llm,
    verbose=True,
    allow_delegation=False
)
 
chat_agent = Agent(
    role="Chat Agent",
    goal="Answer user queries based on previous research using RAG tool",
    backstory="""You are a Chat Agent that answers queries using retrieved information from past researches.
    Use the rag_tool to retrieve relevant data, then formulate a comprehensive answer based on that information.
    If no relevant data is found, state that and suggest performing new research.""",
    llm=llm,
    tools=[rag_tool],
    verbose=True,
    allow_delegation=False
)
 
router_agent = Agent(
    role="Router Agent",
    goal="Determine if the query is a new research topic or a follow-up on previous one",
    backstory="""You are a Router Agent.
    Analyze if the query is a new market research topic or related to previous ones.
    Based on the previous topics provided, decide.
    If it seems unrelated or new, choose 'new'. If related or a follow-up, choose 'follow-up'.
    Output ONLY 'new' or 'follow-up' without any additional text or explanation.""",
    llm=llm,
    verbose=True,
    allow_delegation=False
)
 
 
# -------------------------------
# Task Builder
# -------------------------------
def build_research_tasks(query: str) -> list[Task]:
    gather_task = Task(
        description=f"""Gather comprehensive market research data on: {query}
       
        Specific Requirements:
        1. Use serper_tool to get fresh search results
        2. Collect data from top 10 companies in this market
        3. For each company, gather:
           - Company name and website
           - Product/service offerings
           - Pricing information (if available)
           - Recent news/announcements
        4. Include any available market reports or industry analyses
        5. Organize data clearly for analysis
        6. Analyze competitors, entry barriers, and profitability using SWOT, PEST, and Porter’s Five Forces (collect required inputs and evidence for each).
        7. Segment the market into TAM, SAM, and SOM with any available figures, sources, and explicit assumptions for later validation.""",
        agent=research_agent,
        expected_output="A well-organized collection of raw market data including company information, products, pricing, and market trends."
    )
   
    analyze_task = Task(
        description=f"""Analyze the collected market research data on: {query}
       
        Analysis Guidelines:
        1. Identify the top 5-10 market players
        2. Compare their product offerings
        3. Analyze pricing strategies
        4. Identify market trends and gaps
        5. Highlight competitive advantages
        6. Provide strategic recommendations
        7. Include sources for all data points.
        8. Format the report professionally
        9. Provide a concise SWOT for key competitors.
        10. Provide a PEST analysis summarizing macro factors.
        11. Summarize Porter’s Five Forces with evidence-backed judgments (High/Medium/Low).
        12. Size and justify TAM, SAM, SOM (show calculations, assumptions, and data sources).""",
        agent=research_analyst,
        expected_output="A comprehensive market research report with analysis, trends, competitive landscape, and strategic recommendations.",
        context=[gather_task]
    )
 
    writer_task = Task(
        description=f"""Summarize the research analysis for: {query}
       
        Presentation Guidelines:
        1. Write an engaging executive summary
        2. Simplify complex points without losing meaning
        3. Use bullet points, headings, and formatting for readability
        4. Keep it concise (max 2 pages worth of text)
        5. Maintain professional tone
        6. Include actionable recommendations
        7. Create a tables for appropriate data visualization
        8. Create  tables for key data points.
        9. Ensure all sources are preserved in an appendix section
        10. Include brief sections for SWOT, PEST, Porter’s Five Forces, and a TAM/SAM/SOM snapshot (concise, board-ready).""",
        agent=research_writer,
        expected_output="A client-ready market research summary that is clear, concise, and professionally formatted.",
        context=[analyze_task]
    )
 
    return [gather_task, analyze_task, writer_task]
 
# -------------------------------
# Crew Setup
# -------------------------------
crew = Crew(
    agents=[research_agent, research_analyst, research_writer],
    tools=[tavily_tool, tavily_schema_tool],
    tasks=[],
    verbose=True,
)

# -------------------------------
# Main CrewAI Execution
# -------------------------------
async def main():
    print("✅ Market Research CrewAI Ready with Research Writer Agent!\n")
    
    previous_topics = []
    
    while True:
        query = input("🔍 Enter research topic (or commands: 'update:<id>', 'delete:<id>', 'list[:topic_like]', or 'exit'): ")
        if query.lower() in ['exit', 'quit']:
            break

        # ---------------- NEW: simple DB commands for update/delete/list ----------------
        try:
            if query.lower().startswith("update:"):
                # Syntax: update:<id>
                id_part = query.split(":", 1)[1].strip()
                if not id_part.isdigit():
                    print("⚠️ Use: update:<id>")
                    continue
                rid = int(id_part)
                new_topic = input("New topic (leave blank to keep same): ").strip()
                new_client = input("New client name (leave blank to keep same): ").strip()
                new_research = input("New research content (leave blank to keep same): ").strip()
                res = db_update_writer_report(rid, topic=new_topic or None,client_name=new_client or None, research=new_research or None)
                print(res)
                continue

            if query.lower().startswith("delete:"):
                # Syntax: delete:<id>
                id_part = query.split(":", 1)[1].strip()
                if not id_part.isdigit():
                    print("⚠️ Use: delete:<id>")
                    continue
                rid = int(id_part)
                res = db_delete_writer_report(rid)
                print(res)
                continue

            if query.lower().startswith("list"):
                # Syntax: list  OR list:<topic_like>
                topic_like = None
                if ":" in query:
                    topic_like = query.split(":", 1)[1].strip() or None
                res = db_get_reports(limit=10, topic_like=topic_like)
                print(res)
                continue
        except Exception as e:
            print(f"❌ DB Command Error: {e}")
            continue
        # ---------------- END NEW ----------------

        try:
            # Routing
            route_task = Task(
                description=f"""Analyze the following query: {query}
Previous topics: {', '.join(previous_topics) if previous_topics else 'None'}
Determine if this is a new research topic or a follow-up/related to previous topics.
Output ONLY 'new' or 'follow-up' without any additional text.""",
                agent=router_agent,
                expected_output="'new' or 'follow-up'"
            )
            
            route_crew = Crew(
                agents=[router_agent],
                tasks=[route_task],
                verbose=True
            )
            
            decision = (await route_crew.kickoff_async()).raw.strip().lower()
            print(f"Routing decision: {decision}")
            
            if decision == 'new':
                tasks = build_research_tasks(query)
                crew.tasks = tasks
                
                result = await crew.kickoff_async({"input": query})
                print(f"\n📊 Final Customer Report:\n{result}\n")

                safe_topic = query.replace(" ", "_").replace("/", "_")
                if hasattr(tasks[1], 'output') and tasks[1].output:
                    analyst_pdf_name = f"{safe_topic}_analyst_report.pdf"
                    save_to_pdf(str(tasks[1].output), analyst_pdf_name)
                    print(f"💾 Research Analyst report saved to Docs/{analyst_pdf_name}")

                if hasattr(tasks[2], 'output') and tasks[2].output:
                    writer_pdf_name = f"{safe_topic}_writer_report.pdf"
                    save_to_pdf(str(tasks[2].output), writer_pdf_name)
                    print(f"💾 Research Writer report saved to Docs/{writer_pdf_name}")
                    
                    # Upsert to RAG
                    upsert_result = rag_upsert(str(tasks[2].output), query)
                    print(f"💾 Upserted to RAG: {upsert_result}")

                    # ---------------- NEW: Insert Writer report to DB ----------------
                    try:
                        db_res = db_insert_writer_report(topic=query, research=str(tasks[2].output))
                        print(db_res)
                    except Exception as e:
                        print(f"❌ DB Insert Error: {e}")
                    # ---------------------------------------------------------------

                previous_topics.append(query)
            
            else:  # follow-up
                chat_task = Task(
                    description=f"""Answer the following query using the rag_tool to retrieve relevant previous research data: {query}
Use the retrieved information to provide a detailed answer.
If no relevant data is found, inform the user and suggest performing new research.""",
                    agent=chat_agent,
                    expected_output="A detailed answer based on previous research."
                )
                
                chat_crew = Crew(
                    agents=[chat_agent],
                    tasks=[chat_task],
                    tools=[rag_tool],
                    verbose=True
                )
                
                result = await chat_crew.kickoff_async()
                print(f"\n📊 Follow-up Answer:\n{result}\n")
                
                # If RAG tool fails to find relevant data, fall back to new research
                if "No relevant data was found" in str(result):
                    print("⚠️ RAG tool failed to find relevant data. Initiating new research...")
                    tasks = build_research_tasks(query)
                    crew.tasks = tasks
                    
                    result = await crew.kickoff_async({"input": query})
                    print(f"\n📊 Final Customer Report:\n{result}\n")

                    safe_topic = query.replace(" ", "_").replace("/", "_")
                    if hasattr(tasks[1], 'output') and tasks[1].output:
                        analyst_pdf_name = f"{safe_topic}_analyst_report.pdf"
                        save_to_pdf(str(tasks[1].output), analyst_pdf_name)
                        print(f"💾 Research Analyst report saved to Docs/{analyst_pdf_name}")

                    if hasattr(tasks[2], 'output') and tasks[2].output:
                        writer_pdf_name = f"{safe_topic}_writer_report.pdf"
                        save_to_pdf(str(tasks[2].output), writer_pdf_name)
                        print(f"💾 Research Writer report saved to Docs/{writer_pdf_name}")
                        
                        # Upsert to RAG
                        upsert_result = rag_upsert(str(tasks[2].output), query)
                        print(f"💾 Upserted to RAG: {upsert_result}")

                        # ---------------- NEW: Insert Writer report to DB ----------------
                        try:
                            db_res = db_insert_writer_report(topic=query, research=str(tasks[2].output))
                            print(db_res)
                        except Exception as e:
                            print(f"❌ DB Insert Error: {e}")
                        # ---------------------------------------------------------------

                    previous_topics.append(query)
        
        except Exception as e:
            print(f"❌ Error: {e}")


# -------------------------------
# Entry Point
# -------------------------------
if __name__ == "__main__":
    asyncio.run(main())
