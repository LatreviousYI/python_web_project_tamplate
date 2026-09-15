import configs
from utils import httpx_utils, log_util, response_utils

from fastapi import status


async def get_group_repositories(token, page=1, perpage=20):
    """
    获取代码组内的仓库列表
    response.header中有个参数x-total 是仓库总数量
    [
        {
            "accessLevel": 30,
            "archived": false,
            "createdAt": "2024-04-15T15:28:49+08:00",
            "creatorId": 1119475,
            "creatorUid": "64743b3968eb1baac2f20886",
            "demoProject": false,
            "encrypted": false,
            "httpUrlToRepo": "https://codeup.aliyun.com/5f278b52d248146039338d7b/ai/auto-recruit.git",
            "id": 4282444,
            "lastActivityAt": "2026-09-14T16:02:28+08:00",
            "name": "auto-recruit",
            "nameWithNamespace": "5f278b52d248146039338d7b / ai / auto-recruit",
            "namespaceId": 1221832,
            "path": "auto-recruit",
            "pathWithNamespace": "5f278b52d248146039338d7b/ai/auto-recruit",
            "repositorySize": "849.966",
            "repositoryTags": [],
            "sshUrlToRepo": "git@codeup.aliyun.com:5f278b52d248146039338d7b/ai/auto-recruit.git",
            "starCount": 0,
            "starred": false,
            "updatedAt": "2026-09-13T01:02:25+08:00",
            "visibility": "private",
            "webUrl": "https://codeup.aliyun.com/5f278b52d248146039338d7b/ai/auto-recruit"
        },
        {
            "accessLevel": 30,
            "archived": false,
            "createdAt": "2026-05-29T12:03:23+08:00",
            "creatorId": 1347242,
            "creatorUid": "6638865cf5d9fd66482f54e5",
            "demoProject": false,
            "encrypted": false,
            "httpUrlToRepo": "https://codeup.aliyun.com/5f278b52d248146039338d7b/ai/ssc_intelli_engine.git",
            "id": 6907703,
            "lastActivityAt": "2026-09-14T11:24:34+08:00",
            "name": "ssc_intelli_engine",
            "nameWithNamespace": "5f278b52d248146039338d7b / ai / ssc_intelli_engine",
            "namespaceId": 1221832,
            "path": "ssc_intelli_engine",
            "pathWithNamespace": "5f278b52d248146039338d7b/ai/ssc_intelli_engine",
            "repositorySize": "3.27734",
            "repositoryTags": [],
            "sshUrlToRepo": "git@codeup.aliyun.com:5f278b52d248146039338d7b/ai/ssc_intelli_engine.git",
            "starCount": 0,
            "starred": false,
            "updatedAt": "2026-09-09T12:41:03+08:00",
            "visibility": "private",
            "webUrl": "https://codeup.aliyun.com/5f278b52d248146039338d7b/ai/ssc_intelli_engine"
        }
    ]
    """
    url = f"{configs.settings.ali_yunxiao}/oapi/v1/codeup/organizations/5f278b52d248146039338d7b/groups/2090025/repositories"
    headers = {"x-yunxiao-token": token}
    response = await httpx_utils.httpx_client.get(url, headers=headers, params={"page": page, "perpage": perpage})
    if response.status_code != status.HTTP_200_OK:
        log_util.logger.error(f"获取代码组内仓库失败 {response.text}")
        response_utils.server_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "获取代码组内仓库失败")
    return response


