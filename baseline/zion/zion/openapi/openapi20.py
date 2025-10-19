from typing import Any

from zion.openapi.openapi_plugin import IncludeOpenAPIPath


def remove_unused_definitions(
    definitions: dict[str, Any], used_definitions: set
) -> dict[str, Any]:
    """Remove unused definitions from the spec."""
    return {
        definition: value
        for definition, value in definitions.items()
        if definition in used_definitions
    }


def find_used_definitions(docs: dict | list) -> set:
    """Find the used definitions in the docs."""
    used_definitions = set()
    if isinstance(docs, dict):
        for key, value in docs.items():
            if key == "$ref":
                used_definitions.add(value.split("/")[-1])
            elif isinstance(value, dict):
                used_definitions.update(find_used_definitions(value))
            elif isinstance(value, list):
                for item in value:
                    used_definitions.update(find_used_definitions(item))
    elif isinstance(docs, list):
        for item in docs:
            used_definitions.update(find_used_definitions(item))
    return used_definitions


def group_filter_paths_by_path_name(
    filter_paths: list[IncludeOpenAPIPath],
) -> dict[str, dict[str, bool]]:
    """Group the filter paths by the path name."""
    grouped = {}

    for fp in filter_paths:
        if fp.path not in grouped:
            grouped[fp.path] = {}

        grouped[fp.path][fp.method.lower()] = True
    return grouped


def filter_operations_by_path_and_method(
    spec: dict[str, Any], grouped_filter_paths: dict[str, dict[str, bool]]
) -> dict[str, dict[str, Any]]:
    """Filter operations by path and method"""
    filtered = {}
    for path, operations in spec["paths"].items():
        if path not in grouped_filter_paths:
            continue

        filtered[path] = {
            method: operation
            for method, operation in operations.items()
            if method.lower() in grouped_filter_paths[path]
        }
    return filtered


def reduce_openapi_20_spec(
    openapi_spec: dict[str, Any],
    filter_paths: list[IncludeOpenAPIPath],
    ignored_definition_keys: list[str],
) -> dict[str, Any]:
    """Filter only the wanted routes from the OpenAPI spec. Remove the unused definitions."""
    used_definitions = set()

    spec = openapi_spec.copy()
    grouped_filter_paths = group_filter_paths_by_path_name(filter_paths)
    filtered_paths = filter_operations_by_path_and_method(spec, grouped_filter_paths)

    # find all definition used in the filtered_paths
    for operations in filtered_paths.values():
        for operation_name, docs in operations.items():
            if operation_name in ["get", "post", "patch", "put", "delete"]:
                used_definitions.update(find_used_definitions(docs))

    spec_definitions = spec.get("definitions", {})

    # find all nested definitions reference in the used definitions
    for definition, value in spec_definitions.items():
        if definition in used_definitions:
            used_definitions.update(find_used_definitions(value))

    if ignored_definition_keys:
        used_definitions = used_definitions.difference(set(ignored_definition_keys))

    # Remove unused definitions from the spec (The nested ones but not direct used need to be persist)
    if spec_definitions:
        spec["definitions"] = remove_unused_definitions(
            spec["definitions"], used_definitions
        )

    # Update the paths with the filtered and dereferenced paths
    spec["paths"] = filtered_paths

    return spec
