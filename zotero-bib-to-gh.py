from os import environ

import httpx
from logzero import logger


def follow_and_extract(url, headers):
    request = httpx.get(url=url, headers=headers)
    logger.info(f'{url} returned {request.status_code} after {request.elapsed}')
    # If there is s link to next url recursive call
    try:
        next_url = request.links['next'].get('url')
        return request.text + follow_and_extract(next_url, headers)
    # If there is no more link to next url recursion terminates
    except KeyError:
        return request.text


zotero_user_id = environ.get('ZOTERO_USER_ID')
if zotero_user_id is None:
    error = f'ZOTERO_USER_ID not set in GitHub secrets'
    logger.error(error)
    exit(error)
zotero_bearer_token = environ.get('ZOTERO_BEARER_TOKEN')
if zotero_bearer_token is None:
    error = f'ZOTERO_BEARER_TOKEN not set in GitHub secrets'
    logger.error(error)
    exit(error)

zotero_url = f'https://api.zotero.org/users/{zotero_user_id}/items?v=3&format=biblatex'
zotero_headers = {'Authorization': f'Bearer {zotero_bearer_token}'}

with open('bibliography/last-modified-version', 'r') as file:
    cached_version = int(file.readline())
    logger.info(f'last-modified-version is {cached_version}')

zotero_connection = httpx.get(url=zotero_url, headers=zotero_headers)
error = f'{zotero_url} returned {zotero_connection.status_code} after {zotero_connection.elapsed}'
if zotero_connection.status_code != 200:
    logger.error(error)
    exit(error)
logger.info(error)

latest_version = zotero_connection.headers.get('last-modified-version')

if cached_version is latest_version:
    logger.info(f'online version {latest_version} is not different from cache {cached_version}. Done!')
    exit()

logger.info(f'online version {latest_version} is different from cache {cached_version}. Fetching data...')
biblatex_file_content = follow_and_extract(url=zotero_url, headers=zotero_headers)

with open('bibliography/zotero.bib', 'w') as file:
    file.write(biblatex_file_content)
    logger.info('zotero.bib updated')

with open('bibliography/last-modified-version', 'w') as file:
    file.write(str(latest_version))
    logger.info(f'last-modified-version updated to {latest_version}')

logger.info('Done!')
