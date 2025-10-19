from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.ext.declarative import declarative_base

AgentExecutionTrailBase = declarative_base()


class QueryAgentPluginRequest(BaseModel):
    channel_name: str
    agent_name: str
    username: str
    plugin_keyword: str = ""


class AgentPlugin(AgentExecutionTrailBase):
    __tablename__ = "agent_plugin"
    id = Column(Integer, primary_key=True, index=True)
    schema_version = Column(String(255), nullable=False)
    name_for_model = Column(String(255), nullable=False)
    name_for_human = Column(String(255), nullable=False)
    description_for_model = Column(String(255), nullable=False)
    description_for_human = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    api = Column(JSON, nullable=False, default={})
    http_plugin_detail = Column(JSON, nullable=False, default={})
    is_moved = Column(Boolean, nullable=False, default=False)
    owner = Column(JSON, nullable=False, default=[])
    orchestrators_plugin = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
