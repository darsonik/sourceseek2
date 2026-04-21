from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_fireworks import ChatFireworks

from app.core.config import settings
from app.agents.tools import keyword_search_tool, semantic_search_tool

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# --- Define Tools ---
# Tools are now imported from app.agents.tools

# --- Define Graph Components ---

tools = [keyword_search_tool, semantic_search_tool]

# Initialize the Fireworks LLM
llm = ChatFireworks(
    model=settings.VISION_MODEL_NAME, # We reuse the model name from config for the agent
    api_key=settings.VISION_MODEL_API_KEY
)
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState):
    """
    The main reasoning node. It looks at the conversation history and decides whether to 
    call a tool (search DB) or return a final synthesized answer.
    """
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    """
    Router function to determine the next step after the agent node.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM decided to call a tool, route to the tool node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, it means the LLM synthesized a final answer, so we end
    return END

# --- Compile the Graph ---

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

# Add edges
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
workflow.add_edge("tools", "agent")

search_app = workflow.compile()

def run_search_agent(query: str) -> str:
    """
    Helper function to invoke the compiled agent with a user query.
    """
    system_prompt = (
        "You are a helpful AI assistant connected to a document database. "
        "When a user asks a question, decide whether you need to do an exact keyword match "
        "(for IDs, names, exact phrases) or a semantic match (for conceptual questions). "
        "Use the provided tools to search. "
        "Once you have the search results, synthesize a highly accurate answer for the user. "
        "ALWAYS include citations in your answer, referring to the Filename and the exact location metadata "
        "(e.g., 'according to document.pdf on page 4, line 12...')."
    )
    
    inputs = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
    }
    
    # Run the graph and get the final state
    final_state = search_app.invoke(inputs)
    
    # Return the content of the very last message (the LLM's final synthesized response)
    return final_state["messages"][-1].content
