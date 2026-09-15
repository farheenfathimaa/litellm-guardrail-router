from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from app.config import PRICING, PROVIDERS, aws_credentials_present
from app.guardrails import check_input, check_output, get_events
from app.router import RoutingError, route_request
from app.usage import tracker

app = FastAPI(
    title="LiteLLM Guardrail Router",
    version="1.0.0",
    description="Multi-provider LLM gateway with guardrails and cost tracking",
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    tokens: dict
    guardrail_flags: List[str] = []


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    messages = [m.model_dump() for m in request.messages]

    block_reason = check_input(messages)
    if block_reason:
        raise HTTPException(status_code=400, detail={"blocked": True, "reason": block_reason})

    try:
        result = route_request(messages, request.max_tokens)
    except RoutingError as exc:
        raise HTTPException(status_code=502, detail={"error": str(exc)})

    provider_name = result["provider"]
    input_tokens = result["input_tokens"]
    output_tokens = result["output_tokens"]

    pricing = PRICING.get(provider_name)
    if pricing:
        cost = (input_tokens * pricing.input_per_token) + (
            output_tokens * pricing.output_per_token
        )
    else:
        cost = 0.0

    tracker.record(provider_name, input_tokens, output_tokens, cost)

    output_flags = check_output(result["content"])

    return ChatResponse(
        content=result["content"],
        provider=provider_name,
        model=result["model"],
        tokens={
            "input": input_tokens,
            "output": output_tokens,
            "total": result["total_tokens"],
            "estimated_cost": round(cost, 6),
        },
        guardrail_flags=output_flags,
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bedrock_available": aws_credentials_present(),
        "providers": [p.name for p in sorted(PROVIDERS, key=lambda p: p.priority)],
    }


@app.get("/usage")
def usage():
    return tracker.get_summary()


@app.get("/guardrail-events")
def guardrail_events():
    return {"events": get_events()}
