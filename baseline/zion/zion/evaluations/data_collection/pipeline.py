from datetime import datetime, timezone
from typing import Optional

from langsmith import Client as LangSmithClient
from llm_evaluation.test_cases_handler.sync_dataset import SyncLangsmithDataset
from llm_evaluation.test_cases_handler.test_case_classes import (
    LangsmithTestCaseData,
    LangsmithTestMetadata,
)

from zion.config import global_config
from zion.evaluations.data_collection.collectors.hades_collector import HadesCollector
from zion.evaluations.data_collection.collectors.ti_support_collector import (
    TISupportCollector,
)
from zion.evaluations.data_collection.models import (
    EvaluationDataPoint,
    generate_slack_link,
)
from zion.logger import get_logger

logger = get_logger(__name__)

# Slack channel IDs
CHANNEL_IDS = [
    "CB6L7PN5T",
    "C01F6TMGL9L",
    "C0427G128KX",
    "CHSRQRYAH",
    "CAT523W9M",
    "CSL7T4YJV",
    "C48AHCH3Q",
    "C018QDH1Q75",
    "C01QLJJ1NAX",
    "CR762E3EZ",
    "C142W0FGV",
    "CBELS13S4",
    "C303DTK3K",
    "CCKDMK6GJ",
    "C3HUTTRB2",
    "C6A49RX09",
    "C0452CGK8AY",
    "C3FKZTP9N",
    "C4GAPP799",
    "C5K7ZK5P0",
    "C97AVKGDC",
    "C55UDEDN0",
    "C02HBSLNGHE",
    "C7FR6PPS6",
    "C01TVRBC2H3",
    "C4AG71WJW",
    "C018U97DSQZ",
    "C036W0F21RQ",
    "C04B4EG50G2",
    "CUGKR22BB",
    "C78UY0F3K",
    "CQS4A5ZAS",
    "C8XBBU32B",
    "CAB0RUN10",
    "C017EFLJRG9",
    "C03RC9E0M09",
    "C015Y8MS8FN",
    "C543VR9HT",
    "C0278KC380L",
    "C0QQAVC8N",
    "C04JRFZTDHV",
    "C01CFB5LVRN",
    "C02CLHSJ9SQ",
    "C02611CQW13",
    "CLVNH0673",
    "C0120PJ432B",
    "C044D8GSF2T",
    "C7URS9HPT",
    "CDFPFD21Z",
    "CL73RRH29",
    "C450DC4G3",
    "C065G5YAF",
    "CL999U1K3",
    "C017YEJPRD4",
    "C04SXDNR7FA",
    "CHU5ASEUV",
    "C012A4PHF41",
    "CSU8ETTB9",
    "C023XMZ0Y00",
    "C4RTRAJUD",
    "CDJQ0E6EP",
    "C019Z3Y9739",
    "C8BR1EVU6",
    "CCQRPN5FD",
    "C6HJA7GRH",
    "C055QGZ557F",
    "C03UM0WBF60",
    "C051MEW3C68",
    "C03CH14ECT1",
    "C05LZ367NJJ",
    "CTP5JDZ96",
    "C04083RKBDL",
    "C04R05JBM7X",
    "C051KR29CDA",
    "C055YTRC4F3",
    "CP8Q8KPHQ",
    "C04TD69FECE",
    "C04FE6H2NG3",
    "C063N8JUVUZ",
    "C01M7HG21PS",
    "C04UNAU54TZ",
    "C0578FK1X9U",
    "C05KX9S39LK",
    "C0129EFQPM2",
    "C07P169CPNH",
    "C06FKNS2EPR",
    "C056CBMFFQT",
    "C05126Z4Q07",
]

# Staging channel IDs used in 2025
STAGING_CHANNEL_IDS = [
    "C07L8NAHHDM",
    "C07GP6PA7JP",
    "C03RC9E0M09",
    "C08PVAV980M",
    "C08MX9E0A1F",
    "C06T42F1ALD",
    "C08CU36GJJH",
    "C07GDR53KCH",
    "C07J9EWHQBW",
    "C07PE5K1GDC",
    "C05126Z4Q07",
]


def get_channel_ids() -> list[str]:
    if global_config.environment in {"stg", "dev"}:
        return STAGING_CHANNEL_IDS
    return CHANNEL_IDS


# Define custom exceptions
class PipelineConnectionError(RuntimeError):
    """Raised when pipeline fails to validate connections to data sources."""

    ERROR_MSG = "Failed to validate connections to data sources"


