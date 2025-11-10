import json
import logging
from pathlib import Path
from typing import Iterable, List, Mapping, Any

logger = logging.getLogger(__name__)

def _validate_profiles(profiles: Iterable[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """
    Perform a light sanity-check on profile dictionaries before exporting.

    The goal is not strict validation, just ensuring the top-level keys that
    downstream consumers expect are present.
    """
    required_keys = {
        "username",
        "full_name",
        "biography",
        "external_url",
        "category",
        "follower_count",
        "following_count",
        "is_verified",
        "media_count",
        "profile_pic_url_hd",
        "account_type",
        "location_data",
    }

    validated: List[Mapping[str, Any]] = []
    for idx, profile in enumerate(profiles):
        missing = required_keys.difference(profile.keys())
        if missing:
            logger.warning(
                "Profile at index %d is missing keys: %s. It will still be exported.",
                idx,
                ", ".join(sorted(missing)),
            )
        validated.append(profile)
    return validated

def export_profiles_to_json(
    profiles: Iterable[Mapping[str, Any]],
    output_path: Path,
    pretty: bool = True,
) -> None:
    """
    Serialize a collection of profile dictionaries to JSON.

    :param profiles: Iterable of profile mappings (dict-like).
    :param output_path: Path to the JSON file to be written.
    :param pretty: If True, write indented JSON; otherwise write compact JSON.
    """
    profiles_list = _validate_profiles(profiles)

    try:
        if pretty:
            content = json.dumps(profiles_list, indent=4, ensure_ascii=False)
        else:
            content = json.dumps(profiles_list, separators=(",", ":"), ensure_ascii=False)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(content)

        logger.info(
            "Exported %d profiles to '%s' (pretty=%s).",
            len(profiles_list),
            output_path,
            pretty,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to export profiles to %s: %s", output_path, exc)
        raise