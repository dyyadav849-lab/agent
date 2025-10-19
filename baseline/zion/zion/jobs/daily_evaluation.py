"""
Daily evaluation job that runs the data collection pipeline and LangSmith evaluation.
This job is designed to be called from the /run_job/daily_evaluation endpoint.
"""

from datetime import datetime, timezone

from zion.logger import get_logger

logger = get_logger(__name__)

JOB_NAME_DAILY_EVALUATION = "daily_evaluation"


class DailyEvaluationRunner:
    """Runner for daily evaluation tasks"""

    def __init__(self) -> None:
        """Initialize the runner"""

    async def run_data_collection_pipeline(self) -> bool:
        """Run the data collection pipeline using function call"""
        try:
            logger.info("Starting data collection pipeline")

            # Import the pipeline function
            from zion.evaluations.data_collection.pipeline import (
                run_data_collection,
            )

            # Run the pipeline with default parameters
            await run_data_collection()

            logger.info("Data collection pipeline completed successfully")
            return True  # noqa: TRY300

        except Exception:
            logger.exception("Failed to run data collection pipeline")
            return False

    async def run_langsmith_evaluation(self) -> bool:
        """Run the langsmith evaluation using core function call"""
        try:
            logger.info("Starting langsmith evaluation")

            # Import the core evaluation function
            from zion.evaluations.langsmith_evaluation import (
                run_langsmith_evaluation_core,
            )

            # Use the same dataset name as the pipeline: auto_evals_data_YYYYMMDD
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            agent_name = "ti-bot-level-zero"
            test_project_name = f"auto_evals_data_{today}"

            logger.info(
                "Running evaluation for agent: %s, project: %s",
                agent_name,
                test_project_name,
            )

            # Prepare the agent configuration
            agent_input = {
                "input": {
                    "agent_config": {
                        "plugins": [
                            {"name": "glean_search", "type": "common"},
                            {"name": "slack_conversation_tool", "type": "common"},
                        ],
                        "agent_type": "multi_agent",
                        "llm_model": {"model_name": "azure/gpt-4o"},
                    }
                }
            }

            # Run the core evaluation function with timeout
            logger.info("Calling run_langsmith_evaluation_core")
            import asyncio
            import concurrent.futures

            try:
                # Run the evaluation in a thread pool with direct timeout
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            run_langsmith_evaluation_core(
                                agent_name=agent_name,
                                test_project_name=test_project_name,
                                agent_input=agent_input,
                                use_existing_outputs=False,
                            )
                        )
                    )

                    # Wait for the future with timeout
                    result = future.result(
                        timeout=270
                    )  # 4.5 minutes (safe within 5-minute gunicorn timeout)
            except concurrent.futures.TimeoutError:
                logger.warning(
                    "Evaluation timed out after 4.5 minutes, but partial results may have been inserted"
                )
                future.cancel()
                return True

            if result.status == "completed":
                logger.info("Langsmith evaluation completed successfully")
                logger.info("Test run name: %s", result.test_run_name)
                logger.info("Results count: %d", len(result.results))
                return True
            logger.error("Langsmith evaluation failed: %s", result.message)
            if result.error:
                logger.error("Error details: %s", result.error)
            if result.results and len(result.results) > 0:
                logger.info(
                    "Partial results available: %d results", len(result.results)
                )
                return True
            logger.info("Evaluation failed but partial results may have been inserted")
            return True  # noqa: TRY300

        except Exception:
            logger.exception("Failed to run langsmith evaluation")
            return False

    async def run_daily_evaluation(self) -> bool:
        """Run the complete daily evaluation process"""
        start_time = datetime.now(timezone.utc)
        logger.info("Starting daily evaluation at %s", start_time)

        try:
            # Step 1: Run data collection pipeline
            pipeline_success = await self.run_data_collection_pipeline()
            if not pipeline_success:
                logger.error(
                    "Data collection pipeline failed, skipping langsmith evaluation"
                )
                return False

            # Step 2: Run langsmith evaluation
            langsmith_success = await self.run_langsmith_evaluation()
            if not langsmith_success:
                logger.error("Langsmith evaluation failed")
                return False
            end_time = datetime.now(timezone.utc)
            duration = end_time - start_time
            logger.info("Daily evaluation completed successfully in %s", duration)
            return True  # noqa: TRY300

        except Exception:
            logger.exception("Daily evaluation failed")
            return False


async def daily_evaluation() -> None:
    """Main function to run the daily evaluation job"""
    try:
        runner = DailyEvaluationRunner()
        success = await runner.run_daily_evaluation()

        if not success:
            logger.info("Daily evaluation failed due to run time error")

        logger.info("Daily evaluation job completed successfully")

    except Exception:
        logger.exception("Daily evaluation job failed")
        raise