class EvaluationDataPipeline:
    """Pipeline for collecting and uploading evaluation data"""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.hades_collector = HadesCollector(config)
        self.ti_collector = TISupportCollector(config)
        logger.info(
            "Initializing LangSmith client",
            extra={
                "endpoint": global_config.langchain_endpoint,
                "api_key_exists": bool(global_config.langchain_api_key),
            },
        )
        self.langsmith_client = LangSmithClient(
            api_key=global_config.langchain_api_key,
            api_url=global_config.langchain_endpoint,
        )
        self.dataset = SyncLangsmithDataset(
            langsmith_client=self.langsmith_client,
            name=config["langsmith"]["dataset_name"],
            description="Evaluation dataset from Hades KB and TI Support",
            repo_test_examples=[],
        )

        logger.info(
            "Pipeline initialized",
            extra={
                "dataset_name": config["langsmith"]["dataset_name"],
                "project_name": config["langsmith"]["project_name"],
                "collectors": ["hades", "ti-support"],
            },
        )

    async def validate_connections(self) -> bool:
        """Validate connections to all data sources"""
        logger.info("Validating connections to data sources")

        hades_valid = await self.hades_collector.validate_connection()
        ti_valid = await self.ti_collector.validate_connection()

        if not hades_valid:
            logger.error("Failed to validate Hades KB connection")
        else:
            logger.info("Hades KB connection validated successfully")

        if not ti_valid:
            logger.error("Failed to validate TI Support connection")
        else:
            logger.info("TI Support connection validated successfully")

        return hades_valid and ti_valid

    async def collect_data(self, last_n_days: int = 1) -> list[EvaluationDataPoint]:
        """Collect data from all sources and merge based on matching thread_ts.

        Args:
            last_n_days: Number of days to look back for TI Support data collection. Defaults to 1.
                        This is used to fetch topics from TI Support.
                        For Hades, uses config parameters (limit, offset, channel_ids).

        Returns:
            list[EvaluationDataPoint]: List of merged data points from both sources.
        """
        # Collect data from both sources
        # Hades uses config parameters (limit, offset, channel_ids)
        # TI Support uses last_n_days
        hades_data = await self.hades_collector.collect_data()
        ti_data = await self.ti_collector.collect_data(last_n_days=last_n_days)

        # Convert to lists of dicts for easier merging
        hades_dicts = [dp.dict() for dp in (hades_data or [])]
        ti_dicts = [dp.dict() for dp in (ti_data or [])]

        def create_merged_data_point(
            ti_point: dict, hades_point: dict, thread_ts_for_url: str
        ) -> EvaluationDataPoint:
            """Helper function to create a merged EvaluationDataPoint."""
            slack_url = (
                generate_slack_link(
                    channel_id=ti_point["channel_id"], thread_ts=thread_ts_for_url
                )
                if thread_ts_for_url
                else None
            )

            return EvaluationDataPoint(
                source="merged",
                input=ti_point["input"],
                expected_output=hades_point["expected_output"],
                main_thread_ts=ti_point["main_thread_ts"],
                channel_id=ti_point["channel_id"],
                channel_name=ti_point.get("channel_name"),
                slack_url=slack_url,
                created_at=ti_point["created_at"],
                updated_at=ti_point.get("updated_at"),
                query_category=ti_point.get("query_category"),
                can_be_answered=ti_point.get("can_be_answered"),
                is_in_hades=ti_point.get("is_in_hades"),
                threaded_message_id=ti_point.get("threaded_message_id"),
            )

        # Merge on main_thread_ts
        merged_data_points = []

        for ti_point in ti_dicts:
            matched = False
            for hades_point in hades_dicts:
                # Primary match: exact thread_ts and channel_id
                if (
                    ti_point["main_thread_ts"] == hades_point["main_thread_ts"]
                    and ti_point["channel_id"] == hades_point["channel_id"]
                ):
                    # Use TI Support's input (query) and Hades' expected_output (chat_summary)
                    merged_point = create_merged_data_point(
                        ti_point, hades_point, ti_point["main_thread_ts"]
                    )
                    merged_data_points.append(merged_point)
                    matched = True
                    break  # For the same channel_id, we only have one thread_ts

            # Fallback match: hades.main_thread_ts with tibot.threaded_message_id (threadedMessageTs)
            if not matched:
                for hades_point in hades_dicts:
                    if (
                        ti_point.get("threaded_message_id")
                        == hades_point["main_thread_ts"]
                        and ti_point["channel_id"] == hades_point["channel_id"]
                    ):
                        merged_point = create_merged_data_point(
                            ti_point, hades_point, hades_point["main_thread_ts"]
                        )
                        merged_data_points.append(merged_point)
                        matched = True
                        break

        logger.info(
            "Collected and merged data points",
            extra={
                "hades_count": len(hades_data) if hades_data else 0,
                "ti_count": len(ti_data) if ti_data else 0,
                "merged_count": len(merged_data_points),
            },
        )

        return merged_data_points

    async def upload_to_langsmith(self, data_points: list[EvaluationDataPoint]) -> None:
        """Upload data points to Langsmith using LLM Kit's classes"""
        logger.info("Starting upload to Langsmith", extra={"count": len(data_points)})

        try:
            # Convert data points to Langsmith examples using LLM Kit's classes
            examples = []
            for point in data_points:
                # Skip data points with channel_id CL73RRH29 (cloud-infra) and query category Query
                if point.channel_id == "CL73RRH29" and point.query_category == "Query":
                    # Skip data points with input containing MR/request/approval related words
                    input_lower = point.input.lower() if point.input else ""
                    skip_words = [
                        "mr",
                        "request",
                        "approval",
                        "merge request",
                        "approve",
                    ]
                    if any(word in input_lower for word in skip_words):
                        continue

                example_dict = point.to_langsmith_example()
                # Convert to LangsmithTestCaseData object
                example = LangsmithTestCaseData(
                    metadata=LangsmithTestMetadata(
                        test_case_name=example_dict["metadata"]["test_case_name"],
                        test_case_description=example_dict["metadata"][
                            "test_case_description"
                        ],
                    ),
                    inputs=example_dict["inputs"],
                    outputs=example_dict["outputs"],
                )
                examples.append(example)

            SyncLangsmithDataset(
                langsmith_client=self.langsmith_client,
                name=self.config["langsmith"]["dataset_name"],
                description="Evaluation dataset from Hades KB and TI Support",
                repo_test_examples=examples,
            )

            logger.info(
                "Successfully uploaded to Langsmith",
                extra={
                    "count": len(examples),
                    "dataset_name": self.config["langsmith"]["dataset_name"],
                    "project_name": self.config["langsmith"]["project_name"],
                },
            )

        except Exception as e:
            logger.exception(
                "Failed to upload to Langsmith",
                extra={"error_type": type(e).__name__, "count": len(data_points)},
            )
            raise

    async def run_pipeline(self) -> None:
        """Run the complete pipeline"""

        def raise_connection_error() -> None:
            """Raise a PipelineConnectionError with a descriptive message."""
            raise PipelineConnectionError(PipelineConnectionError.ERROR_MSG)

        try:
            # Validate connections
            if not await self.validate_connections():
                raise_connection_error()

            # Collect data using last_n_days from config
            data_points = await self.collect_data(
                last_n_days=self.config["ti_support"]["last_n_days"]
            )
            if not data_points:
                logger.warning("No data points collected")
                return

            # Upload to Langsmith
            await self.upload_to_langsmith(data_points)

        except PipelineConnectionError as e:
            logger.exception(
                "Pipeline failed to validate connections", extra={"error_msg": str(e)}
            )
            raise
        except Exception as e:
            logger.exception(
                "Pipeline failed",
                extra={"error_type": type(e).__name__, "error_msg": str(e)},
            )
            raise


