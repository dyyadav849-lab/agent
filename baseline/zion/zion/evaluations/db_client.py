from typing import Callable

from sqlalchemy.orm import Session

from zion.evaluations.models import EvaluationResult
from zion.util.log.logger import Logger


class EvaluationDbError(Exception):
    """Custom exception for evaluation database operations."""


class EvaluationDbClient:
    def __init__(self, db_session: Callable[..., Session]) -> None:
        self.__db_session = db_session
        self.__logger = Logger(name=self.__class__.__name__)

    def insert_evaluation_result(
        self, evaluation_result: EvaluationResult
    ) -> EvaluationResult:
        """
        Method to insert evaluation result data.
        """
        try:
            with self.__db_session() as session:
                session.add(evaluation_result)
                session.commit()
                session.refresh(evaluation_result)
                return evaluation_result
        except Exception as e:
            description = "Insert evaluation result data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise EvaluationDbError(log_message) from e

    def insert_evaluation_results_batch(
        self, evaluation_results: list[EvaluationResult]
    ) -> list[EvaluationResult]:
        """
        Method to insert multiple evaluation results in a single transaction.
        This prevents data loss by committing results in batches.
        """
        try:
            with self.__db_session() as session:
                session.add_all(evaluation_results)
                session.commit()

                # Refresh all results to get their IDs
                for result in evaluation_results:
                    session.refresh(result)

                self.__logger.info(
                    "Successfully inserted batch of %d evaluation results",
                    len(evaluation_results),
                )
                return evaluation_results
        except Exception as e:
            description = "Insert evaluation results batch failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise EvaluationDbError(log_message) from e
