from sqlalchemy import BigInteger, Column, DateTime, Float, String, Text, func, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    agent_name = Column(String(255), nullable=False)
    test_project_name = Column(String(255), nullable=False)
    test_run_name = Column(String(255), nullable=False)
    experiment_name = Column(String(255), nullable=False)
    run_id = Column(String(255), nullable=False)
    run_name = Column(String(255), nullable=False)
    run_type = Column(String(255), nullable=False)
    model_name = Column(String(255), nullable=True)
    channel_name = Column(String(255), nullable=False)
    slack_url = Column(String(512), nullable=True)
    dataset_id = Column(String(255), nullable=False)
    example_id = Column(String(255), nullable=False)
    input_text = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    actual_output = Column(Text)
    tool_score = Column(Float)
    rouge_score = Column(Float)
    llm_judge_score = Column(Float)
    grading_note_score = Column(Float)
    llm_judge_comment = Column(Text)
    grading_note_comment = Column(Text)
    contextual_relevancy_score = Column(Float)
    contextual_relevancy_comment = Column(Text)
    faithfulness_score = Column(Float)
    faithfulness_comment = Column(Text)
    contextual_recall_score = Column(Float)
    contextual_recall_comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<EvaluationResult(agent_name='{self.agent_name}',
        test_project_name='{self.test_project_name}',
        test_run_name='{self.test_run_name}',
        experiment_name='{self.experiment_name}',
        run_id='{self.run_id}',
        run_name='{self.run_name}',
        run_type='{self.run_type}',
        model_name='{self.model_name}',
        channel_name='{self.channel_name}',
        dataset_id='{self.dataset_id}',
        example_id='{self.example_id}')>"""
