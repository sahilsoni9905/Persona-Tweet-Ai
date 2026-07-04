import logging
import config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.embedding import get_embedding_model
from routes import generate, tweets, style, settings, scheduler, history, browser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

get_embedding_model()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(tweets.router)
app.include_router(style.router)
app.include_router(settings.router)
app.include_router(scheduler.router)
app.include_router(history.router)
app.include_router(browser.router)
