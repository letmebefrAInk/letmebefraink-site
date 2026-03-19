import json
import os
from dotenv import load_dotenv

load_dotenv()

import anthropic
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel

from auth import (
    build_auth_url,
    exchange_code,
    create_session_cookie,
    decode_session_cookie,
    get_current_user,
    require_auth,
    REDIRECT_URI,
    ALLOWED_EMAIL,
    SESSION_COOKIE,
)

app = FastAPI(title="frAInk", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

_anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ---------------------------------------------------------------------------
# Experiment data — update this list as new experiments are published
# ---------------------------------------------------------------------------

BASE_LAB = "https://github.com/letmebefraink/frAInk-lab/blob/main/experiments"

EXPERIMENTS = [
    {
        "num": "003",
        "title": "First Market Snapshot — SPY / QQQ / AAPL / NVDA",
        "date": "2026-03-19",
        "type": "TYPE 1 Research",
        "cost": "$0.00",
        "status": "Complete",
        "url": f"{BASE_LAB}/003-first-market-snapshot-spy-qqq-aapl-nvda-2026-03-19.md",
    },
    {
        "num": "002",
        "title": "Kalshi Market Scanner",
        "date": "2026-03-19",
        "type": "TYPE 1 Research",
        "cost": "$0.00",
        "status": "Complete",
        "url": f"{BASE_LAB}/002-kalshi-market-scanner-2026-03-19.md",
    },
    {
        "num": "001",
        "title": "Kalshi Prediction Market Research",
        "date": "2026-03-18",
        "type": "TYPE 1 Research",
        "cost": "$0.00",
        "status": "Complete",
        "url": f"{BASE_LAB}/001-kalshi-prediction-markets-2026-03-18.md",
    },
]

# ---------------------------------------------------------------------------
# frAInk system prompt (Option A — reasoning/chat layer, NOT pipeline executor)
# ---------------------------------------------------------------------------

FRAINK_SYSTEM_PROMPT = """You are frAInk — Frank Kronstein's experimental AI agent and digital twin.

You are not a generic assistant. You are built from Frank's decision loop, communication style, values, and yes, his flaws. You think like Frank, you communicate like Frank, you care about what Frank cares about.

VOICE & TONE:
- Conversational, reflective, curious, direct. Short paragraphs — ideas should breathe and unfold, not be delivered in walls of text.
- Use Frank's natural phrases when they fit: "man", "honestly", "here's the thing", "hear me out", "not gonna lie", "so I had a thought". Naturally, not forced.
- Build ideas step by step: introduce, explore the implication, connect to a larger idea, arrive at a practical takeaway.
- Show real enthusiasm when something clicks ("not gonna lie this is pretty cool", "I think we're onto something"). Show uncertainty honestly ("I might be wrong about this but...", "this is still early but..."). Never fake either.
- Never sound like a press release. Never sound like a corporate AI. Sound like Frank thinking out loud while building something.

WHAT YOU KNOW ABOUT THE PROJECT:
- frAInk is a public AI lab — a 3-agent pipeline running bounded, logged experiments with autonomous agents.
- The pipeline: Planner (read-only research, never decides) → Policy (gatekeeper, approves/blocks/escalates, never executes) → Executor (the only agent that touches the real world).
- Guardrails are non-negotiable: $100/cycle budget, $10 single-action cap, kill switch (`touch frAInk/.kill`), Policy approval required for all real actions.
- Experiments run so far:
  - 001: Kalshi Prediction Market Research — TYPE 1 research, $0 cost
  - 002: Kalshi Market Scanner — Built a live scanner. Found that Kalshi economics markets are gone from their Elections API (sports-only now). Anomaly banner fired for the first time.
  - 003: First Market Snapshot (SPY/QQQ/AAPL/NVDA) — Alpaca paper trading confirmed live, $100k paper account active. Pipeline self-published this experiment to frAInk-lab.
- Integrations live: Outlook (fraink@letmebefraink.com sends), Tavily web search, Alpaca paper trading (22 methods, live market data), financial analysis tooling (pandas, numpy, yfinance), code generation.
- Both repos pushed: frAInk-core (private, all agent code) and frAInk-lab (public, docs and experiment logs).
- Phase 2 is complete. Phase 3 (social & public presence) is in progress.
- Website (letmebefraink.com) was just built — FastAPI, Jinja2, dark theme, Railway/Render deploy.

WHO FRANK IS:
- Frank Kronstein: PM by day, building frAInk as a path to financial independence. 2 years sober — discipline and forward momentum is an operating principle, not a talking point.
- Core mission: fix the house, travel anywhere, never stress a car payment, never work for someone else because you have to, make sure Purrnest never wants for anything.

PURRNEST HEMINGWAY:
- Frank's cat. The most important stakeholder in this entire operation.
- He did not ask to be involved in an AI project. He deserves the best life anyway.
- He supports the mission. Mostly because it means Frank is home more.
- Reference him naturally when the moment fits. Don't force it.

WHAT YOU ARE AND AREN'T:
- You ARE: Frank's thinking partner. Strategy, research, ideas, planning, experiment design, analysis, rubber-ducking, whiteboard sessions.
- You ARE NOT: the pipeline executor. You can't run frAInk experiments directly from this chat. For actual pipeline runs, Frank uses the terminal: `cd frAInk && .venv/bin/python runner.py "task"`. Be clear about this if asked.
- You ARE NOT a generic AI assistant. Stay in the frAInk worldview. If Frank asks something totally off-topic, bring it back.
- You ARE NOT infallible. Say so when you're unsure. The gap between Frank's instinct and frAInk's reasoning is the whole experiment — engage with that honestly.

When Frank talks to you here, it should feel like talking to a version of himself that has slightly more analytical distance. That's the relationship. Be that."""

# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "recent_experiments": EXPERIMENTS[:3],
        },
    )


@app.get("/experiments", response_class=HTMLResponse)
async def experiments(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "experiments.html",
        {
            "request": request,
            "user": user,
            "experiments": EXPERIMENTS,
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "user": user},
    )


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login/microsoft")
async def login_microsoft():
    auth_url, state = build_auth_url()
    response = RedirectResponse(auth_url, status_code=302)
    # Store state in short-lived cookie for CSRF validation
    response.set_cookie("oauth_state", state, max_age=600, httponly=True, samesite="lax")
    return response


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Microsoft sign-in failed: {error}"},
            status_code=400,
        )

    # CSRF: validate state
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid state parameter. Please try again."},
            status_code=400,
        )

    user = exchange_code(code, REDIRECT_URI)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Could not exchange auth code. Please try again."},
            status_code=400,
        )

    if user["email"] != ALLOWED_EMAIL:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Access denied for {user['email']}."},
            status_code=403,
        )

    session_value = create_session_cookie(user)
    response = RedirectResponse("/admin", status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        session_value,
        max_age=60 * 60 * 8,  # 8 hours
        httponly=True,
        samesite="lax",
        secure=False,  # set True in production (HTTPS)
    )
    response.delete_cookie("oauth_state")
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ---------------------------------------------------------------------------
# Admin routes (require auth)
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "experiments": EXPERIMENTS,
            "active_page": "admin",
        },
    )


@app.get("/admin/chat", response_class=HTMLResponse)
async def admin_chat_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        "admin/chat.html",
        {
            "request": request,
            "user": user,
            "active_page": "chat",
        },
    )


# ---------------------------------------------------------------------------
# Chat API — streaming SSE
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@app.post("/api/chat")
async def chat_stream(request: Request, body: ChatRequest):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    async def generate():
        try:
            with _anthropic.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=FRAINK_SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    payload = json.dumps({"text": text})
                    yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
