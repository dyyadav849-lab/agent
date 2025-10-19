from sqlalchemy import JSON, Column, DateTime, Integer, String, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import select

from zion.data.connection import get_session

AgentExecutionTrailBase = declarative_base()


class AgentExecutionTrail(AgentExecutionTrailBase):
    __tablename__ = "agent_execution_trail"
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(255), nullable=False)
    langsmith_run_id = Column(String(255), nullable=False)
    langsmith_project_name = Column(String(255), nullable=False)
    agent_actions = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


def create_trail(
    agent_name: str,
    langsmith_run_id: str,
    langsmith_project_name: str | None = "",
    agent_actions: list | None = None,
) -> AgentExecutionTrail:
    if agent_actions is None:
        agent_actions = []

    with get_session() as db:
        db_trail = AgentExecutionTrail(
            agent_name=agent_name,
            langsmith_run_id=langsmith_run_id,
            langsmith_project_name=langsmith_project_name,
            agent_actions=agent_actions,
        )
        db.add(db_trail)
        db.commit()
        db.refresh(db_trail)
        return db_trail


def get_trail(trail_id: int) -> AgentExecutionTrail | None:
    """Get audit by record id."""
    with get_session() as db:
        db_trail = db.execute(
            select(AgentExecutionTrail).where(AgentExecutionTrail.id == trail_id)
        ).first()
        if db_trail is None:
            message = f"Audit with id {trail_id} not found"
            raise ValueError(message)
        return db_trail[0]


def get_trails_by_agent_name(
    agent_name: str, page: int, page_size: int
) -> tuple[bool, list[AgentExecutionTrail]]:
    """Get all audits for a given agent_name. Paginated."""
    with get_session() as db:
        query = db.query(AgentExecutionTrail).filter(
            AgentExecutionTrail.agent_name == agent_name
        )
        total = query.count()
        db_trails = query.offset(page * page_size).limit(page_size).all()
        has_more = (page + 1) * page_size < total
        return db_trails, has_more