async def run_data_collection(
    *,
    dataset_name: Optional[str] = None,
) -> None:
    """
    Data collection pipeline runner.

    Args:
        dataset_name: Uses today's date format
    """

    if dataset_name is None:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        dataset_name = f"auto_evals_data_{today}"

    last_n_days = 1

    config = {
        "hades": {
            "timeout": 30,
            "channel_ids": get_channel_ids(),
        },
        "ti_support": {
            "timeout": 30,
            "last_n_days": last_n_days,
            "topic_collection": {
                "query_categories": "Others,Issue,Query,Informational,Ask a Question",
                "can_be_answered": "Yes",
                "channel_ids": ",".join(get_channel_ids()),
                "is_in_hades": "true",
            },
        },
        "langsmith": {"dataset_name": dataset_name, "project_name": "ti-bot"},
    }

    logger.info(
        "Starting evaluation pipeline",
        extra={
            "dataset_name": dataset_name,
            "last_n_days": last_n_days,
            "note": "Running with hardcoded configuration",
        },
    )

    # Create and run pipeline
    pipeline = EvaluationDataPipeline(config)

    # Validate connections
    if not await pipeline.validate_connections():
        raise PipelineConnectionError(PipelineConnectionError.ERROR_MSG)

    # Collect data
    data_points = await pipeline.collect_data(last_n_days=last_n_days)
    if not data_points:
        error_msg = "No data points collected - unable to create evaluation dataset"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Upload to Langsmith
    await pipeline.upload_to_langsmith(data_points)

    logger.info(
        "Evaluation pipeline completed successfully",
        extra={
            "dataset_name": dataset_name,
            "data_points_count": len(data_points),
            "note": "Data uploaded to LangSmith",
        },
    )
