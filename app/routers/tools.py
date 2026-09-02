"""
Tool call REST endpoints.
Bridge between LLM (or direct API calls) and the gate layer.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any, Dict

from app.db import get_db
from app.tools import run_tool_call, ToolCallResult

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolCallRequest(BaseModel):
    """Request to execute a tool call."""
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.post("/call", response_model=ToolCallResult)
def call_tool(
    request: ToolCallRequest,
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Execute a tool call.
    
    The session_id is extracted from query parameter/header by the server,
    never specified by the client (preventing LLM confusion about whose session it is).
    
    Args:
        request: ToolCallRequest with tool_name and arguments
        session_id: User session ID (server-injected)
        db: SQLAlchemy session
    
    Returns:
        ToolCallResult with status, data, and message
    """
    result = run_tool_call(
        tool_name=request.tool_name,
        arguments=request.arguments,
        session_id=session_id,
        db=db,
    )
    return result
