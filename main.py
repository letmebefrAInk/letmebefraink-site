from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI(title="frAInk", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "recent_experiments": EXPERIMENTS[:3],
        },
    )


@app.get("/experiments", response_class=HTMLResponse)
async def experiments(request: Request):
    return templates.TemplateResponse(
        "experiments.html",
        {
            "request": request,
            "experiments": EXPERIMENTS,
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request},
    )


# ---------------------------------------------------------------------------
# Health check — used by Railway/Render
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
