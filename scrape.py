import aiofiles
import aiohttp
import asyncio
from collections import defaultdict
from typing import List
import base64
import time
from dotenv import dotenv_values


config = dotenv_values(".env")


async def make_databricks_api_call(session: aiohttp.ClientSession,
                                   path: str,
                                   api_url: str,
                                   databricks_url: str = config["DATABRICKS_URL"],
                                   token: str = config["DATABRICKS_TOKEN"]):
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{databricks_url}{api_url}", headers=headers, json={"path": path}) as resp:
        if resp.status == 200:
            response = await resp.json()
            return response
        else:
            raise AttributeError(f"Unsuccessful request:\n{resp.status} - {resp.reason}\n{resp.text}")


async def add_notebook_properties_to_results(results: defaultdict,
                                             nb_object: dict):
    results["object_type"].append(nb_object["object_type"])
    results["path"].append(nb_object["path"])
    results["object_id"].append(nb_object["object_id"])
    results["language"].append(nb_object["language"])


async def list_notebooks(session: aiohttp.ClientSession,
                         workspace: str,
                         api_url: str,
                         api_data: defaultdict):
    tasks = []
    recursive_tasks = []

    response = await make_databricks_api_call(session, path=workspace, api_url=api_url)

    if objects := response.get("objects"):
        for object in objects:
            if object["object_type"] == "NOTEBOOK":
                tasks.append(asyncio.ensure_future(add_notebook_properties_to_results(api_data, object)))

            elif object["object_type"] == "DIRECTORY":
                recursive_tasks.append(asyncio.ensure_future(
                    list_notebooks(session,
                                workspace=object["path"],
                                api_url=api_url,
                                api_data=api_data)))
    if recursive_tasks:
        await asyncio.gather(*recursive_tasks)
    if tasks:
        await asyncio.gather(*tasks)
    


async def load_notebook_ids_to_export(session: aiohttp.ClientSession,
                                      workspace: str) -> defaultdict:
    api_url = "/api/2.0/workspace/list"
    api_data = defaultdict(list)
    start_time = time.time()
    await list_notebooks(session, workspace, api_url, api_data)

    with open("all_notebooks.txt", "w") as f:
        f.write('\n'.join([str(id) for id in api_data["object_id"]]))
    
    
    print(f"Found {len(api_data['path'])} notebooks (in {time.time() - start_time} seconds)")
    return api_data


def get_notebook_url_from_id(notebook_id: str,
                             databricks_url: str = config["DATABRICKS_URL"]) -> str:
    return f"{databricks_url}/#notebook/{notebook_id}"


async def add_notebook_contents_to_results(results: list,
                                           content: str,
                                           notebook_id: str,
                                           path: str,
                                           language: str) -> list:
    notebook_content = base64.b64decode(content).decode('utf-8')
    notebook_url = get_notebook_url_from_id(notebook_id)

    results.append({
        "notebook_path": path,
        "notebook_id": notebook_id,
        "notebook_language": language,
        "notebook_url": notebook_url,
        "notebook_content": notebook_content,
    })
    return results


async def export_one_notebook(session: aiohttp.ClientSession,
                              code_blocks: List[dict],
                              path: str,
                              notebook_id: str,
                              language: str):
    api_url = "/api/2.0/workspace/export"
    response = await make_databricks_api_call(session, path, api_url)
    if content := response.get('content'):
        await add_notebook_contents_to_results(code_blocks, content, notebook_id, path, language)
        async with aiofiles.open('finished_notebooks.txt', mode='a') as f:
            await f.write(f"{notebook_id}\n")


async def export_all_notebooks(workspace: str) -> List[dict]:

    # Create or overwrite file
    open("finished_notebooks.txt", "w").close()

    tcp_connection = aiohttp.TCPConnector(limit=18, force_close=True)
    session = aiohttp.ClientSession(connector=tcp_connection)
    notebook_data = await load_notebook_ids_to_export(session, workspace)

    code_blocks = []
    tasks = []

    start_time = time.time()
    for id, language, path in zip(notebook_data["object_id"], notebook_data["language"], notebook_data["path"]):
        tasks.append(export_one_notebook(session, code_blocks, path, id, language))

    await asyncio.gather(*tasks)
    await session.close()

    print(f"Exported {len(code_blocks)} notebooks (in {time.time() - start_time} seconds)")
    return code_blocks
