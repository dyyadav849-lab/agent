from typing import Any

from langsmith import Client as LangSmithClient
from langsmith.schemas import Dataset
from pydantic import BaseModel

from zion.agent.zion_agent import ZionAgentInput
from zion.evaluations.custom_evaluator import AgentActionEval


class LangsmithTestMetadata(BaseModel):
    test_case_name: str
    test_case_description: str | None


class LangsmithTestExampleOutputs(BaseModel):
    eval_must_mention: list | None
    eval_structured_response_type: dict[str, str] | None
    eval_structured_response_value: dict[str, Any] | None
    eval_agent_actions: dict[str, AgentActionEval] | None


class LangsmithTestExample(BaseModel):
    metadata: LangsmithTestMetadata
    inputs: ZionAgentInput
    outputs: LangsmithTestExampleOutputs


class LangsmithTestDataset(BaseModel):
    langsmith_client: LangSmithClient
    name: str
    description: str
    dataset: Dataset | None = None
    repo_test_examples: list[LangsmithTestExample]

    class Config:
        arbitrary_types_allowed = True

    def init(self) -> None:
        self.create_dataset_if_not_exists()
        self.sync_dataset_examples()

    def create_dataset_if_not_exists(self) -> None:
        existing_datasets_itr = self.langsmith_client.list_datasets(
            dataset_name=self.name
        )
        existing_datasets = list(existing_datasets_itr)

        if len(existing_datasets) > 0:
            dataset = existing_datasets[0]
        else:
            dataset = self.langsmith_client.create_dataset(
                dataset_name=self.name, description=self.description
            )

        self.dataset = dataset

    def sync_dataset_examples(self) -> None:
        examples_iter = self.langsmith_client.list_examples(dataset_id=self.dataset.id)
        examples = list(examples_iter)
        repo_examples = [tc.dict() for tc in self.repo_test_examples]
        remote_examples = [obj.__dict__ for obj in examples]
        new_examples, removed_examples, outdated_examples, _unchanged_examples = (
            sync_test_cases(repo_examples, remote_examples)
        )

        if len(new_examples) > 0:
            dataset_inputs, dataset_outputs, metadata = zip(
                *[(tc["inputs"], tc["outputs"], tc["metadata"]) for tc in new_examples]
            )

            if new_examples:
                self.langsmith_client.create_examples(
                    inputs=dataset_inputs,
                    outputs=dataset_outputs,
                    dataset_id=self.dataset.id,
                    metadata=metadata,
                )

        for outdated_example in outdated_examples:
            self.langsmith_client.update_example(
                example_id=outdated_example["id"],
                inputs=outdated_example["inputs"],
                outputs=outdated_example["outputs"],
                metadata=outdated_example["metadata"],
                dataset_id=self.dataset.id,
            )

        for removed_example in removed_examples:
            self.langsmith_client.delete_example(removed_example["id"])


def sync_test_cases(
    list_a: list[dict], list_b: list[dict]
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    dict_a = {obj["metadata"]["test_case_name"]: obj for obj in list_a}
    dict_b = {obj["metadata"]["test_case_name"]: obj for obj in list_b}

    items_to_add = []
    items_to_delete = []
    items_to_update = []
    items_unchanged = []

    for test_case_name, obj_a in dict_a.items():
        if test_case_name not in dict_b:
            items_to_add.append(obj_a)
        elif (
            obj_a["inputs"] == dict_b[test_case_name]["inputs"]
            and obj_a["outputs"] == dict_b[test_case_name]["outputs"]
        ):
            items_unchanged.append(dict_b[test_case_name])
        else:
            dict_b[test_case_name]["inputs"] = obj_a["inputs"]
            dict_b[test_case_name]["outputs"] = obj_a["outputs"]
            dict_b[test_case_name]["metadata"] = obj_a["metadata"]
            items_to_update.append(dict_b[test_case_name])

    for test_case_name, obj_b in dict_b.items():
        if test_case_name not in dict_a:
            items_to_delete.append(obj_b)

    return items_to_add, items_to_delete, items_to_update, items_unchanged
