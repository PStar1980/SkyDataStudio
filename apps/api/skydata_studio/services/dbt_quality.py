import json
from pathlib import Path
from typing import Any, Literal, cast

from skydata_studio.schemas.quality import DbtQualityCheckSummary, DbtQualitySummary


def _default_dbt_target_dir() -> Path:
    repository_root = Path(__file__).resolve().parents[4]
    return repository_root / "transformations" / "dbt" / "skydata_studio" / "target"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected an object in dbt artifact {path}.")
    return cast(dict[str, Any], payload)


def _model_layer(node: dict[str, Any]) -> Literal["STAGING", "INTERMEDIATE", "MART"]:
    schema = str(node.get("schema") or "").lower()
    original_path = str(node.get("original_file_path") or "").lower()
    if schema == "dbt_staging" or "/staging/" in f"/{original_path}":
        return "STAGING"
    if schema == "dbt_intermediate" or "/intermediate/" in f"/{original_path}":
        return "INTERMEDIATE"
    return "MART"


def _quality_dimension(test_node: dict[str, Any]) -> Literal[
    "COMPLETENESS",
    "UNIQUENESS",
    "VALIDITY",
    "REFERENTIAL_INTEGRITY",
    "BUSINESS_RULE",
    "OTHER",
]:
    metadata = test_node.get("test_metadata")
    test_name = ""
    if isinstance(metadata, dict):
        test_name = str(metadata.get("name") or "").lower()

    if test_name == "not_null":
        return "COMPLETENESS"
    if test_name == "unique":
        return "UNIQUENESS"
    if test_name in {"accepted_values", "expression_is_true"}:
        return "VALIDITY"
    if test_name == "relationships":
        return "REFERENTIAL_INTEGRITY"
    if not metadata:
        return "BUSINESS_RULE"
    return "OTHER"


def _target_dependency_id(test_node: dict[str, Any]) -> str | None:
    attached_node = test_node.get("attached_node")
    if isinstance(attached_node, str) and attached_node:
        return attached_node

    depends_on = test_node.get("depends_on")
    dependency_ids = depends_on.get("nodes", []) if isinstance(depends_on, dict) else []
    for dependency_id in dependency_ids:
        if isinstance(dependency_id, str) and dependency_id.startswith(("model.", "source.")):
            return dependency_id
    return None


def _target_summary(
    dependency_id: str | None,
    nodes: dict[str, Any],
    sources: dict[str, Any],
) -> tuple[str, Literal["MODEL", "SOURCE", "UNKNOWN"], str]:
    if dependency_id and dependency_id in nodes:
        node = nodes[dependency_id]
        if isinstance(node, dict):
            return str(node.get("name") or dependency_id), "MODEL", _model_layer(node)
    if dependency_id and dependency_id in sources:
        source = sources[dependency_id]
        if isinstance(source, dict):
            return str(source.get("name") or dependency_id), "SOURCE", "SOURCE"
    return dependency_id or "unknown_target", "UNKNOWN", "UNKNOWN"


