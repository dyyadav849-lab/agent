from typing import Any

from zion.openapi.openapi_plugin import IncludeOpenAPIPath


def remove_unused_schemas(schemas: dict[str, Any], used_schemas: set) -> dict[str, Any]:
    """Remove unused definitions from the spec."""
    return {
        definition: value
        for definition, value in schemas.items()
        if definition in used_schemas
    }


def find_used_schemas(docs: dict | list) -> set:
    """Find the used definitions in the docs."""
    used_schemas = set()
    if isinstance(docs, dict):
        for key, value in docs.items():
            if key == "$ref":
                used_schemas.add(value.split("/")[-1])
            elif isinstance(value, dict):
                used_schemas.update(find_used_schemas(value))
            elif isinstance(value, list):
                for item in value:
                    used_schemas.update(find_used_schemas(item))
    elif isinstance(docs, list):
        for item in docs:
            used_schemas.update(find_used_schemas(item))
    return used_schemas


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


def reduce_openapi_3x_spec(
    openapi_spec: dict[str, Any],
    filter_paths: list[IncludeOpenAPIPath],
    ignored_definition_keys: list[str],
) -> dict[str, Any]:
    """Filter only the wanted routes from the OpenAPI spec. Remove the unused definitions."""
    used_schemas = set()

    spec = openapi_spec.copy()
    grouped_filter_paths = group_filter_paths_by_path_name(filter_paths)
    filtered_paths = filter_operations_by_path_and_method(spec, grouped_filter_paths)

    # find all definition used in the filtered_paths
    for operations in filtered_paths.values():
        for operation_name, docs in operations.items():
            if operation_name in ["get", "post", "patch", "put", "delete"]:
                used_schemas.update(find_used_schemas(docs))

    # find all nested definitions reference in the used definitions
    schemas_spec = spec.get("components", {}).get("schemas", {})
    for definition, value in schemas_spec.items():
        if definition in used_schemas:
            used_schemas.update(find_used_schemas(value))

    if ignored_definition_keys:
        used_schemas = used_schemas.difference(set(ignored_definition_keys))

    # Remove unused definitions from the spec (The nested ones but not direct used need to be persist)
    if schemas_spec:
        reduced_schemas = remove_unused_schemas(
            spec["components"]["schemas"], used_schemas
        )

        # Update the paths with the filtered/dereferenced paths and schemas
        spec["components"]["schemas"] = reduced_schemas

    spec["paths"] = filtered_paths

    # Remove the tags as they are not useful information
    spec.pop("tags", None)

    return spec
