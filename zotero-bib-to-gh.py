from os import environ
from pathlib import Path
import httpx
from logzero import logger


def fetch_data(client, url, headers, cached_version):
    response = client.get(url=url, headers=headers)
    response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    latest_version = int(response.headers.get("last-modified-version", 0))

    if cached_version >= latest_version:
        logger.info(f"No new updates found for {url}.")
        return None, latest_version

    logger.info(f"Fetching updates from {url}.")
    return response.text, latest_version


def save_file(directory, file_name, content, latest_version):
    directory_path = Path(directory)
    directory_path.mkdir(parents=True, exist_ok=True)

    if content:
        with open(directory_path / file_name, "w") as file:
            file.write(content)
            logger.info(f"{file_name} updated.")

    with open(directory_path / f"{file_name}-last-modified-version", "w") as file:
        file.write(str(latest_version))
        logger.info(f"last-modified-version updated to {latest_version}.")


def get_cached_version(directory, file_name):
    try:
        with open(Path(directory) / f"{file_name}-last-modified-version", "r") as file:
            return int(file.readline())
    except FileNotFoundError:
        return 0


def download_and_write_bib(
    client, headers, base_url, directory, file_name="zotero.bib"
):
    cached_version = get_cached_version(directory, file_name)
    content, latest_version = fetch_data(client, base_url, headers, cached_version)
    save_file(directory, file_name, content, latest_version)


def main():
    timeout = httpx.Timeout(10.0, connect=60.0)

    with httpx.Client(timeout=timeout) as client:
        zotero_user_id = environ.get("ZOTERO_USER_ID", "")
        zotero_bearer_token = environ.get("ZOTERO_BEARER_TOKEN", "")

        if not zotero_user_id or not zotero_bearer_token:
            logger.error("ZOTERO_USER_ID or ZOTERO_BEARER_TOKEN not set.")
            return

        zotero_headers = {"Authorization": f"Bearer {zotero_bearer_token}"}
        zotero_user_url = (
            f"https://api.zotero.org/users/{zotero_user_id}/items?v=3&format=biblatex"
        )

        download_and_write_bib(
            client, zotero_headers, zotero_user_url, "bibliography", "zotero.bib"
        )

        logger.info("Downloading all groups.")
        groups_response = client.get(
            f"https://api.zotero.org/users/{zotero_user_id}/groups/",
            headers=zotero_headers,
        )
        groups_response.raise_for_status()

        for group in groups_response.json():
            group_id = group.get("id")
            zotero_group_url = (
                f"https://api.zotero.org/groups/{group_id}/items?v=3&format=biblatex"
            )
            download_and_write_bib(
                client,
                zotero_headers,
                zotero_group_url,
                "bibliography",
                f"group_{group_id}.bib",
            )

        logger.info("Update process completed.")


if __name__ == "__main__":
    main()