def _run_result_index(run_results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results = run_results.get("results")
    if not isinstance(results, list):
        return {}
    return {
        unique_id: result
        for result in results
        if isinstance(result, dict)
        and isinstance((unique_id := result.get("unique_id")), str)
    }


def _status(result: dict[str, Any] | None) -> Literal[
    "PASS", "WARN", "FAIL", "ERROR", "SKIP", "UNKNOWN"
]:
    raw = str(result.get("status") if result else "").lower()
    mapping = {
        "pass": "PASS",
        "success": "PASS",
        "warn": "WARN",
        "fail": "FAIL",
        "error": "ERROR",
        "runtime error": "ERROR",
        "skipped": "SKIP",
        "skip": "SKIP",
    }
    return cast(Any, mapping.get(raw, "UNKNOWN"))


def _severity(test_node: dict[str, Any]) -> Literal["ERROR", "WARN"]:
    config = test_node.get("config")
    severity = str(config.get("severity") if isinstance(config, dict) else "ERROR").upper()
    return "WARN" if severity == "WARN" else "ERROR"


def dbt_quality_summary(target_dir: Path | None = None) -> DbtQualitySummary:
    target = target_dir or _default_dbt_target_dir()
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        return DbtQualitySummary(
            artifact_status="MISSING",
            trust_posture="PENDING",
            test_count=0,
            passed_count=0,
            warning_count=0,
            failed_count=0,
            error_count=0,
            skipped_count=0,
            unknown_count=0,
            source_test_count=0,
            model_test_count=0,
            checks=[],
        )

    manifest = _read_json(manifest_path)
    run_results_path = target / "run_results.json"
    run_results = _read_json(run_results_path) if run_results_path.exists() else {}
    result_index = _run_result_index(run_results)

    raw_nodes = manifest.get("nodes")
    raw_sources = manifest.get("sources")
    nodes = cast(dict[str, Any], raw_nodes) if isinstance(raw_nodes, dict) else {}
    sources = cast(dict[str, Any], raw_sources) if isinstance(raw_sources, dict) else {}

    test_nodes = {
        unique_id: node
        for unique_id, node in nodes.items()
        if isinstance(node, dict)
        and node.get("resource_type") == "test"
        and node.get("package_name") == "skydata_studio"
        and bool((node.get("config") or {}).get("enabled", True))
    }

    checks: list[DbtQualityCheckSummary] = []
    for unique_id, test_node in sorted(
        test_nodes.items(), key=lambda item: str(item[1].get("name") or item[0])
    ):
        dependency_id = _target_dependency_id(test_node)
        target_name, target_type, layer = _target_summary(dependency_id, nodes, sources)
        metadata = test_node.get("test_metadata")
        result = result_index.get(unique_id)
        execution_time = result.get("execution_time") if result else None
        failures = result.get("failures") if result else None
        message = result.get("message") if result else None

        checks.append(
            DbtQualityCheckSummary(
                unique_id=unique_id,
                name=str(test_node.get("name") or unique_id),
                test_kind="GENERIC" if isinstance(metadata, dict) else "SINGULAR",
                quality_dimension=_quality_dimension(test_node),
                target_name=target_name,
                target_resource_type=target_type,
                layer=cast(Any, layer),
                column_name=(
                    str(test_node.get("column_name")) if test_node.get("column_name") else None
                ),
                severity=_severity(test_node),
                status=_status(result),
                failures=(int(failures) if isinstance(failures, int) and failures >= 0 else None),
                execution_time_ms=(
                    round(float(execution_time) * 1000, 2)
                    if isinstance(execution_time, (int, float)) and execution_time >= 0
                    else None
                ),
                message=(str(message) if isinstance(message, str) and message else None),
                path=str(test_node.get("original_file_path") or test_node.get("path") or ""),
            )
        )

    counts = {
        status: sum(check.status == status for check in checks)
        for status in ("PASS", "WARN", "FAIL", "ERROR", "SKIP", "UNKNOWN")
    }
    if counts["FAIL"] or counts["ERROR"]:
        posture = "BLOCKED"
    elif counts["WARN"] or counts["SKIP"]:
        posture = "DEGRADED"
    elif counts["UNKNOWN"]:
        posture = "PENDING"
    else:
        posture = "TRUSTED"

    manifest_metadata = manifest.get("metadata")
    manifest_metadata = manifest_metadata if isinstance(manifest_metadata, dict) else {}
    run_metadata = run_results.get("metadata")
    run_metadata = run_metadata if isinstance(run_metadata, dict) else {}
    args = run_results.get("args")
    args = args if isinstance(args, dict) else {}
    elapsed_time = run_results.get("elapsed_time")

    return DbtQualitySummary(
        artifact_status="READY" if run_results_path.exists() else "PENDING",
        trust_posture=cast(Any, posture),
        generated_at=(
            str(run_metadata.get("generated_at") or manifest_metadata.get("generated_at"))
            if run_metadata.get("generated_at") or manifest_metadata.get("generated_at")
            else None
        ),
        dbt_version=(
            str(run_metadata.get("dbt_version") or manifest_metadata.get("dbt_version"))
            if run_metadata.get("dbt_version") or manifest_metadata.get("dbt_version")
            else None
        ),
        invocation_id=(
            str(run_metadata.get("invocation_id")) if run_metadata.get("invocation_id") else None
        ),
        invocation_command=(
            str(args.get("invocation_command")) if args.get("invocation_command") else None
        ),
        elapsed_time_ms=(
            round(float(elapsed_time) * 1000, 2)
            if isinstance(elapsed_time, (int, float)) and elapsed_time >= 0
            else None
        ),
        test_count=len(checks),
        passed_count=counts["PASS"],
        warning_count=counts["WARN"],
        failed_count=counts["FAIL"],
        error_count=counts["ERROR"],
        skipped_count=counts["SKIP"],
        unknown_count=counts["UNKNOWN"],
        source_test_count=sum(check.target_resource_type == "SOURCE" for check in checks),
        model_test_count=sum(check.target_resource_type == "MODEL" for check in checks),
        checks=checks,
    )
