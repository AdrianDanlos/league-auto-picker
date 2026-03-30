import time

import requests

from utils.logger import log_and_discord
from utils import get_auth, get_base_url, handle_connection_errors


def _is_status_ok(status_code):
    return status_code in (200, 201, 204)


def _get_current_page():
    current_page_res = requests.get(
        f"{get_base_url()}/lol-perks/v1/currentpage",
        auth=get_auth(),
        verify=False,
    )
    if current_page_res.status_code != 200:
        return None
    return current_page_res.json() or {}


def _page_signature(page):
    if not isinstance(page, dict):
        return None
    return (
        page.get("id"),
        tuple(page.get("selectedPerkIds", []) or []),
        page.get("primaryStyleId"),
        page.get("subStyleId"),
    )


def _is_rune_page_populated(page):
    if not isinstance(page, dict):
        return False
    selected_perks = page.get("selectedPerkIds", []) or []
    # A usable rune page should include at least keystone + minor + stat perks.
    return (
        isinstance(selected_perks, list)
        and len(selected_perks) >= 9
        and page.get("primaryStyleId") is not None
        and page.get("subStyleId") is not None
    )


def _is_target_page_current(target_page_id):
    current_page = _get_current_page()
    if not current_page:
        return False
    return current_page.get("id") == target_page_id


@handle_connection_errors
def select_default_runes():
    try:
        max_attempts = 4
        before_page = _get_current_page()
        before_signature = _page_signature(before_page)
        latest_status = None
        latest_body = ""

        for attempt in range(1, max_attempts + 1):
            response = requests.post(
                f"{get_base_url()}/lol-perks/v1/rune-recommender-auto-select",
                auth=get_auth(),
                verify=False,
            )
            latest_status = response.status_code
            latest_body = response.text
            if not _is_status_ok(response.status_code):
                break

            # Recommender can respond before the page has actually been populated.
            time.sleep(0.6)
            after_page = _get_current_page()
            after_signature = _page_signature(after_page)

            if _is_rune_page_populated(after_page) and (
                after_signature != before_signature or before_signature is None
            ):
                print("✅ Successfully set current rune page to recommended one")
                return True

            if attempt < max_attempts:
                time.sleep(0.4)

        log_and_discord(
            "❌ Failed to set recommended rune page. "
            f"(Status: {latest_status}, Body: {latest_body}) "
            "LCU may acknowledge the request but keep runes empty/unapplied in this champ-select state."
        )
        return False

    except Exception as e:
        log_and_discord(f"❌ Unexpected error setting default runes and summs: {e}")
        return False


@handle_connection_errors
def select_configured_runes(config, champion):
    runes_config = config.get("runes", {})
    if not isinstance(runes_config, dict):
        log_and_discord("⚠️ Invalid 'runes' config. Expected an object.")
        return False

    target_page_name = runes_config.get(champion)
    if not isinstance(target_page_name, str) or not target_page_name.strip():
        return False

    target_page_name_normalized = target_page_name.strip().lower()

    try:
        pages_res = requests.get(
            f"{get_base_url()}/lol-perks/v1/pages",
            auth=get_auth(),
            verify=False,
        )
        if pages_res.status_code != 200:
            log_and_discord(
                f"⚠️ Could not read rune pages for {champion} "
                f"(Status: {pages_res.status_code}, {pages_res.text})"
            )
            return False

        pages_payload = pages_res.json()
        pages = (
            pages_payload.get("pages", [])
            if isinstance(pages_payload, dict)
            else pages_payload
        )
        if not isinstance(pages, list):
            log_and_discord("⚠️ Unexpected rune pages response format from LCU.")
            return False

        target_page = next(
            (
                page
                for page in pages
                if str(page.get("name", "")).strip().lower() == target_page_name_normalized
            ),
            None,
        )
        if not target_page:
            print(
                f"ℹ️ Rune page '{target_page_name}' for {champion} not found. "
                "Falling back to recommended runes."
            )
            return False

        target_page_id = target_page.get("id")
        if target_page_id is None:
            log_and_discord(
                f"⚠️ Rune page '{target_page_name}' has no id. Falling back to recommended runes."
            )
            return False

        current_page_payload = {
            "id": target_page_id,
            "name": target_page.get("name", target_page_name),
            "primaryStyleId": target_page.get("primaryStyleId"),
            "subStyleId": target_page.get("subStyleId"),
            "selectedPerkIds": target_page.get("selectedPerkIds", []),
            "current": True,
        }

        current_page_res = requests.put(
            f"{get_base_url()}/lol-perks/v1/currentpage",
            auth=get_auth(),
            json=current_page_payload,
            verify=False,
        )

        if _is_status_ok(current_page_res.status_code) and _is_target_page_current(
            target_page_id
        ):
            print(
                f"✅ Successfully selected configured rune page "
                f"'{target_page.get('name', target_page_name)}' for {champion}"
            )
            return True

        page_update_res = requests.put(
            f"{get_base_url()}/lol-perks/v1/pages/{target_page_id}",
            auth=get_auth(),
            json={"current": True},
            verify=False,
        )

        if _is_status_ok(page_update_res.status_code) and _is_target_page_current(
            target_page_id
        ):
            print(
                f"✅ Successfully selected configured rune page "
                f"'{target_page.get('name', target_page_name)}' for {champion}"
            )
            return True

        log_and_discord(
            f"⚠️ Failed to apply configured rune page '{target_page_name}' for {champion}. "
            "Falling back to recommended runes. "
            f"Endpoints: currentpage={current_page_res.status_code}, "
            f"page_update={page_update_res.status_code}."
        )
        return False

    except Exception as e:
        log_and_discord(
            f"⚠️ Error selecting configured rune page for {champion}: {e}. "
            "Falling back to recommended runes."
        )
        return False


@handle_connection_errors
def select_summoner_spells(config, champion, assigned_lane):
    # Get champion-specific summoner spells, fallback to Default if not found
    summs_config = config.get("summs", {}).get(assigned_lane, {})
    champion_summs = summs_config.get(champion, summs_config.get("Default", {}))

    try:
        response = requests.patch(
            f"{get_base_url()}/lol-champ-select/v1/session/my-selection",
            auth=get_auth(),
            json=champion_summs,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            print(f"✅ Successfully set the summoner spells:{champion_summs}")
        else:
            log_and_discord(
                f"❌ Failed to set the summoner spells (Status: {response.status_code}, {response.text})"
            )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error setting default runes and summs: {e}")
