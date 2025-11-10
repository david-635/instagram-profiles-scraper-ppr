import json
import logging
from pathlib import Path
from typing import List, Optional

import typer

from extractors.instagram_parser import InstagramProfileScraper
from outputs.exporters import export_profiles_to_json

app = typer.Typer(help="Instagram Profiles Scraper PPR - scrape public Instagram profiles to JSON.")

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        logging.warning("Config file %s not found. Falling back to built-in defaults.", config_path)
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        if not isinstance(config, dict):
            raise ValueError("Root of config must be an object.")
        return config
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to read config from %s: %s", config_path, exc)
        return {}

def load_usernames(input_file: Path) -> List[str]:
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    usernames: List[str] = []
    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            usernames.append(line)

    if not usernames:
        raise ValueError("No usernames found in input file.")

    return usernames

def create_scraper_from_config(config: dict) -> InstagramProfileScraper:
    request_cfg = config.get("request", {})
    scraper_cfg = config.get("scraper", {})

    user_agent: Optional[str] = request_cfg.get("user_agent")
    timeout: int = int(request_cfg.get("timeout", 10))
    max_retries: int = int(scraper_cfg.get("max_retries", 2))
    retry_backoff: float = float(scraper_cfg.get("retry_backoff", 1.0))

    return InstagramProfileScraper(
        user_agent=user_agent,
        timeout=timeout,
        max_retries=max_retries,
        retry_backoff=retry_backoff,
    )

def default_paths() -> dict:
    """
    Compute sensible default paths relative to this file: