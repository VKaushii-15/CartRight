"""
Chat endpoint: conversational checkout interface.
Routes user messages through Groq, executes tool calls via gate layer.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db import get_db
from app.groq_client import call_groq
from app.tools import run_tool_call
from app.tools.schemas import ToolCallResult, TOOL_MODEL_BY_NAME
from pydantic import ValidationError
from app.models import ChatMessage, PendingToolCall
import json
import re

router = APIRouter(prefix="/chat", tags=["chat"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ChatRequest(BaseModel):
    """User message for the chat endpoint."""
    message: str


class ToolCallExecution(BaseModel):
    """Result of executing a single tool call."""
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # "ok" or "rejected"
    result: Dict[str, Any]
    message: str


class ChatResponse(BaseModel):
    """Complete response from chat endpoint."""
    user_message: str
    assistant_message: str
    tool_calls_executed: List[ToolCallExecution]
    tool_count: int
    status: str  # "ok" (all tools executed) or "partial" (some failed)


# ============================================================================
# Chat Endpoint
# ============================================================================


@router.post("/{session_id}", response_model=ChatResponse)
def chat(
    session_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Conversational checkout interface.
    
    1. Receive user message
    2. Call Groq with tools attached (returns assistant response + tool calls)
    3. Execute each tool call via gate layer
    4. Return comprehensive response with all results
    
    Args:
        session_id: User session ID (cart/conversation context)
        request: ChatRequest with user message
        db: SQLAlchemy session
    
    Returns:
        ChatResponse with assistant message, tool results, and status
    """
    
    # Persist user message to DB
    user_msg = ChatMessage(session_id=session_id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()

    # If there's a pending under-specified tool-call for this session, try to resolve it
    pending = db.query(PendingToolCall).filter_by(session_id=session_id).order_by(PendingToolCall.created_at.desc()).first()
    if pending:
        try:
            pending_args = json.loads(pending.arguments) if pending.arguments else {}
        except Exception:
            pending_args = {}

        missing = json.loads(pending.missing_fields) if pending.missing_fields else []

        # Simple heuristics to extract values from user text for common fields
        def extract_from_text(text: str, field: str):
            text = text.lower()
            if field == "discount_percent":
                m = re.search(r"(\d{1,2})\s*%", text)
                if m:
                    return int(m.group(1))
                m = re.search(r"(\d{1,2})\s*(?:percent|percentage)", text)
                if m:
                    return int(m.group(1))
            if field == "product_id":
                m = re.search(r"(?:id|product)[:#\s]+(\d+)", text)
                if m:
                    return int(m.group(1))
            if field == "quantity":
                m = re.search(r"\b(\d+)\b", text)
                if m:
                    return int(m.group(1))
                words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
                for w, n in words.items():
                    if w in text:
                        return n
            return None

        for f in missing:
            if f not in pending_args:
                val = extract_from_text(request.message, f)
                if val is not None:
                    pending_args[f] = val

        # Validate merged args
        model_cls = TOOL_MODEL_BY_NAME.get(pending.tool_name)
        if model_cls is not None:
            try:
                model_cls(**pending_args)
                # Valid now — remove pending and execute
                db.delete(pending)
                db.commit()

                result: ToolCallResult = run_tool_call(
                    tool_name=pending.tool_name,
                    arguments=pending_args,
                    session_id=session_id,
                    db=db,
                )

                # Persist execution summary
                exec_summary = f"Tool {pending.tool_name} -> {result.status}: {result.message}"
                exec_msg = ChatMessage(session_id=session_id, role="assistant", content=exec_summary)
                db.add(exec_msg)
                db.commit()

                return ChatResponse(
                    user_message=request.message,
                    assistant_message=exec_summary,
                    tool_calls_executed=[ToolCallExecution(
                        tool_name=pending.tool_name,
                        arguments=pending_args,
                        status=result.status,
                        result=result.data or {},
                        message=result.message,
                    )],
                    tool_count=1,
                    status="ok" if result.status == "ok" else "partial",
                )
            except ValidationError as e:
                # Still missing fields — update pending and ask for clarification
                fields = []
                for err in e.errors():
                    loc = err.get("loc", [])
                    if loc:
                        fields.append(str(loc[0]))
                fields = sorted(set(fields))
                pending.arguments = json.dumps(pending_args)
                pending.missing_fields = json.dumps(fields)
                db.add(pending)
                db.commit()

                if fields:
                    field_list = ", ".join(fields)
                    clarify_text = f"I still need: {field_list}. Could you provide them?"
                else:
                    clarify_text = f"I need more information to run '{pending.tool_name}'. Could you clarify?"

                clar_msg = ChatMessage(session_id=session_id, role="assistant", content=clarify_text)
                db.add(clar_msg)
                db.commit()

                return ChatResponse(
                    user_message=request.message,
                    assistant_message=clarify_text,
                    tool_calls_executed=[],
                    tool_count=0,
                    status="partial",
                )

        # If no known model, fall back to normal flow

    # Step 1: Get Groq response + tool calls
    assistant_message, tool_calls = call_groq(
        user_message=request.message,
        session_id=session_id,
    )

    # Persist assistant message (LLM surface text) to DB
    if assistant_message:
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=assistant_message)
        db.add(assistant_msg)
        db.commit()
    
    # Step 2: Execute tool calls via gate layer
    executed_tools: List[ToolCallExecution] = []
    all_ok = True
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        arguments = tool_call["arguments"]

        # Validate arguments against Pydantic model before executing to support clarification
        model_cls = TOOL_MODEL_BY_NAME.get(tool_name)
        if model_cls is not None:
            try:
                # This will raise ValidationError if args are missing/invalid
                model_cls(**arguments)
            except ValidationError as e:
                # Ask user for missing or invalid fields and create a pending tool-call record
                fields = []
                for err in e.errors():
                    loc = err.get("loc", [])
                    if loc:
                        fields.append(str(loc[0]))
                fields = sorted(set(fields))
                if fields:
                    field_list = ", ".join(fields)
                    clarify_text = f"I need the following information to run '{tool_name}': {field_list}. Could you provide them?"
                else:
                    clarify_text = f"I need more information to run '{tool_name}'. Could you clarify?"

                # Persist clarification as assistant message
                clar_msg = ChatMessage(session_id=session_id, role="assistant", content=clarify_text)
                db.add(clar_msg)
                db.commit()

                # Create pending tool-call for resume
                pending = PendingToolCall(
                    session_id=session_id,
                    tool_name=tool_name,
                    arguments=json.dumps(arguments) if arguments else json.dumps({}),
                    missing_fields=json.dumps(fields),
                )
                db.add(pending)
                db.commit()

                return ChatResponse(
                    user_message=request.message,
                    assistant_message=clarify_text,
                    tool_calls_executed=[],
                    tool_count=0,
                    status="partial",
                )

        # Run tool through gate layer
        result: ToolCallResult = run_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            session_id=session_id,
            db=db,
        )
        
        # Track execution
        executed_tools.append(ToolCallExecution(
            tool_name=tool_name,
            arguments=arguments,
            status=result.status,
            result=result.data or {},
            message=result.message,
        ))
        
        if result.status == "rejected":
            all_ok = False

        # Persist tool execution result as assistant/system message
        exec_summary = f"Tool {tool_name} -> {result.status}: {result.message}"
        exec_msg = ChatMessage(session_id=session_id, role="assistant", content=exec_summary)
        db.add(exec_msg)
        db.commit()
    
    # Step 3: Build response
    return ChatResponse(
        user_message=request.message,
        assistant_message=assistant_message,
        tool_calls_executed=executed_tools,
        tool_count=len(executed_tools),
        status="ok" if all_ok else "partial",
    )
