from fastapi import Request
from neo4j import Session


def get_session(request: Request) -> Session:
    driver = request.app.state.driver
    with driver.session() as session:
        yield session
