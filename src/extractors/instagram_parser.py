import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import requests

from .utils_format import build_location_data, clean_text, ensure_int

logger = logging.getLogger(__name__)

@dataclass
class InstagramProfile:
    username: str
    full_name: str
    biography: str
    external_url: Optional[str]
    category: Optional[str]
    follower_count: int
    following_count: int
    is_verified: bool
    media_count: int
    profile_pic_url_hd: Optional[str]
    account_type: int
    location_data: Dict[str, Any]

class InstagramProfileScraper:
    """
    Scrapes public profile information from Instagram's web endpoints.

    The implementation targets the unofficial web_profile_info API used by the
    Instagram web client. It does not require authentication but relies on
    realistic headers and may occasionally break if Instagram changes internals.
    """

    BASE_URL = "https://www.instagram.com/api/v1/users/web_profile_info/"

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 2,
        retry_backoff: float = 1.0,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        if user_agent:
            self.user_agent = user_agent
        else:
            # A generic but commonly accepted desktop user agent.
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/118.0 Safari/537.36"
            )

    def _build_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.instagram.com/",
            "X-IG-App-ID": "936619743392459",  # public web app id used by browser client
        }

    def _request_profile_raw(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Perform the HTTP request to Instagram and return the raw JSON payload.
        Handles retries with simple exponential backoff.
        """
        params = {"username": username}
        headers = self._build_headers()

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):
            try:
                logger.debug(
                    "Requesting profile info for '%s' (attempt %d)", username, attempt
                )
                response = requests.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.debug("Received JSON payload for '%s'", username)
                        return data
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        logger.warning(
                            "Failed to decode JSON for '%s': %s", username, exc
                        )
                else:
                    last_error = RuntimeError(
                        f"Unexpected status code {response.status_code} for username {username}"
                    )
                    logger.warning(
                        "Non-200 response for '%s': %s %s",
                        username,
                        response.status_code,
                        response.text[:200],
                    )
            except requests.RequestException as exc:
                last_error = exc
                logger.warning(
                    "Network error while requesting profile for '%s': %s", username, exc
                )

            if attempt <= self.max_retries:
                sleep_time = self.retry_backoff * attempt
                logger.debug("Retrying in %.2f seconds...", sleep_time)
                time.sleep(sleep_time)

        if last_error:
            logger.error("Giving up on '%s' after retries: %s", username, last_error)
        return None

    @staticmethod
    def _map_to_profile(payload: Dict[str, Any], username: str) -> InstagramProfile:
        """
        Map Instagram's raw JSON shape into our normalized InstagramProfile model.
        This function is defensive against missing fields or format changes.
        """
        user_data = (
            payload.get("data", {}).get("user")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(user_data, dict):
            logger.warning("Payload for '%s' did not contain expected 'data.user' key.", username)
            user_data = {}

        # Followers and following can be found in different shapes depending on endpoint.
        follower_count = ensure_int(
            user_data.get("edge_followed_by", {}).get("count")
        )
        following_count = ensure_int(
            user_data.get("edge_follow", {}).get("count")
        )

        media_count = ensure_int(
            user_data.get("edge_owner_to_timeline_media", {}).get("count")
        )

        # Account type is often represented as an integer, but not always.
        raw_account_type = user_data.get("account_type")
        account_type = ensure_int(raw_account_type)

        profile = InstagramProfile(
            username=user_data.get("username") or username,
            full_name=clean_text(user_data.get("full_name", "")),
            biography=clean_text(user_data.get("biography", "")),
            external_url=clean_text(user_data.get("external_url", "") or None),
            category=clean_text(user_data.get("category_name", "") or None),
            follower_count=follower_count,
            following_count=following_count,
            is_verified=bool(user_data.get("is_verified", False)),
            media_count=media_count,
            profile_pic_url_hd=user_data.get("profile_pic_url_hd"),
            account_type=account_type,
            location_data=build_location_data(
                city_name=user_data.get("city_name"),
                latitude=user_data.get("latitude"),
                longitude=user_data.get("longitude"),
            ),
        )
        return profile

    def fetch(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Public API used by the runner. Returns a dict that is ready for JSON
        serialization, or None if the profile could not be scraped.
        """
        username = username.strip().lstrip("@")
        if not username:
            logger.warning("Empty username provided to fetch().")
            return None

        raw = self._request_profile_raw(username)
        if raw is None:
            # Graceful fallback: provide a minimal but structurally valid object.
            logger.info(
                "Falling back to minimal profile structure for '%s' due to fetch failure.",
                username,
            )
            fallback = InstagramProfile(
                username=username,
                full_name="",
                biography="",
                external_url=None,
                category=None,
                follower_count=0,
                following_count=0,
                is_verified=False,
                media_count=0,
                profile_pic_url_hd=None,
                account_type=0,
                location_data=build_location_data(None, None, None),
            )
            return asdict(fallback)

        profile = self._map_to_profile(raw, username)
        return asdict(profile)