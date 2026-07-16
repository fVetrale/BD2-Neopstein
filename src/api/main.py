import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from neo4j import GraphDatabase

from src.api.routers import clusters, mails, persons


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    yield
    app.state.driver.close()


app = FastAPI(lifespan=lifespan)
app.include_router(mails.router)
app.include_router(persons.router)
app.include_router(clusters.router)


@app.get("/health")
def health():
    app.state.driver.verify_connectivity()
    return {"status": "ok"}
