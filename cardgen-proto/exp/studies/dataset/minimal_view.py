CLASSES = {
    "queries": {"userQuery", "originalQuery", "query"},
    "size": {"size", "suggestSize"},
    "data_candidates": {"candidateDataBindings", "dataBindings"},
    "event_candidates": {
        "candidateEventCandidates",
        "eventCandidates",
        "candidateActions",
        "actionCandidates",
        "actions",
    },
    "asset_candidates": {
        "candidateAssetIds",
        "candidateAssets",
        "assetCandidates",
        "assets",
    },
    "title_description": {"title", "description"},
}
METADATA = {"romVersion", "functionName", "toolName", "skillName"}


def project(view):
    known = set().union(*CLASSES.values())
    projected = {
        category: {key: value for key, value in view.items() if key in keys}
        for category, keys in CLASSES.items()
    }
    metadata = {key: value for key, value in view.items() if key in METADATA}
    unmapped = {
        key: value for key, value in view.items() if key not in known | METADATA
    }
    reconstructed = {
        key: value for category in projected.values() for key, value in category.items()
    }
    if dict(reconstructed, **metadata, **unmapped) != view:
        raise ValueError("unaccounted input content")
    return {
        "six_classes": projected,
        "outer_metadata_excluded_from_minimal": metadata,
        "retained_unmapped": unmapped,
        "status": "needs_schema_review" if unmapped else "six_class_view_prepared",
        "actual_model_input": "raw complete CardSpec; minimal view is audit-only",
    }