async def get_group_repositories_detail(token, repositories_id):
    """
    获取代码组内的仓库详情
    {
        "accessLevel": "30",
        "allowPush": false,
        "archived": false,
        "cloneDownloadControlGray": true,
        "createdAt": "2025-11-06T10:57:02+08:00",
        "creatorId": 1235264,
        "defaultBranch": "master",
        "demoProject": false,
        "enableCloneDownloadControl": true,
        "forkCount": 0,
        "httpUrlToRepo": "https://codeup.aliyun.com/5f278b52d248146039338d7b/ai/FastOneTouch.git",
        "id": 5940858,
        "lastActivityAt": "2026-09-09T15:29:59+08:00",
        "mergeRequestsEnabled": true,
        "name": "OneTouch",
        "nameWithNamespace": "5f278b52d248146039338d7b / ai / OneTouch",
        "namespace": {
            "createdAt": "2023-08-18T18:02:39+08:00",
            "description": "ai小组用",
            "id": 1221832,
            "name": "ai",
            "ownerId": 1119475,
            "path": "ai",
            "updatedAt": "2023-08-18T18:02:39+08:00",
            "visibility": "private"
        },
        "openCloneDownloadControl": false,
        "owner": {
            "id": 1235264,
            "webUrl": ""
        },
        "path": "FastOneTouch",
        "pathWithNamespace": "5f278b52d248146039338d7b/ai/FastOneTouch",
        "permissions": {
            "groupAccess": null,
            "projectAccess": null
        },
        "projectType": 1,
        "repositorySize": "3.18945",
        "repositoryTags": [],
        "sshUrlToRepo": "git@codeup.aliyun.com:5f278b52d248146039338d7b/ai/FastOneTouch.git",
        "starCount": 1,
        "tagList": [],
        "updatedAt": "2026-09-09T15:29:59+08:00",
        "visibility": "private",
        "webUrl": "https://codeup.aliyun.com/5f278b52d248146039338d7b/ai/FastOneTouch",
        "wikiEnabled": true
    }
    """
    url = f"{configs.settings.ali_yunxiao}/oapi/v1/codeup/organizations/5f278b52d248146039338d7b/repositories/{repositories_id}"
    headers = {"x-yunxiao-token": token}
    response = await httpx_utils.httpx_client.get(url, headers=headers)
    if response.status_code != status.HTTP_200_OK:
        log_util.logger.error(f"获取代码组内仓库详情失败 {response.text}")
        response_utils.server_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "获取代码组内仓库详情失败")
    return response.json()


async def get_ali_yunxiao_user(token, page=1, perpage=20):
    """
    [
        {
            "id": "678e24bfbe33c6ae5a1344e2",
            "organizationId": "5f278b52d248146039338d7b",
            "userId": "678dfb3a3f05113b85e3d9a8",
            "name": "某某",
            "email": "",
            "roleIds": [
                "5f278b52cd3711dd642276d5"
            ],
            "status": "ENABLED",
            "deptIds": [
                "66ab26f5d623b2f55d81b4b2"
            ],
            "joined": "2025-01-20T10:26:07.329Z",
            "visited": "2026-09-10T03:12:10.924Z",
            "lastUpdated": "2026-09-10T03:12:04.714Z"
        },
        {
            "id": "67cfa0ee120358055abfd2f5",
            "organizationId": "5f278b52d248146039338d7b",
            "userId": "67cfa0ed8bb0a312ed3bca35",
            "name": "曾小月",
            "email": "zeng.xiaoyue@fescoadecco.com",
            "roleIds": [
                "5f278b52cd3711dd642276d5"
            ],
            "status": "ENABLED",
            "deptIds": [
                "66ab26f5d623b2f55d81b4b2"
            ],
            "joined": "2025-03-11T02:33:18.093Z",
            "visited": "2026-09-14T07:47:09.148Z",
            "lastUpdated": "2026-09-14T01:47:44.578Z"
        }
    ]
    """
    url = f"{configs.settings.ali_yunxiao}/oapi/v1/platform/organizations/5f278b52d248146039338d7b/members"
    headers = {"x-yunxiao-token": token}
    response = await httpx_utils.httpx_client.get(url, headers=headers, params={"page": page, "perpage": perpage})
    if response.status_code != status.HTTP_200_OK:
        log_util.logger.error(f"获取用户失败 {response.text}")
        response_utils.server_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "获取用户失败")
    return response.json()
