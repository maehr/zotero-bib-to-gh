from os import environ

import httpx
from logzero import logger

def follow_and_extract(client, url, headers):
    request = client.get(url=url, headers=headers)
    logger.info(f"{url} returned {request.status_code} after {request.elapsed}")
    # If there is s link to next url recursive call
    try:
        next_url = request.links["next"].get("url")
        return request.text + follow_and_extract(client, next_url, headers)
    # If there is no more link to next url recursion terminates
    except KeyError:
        return request.text


def download_and_write_bib(client, zotero_headers, zotero_url, file_name="zotero.bib"):
    zotero_connection = client.get(url=zotero_url, headers=zotero_headers)
    error = f"{zotero_url} returned {zotero_connection.status_code} after {zotero_connection.elapsed}"
    if zotero_connection.status_code == 403:
            logger.error("Access to library not granted.")
            return
    if zotero_connection.status_code != 200:
        logger.error(error)
        exit(error)
    logger.info(error)
    try:
        with open(f"bibliography/{file_name}-last-modified-version", "r") as file:
            cached_version = int(file.readline())
            logger.info(f"last-modified-version is {cached_version}")
    except:
        cached_version = 0
    latest_version = int(zotero_connection.headers.get("last-modified-version"))

    if cached_version is latest_version:
        logger.info(
            f"online version {latest_version} is not different from cache {cached_version}. Done!"
        )
        return

    logger.info(
        f"online version {latest_version} is different from cache {cached_version}. Fetching data..."
    )
    biblatex_file_content = follow_and_extract(client, url=zotero_url, headers=zotero_headers)

    with open(f"bibliography/{file_name}", "w") as file:
        file.write(biblatex_file_content)
        logger.info(f"{file_name} updated")

    with open(f"bibliography/{file_name}-last-modified-version", "w") as file:
        file.write(str(latest_version))
        logger.info(f"last-modified-version updated to {latest_version}")

timeout = httpx.Timeout(10.0, connect=60.0)
client = httpx.Client(timeout=timeout)

zotero_user_id = environ.get("ZOTERO_USER_ID")
if zotero_user_id is None:
    error = 'ZOTERO_USER_ID not set in GitHub secrets'
    logger.error(error)
    exit(error)

zotero_bearer_token = environ.get("ZOTERO_BEARER_TOKEN")
if zotero_bearer_token is None:
    error = 'ZOTERO_BEARER_TOKEN not set in GitHub secrets'
    logger.error(error)
    exit(error)

zotero_headers = {"Authorization": f"Bearer {zotero_bearer_token}"}
if zotero_user_id is not None:
    zotero_user_url = (
        f"https://api.zotero.org/users/{zotero_user_id}/items?v=3&format=biblatex"
    )
    download_and_write_bib(client, zotero_headers, zotero_user_url)

logger.info("Downloading all groups!")

groups = client.get(
    f"https://api.zotero.org/users/{zotero_user_id}/groups/", headers=zotero_headers
)

for group in groups.json():
    for attribute, value in group.items():
        if attribute == "id":
            zotero_group_url = (
                f"https://api.zotero.org/groups/{value}/items?v=3&format=biblatex"
            )
            download_and_write_bib(client, zotero_headers, zotero_group_url, f"{value}.bib")

logger.info("Done!")
