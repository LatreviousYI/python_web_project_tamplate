import time
from urllib.parse import quote
from fastapi import status

import configs
from utils import log_util, response_utils, tools, httpx_utils


def get_client_or_secret(is_backstage=True, is_client_id=True):
    if is_backstage:
        if is_client_id:
            return configs.settings.fast_go_client
        else:
            return configs.settings.fast_go_secret_key
    else:
        if is_client_id:
            return configs.settings.fast_go_client
        else:
            return configs.settings.fast_go_secret_key


# 获取登录页地址 local_url为当前用户访问的地址,登录完后会跳回到这个地址
def get_login_url(local_url, is_backstage=True):
    login_url = f"{configs.settings.fast_go_website_url}/login?client={get_client_or_secret(is_backstage, True)}&redirect={quote(local_url)}"
    return login_url


# 接收ticket后拼接成一个url供后续使用
def get_sign_by_ticket_url(ticket, is_backstage=True):
    timestamp = str(int(time.time() * 1000))  # 时间戳
    nonce = tools.get_random_string(32)  # 随机字符串
    sign_full_str = f"client={get_client_or_secret(is_backstage, True)}&nonce={nonce}&ticket={ticket}&timestamp={timestamp}&key={get_client_or_secret(is_backstage, False)}"
    sign = tools.get_md5(sign_full_str)
    check_ticket_url = f"{configs.settings.fast_go_api_url}/api/fast-go/sso/checkTicket?ticket={ticket}&client={get_client_or_secret(is_backstage, True)}&timestamp={timestamp}&nonce={nonce}&sign={sign}"
    return check_ticket_url


# 请求拼接好的ticket 获取用户信息
# 返回结果如下
# {
#     "code": 200,
#     "userAccountInfo": {
#         "accountArea": "",
#         "accountCode": "NVYQL",
#         "accountStatus": "Normal",
#         "createdBy": "",
#         "createdId": 0,
#         "createdTime": 1742288991000,
#         "disabled": false,
#         "email": "lv.yitao@fescoadecco.com",
#         "firstLoginFlag": false,
#         "id": 7140,
#         "lastLoginTime": 1742368576944,
#         "loginType": "EmailCode",
#         "mobilePhone": "",
#         "nickName": "lvyitao",
#         "paasId": "",
#         "password": "MWNrMTJiMTNrMWptanhyZzFoMDEyOWgybGo=:ApILV+NTsFk=",
#         "revision": 0,
#         "spareEmail": "",
#         "sparePhone": "",
#         "tenantId": 1,
#         "tenantName": "FA",
#         "tenantCode": "",
#         "thirdId": "",
#         "updatedBy": "",
#         "updatedId": 0,
#         "updatedTime": 1742289688000,
#         "userName": ""
#     },
#     "fastToken":"kjhajhskjhkjhkj"
# }
async def do_fastgo_check_ticket(ticket, is_backstage=True):
    url = get_sign_by_ticket_url(ticket, is_backstage)
    response = await httpx_utils.httpx_client.post(url)
    return response.json()


async def get_menu_tree_by_token(fast_token, is_backstage=True):
    get_menu_url = (
        f"{configs.settings.fast_go_api_url}/api/fast-go/FunctionPoints/getMenuTreeByToken?clientCode={get_client_or_secret(is_backstage, True)}"
    )
    headers = {"Fast-Token": fast_token}
    response = await httpx_utils.httpx_client.post(get_menu_url, headers=headers)
    return response.json()


def get_permission_children(data: list, path: str, key_word: str, children_key_word: str):
    path_list = path.split(".")
    # 初始化当前数据指向整个数据集
    current_data = data
    # 初始化已达到的深度计数
    depth_reached = 0
    return_data = {}
    # 遍历路径中的每个 ID
    for path_id in path_list:
        # 标记是否找到当前路径 ID
        found = False
        # 在当前数据层级搜索匹配的 ID
        for item in current_data:
            if item.get(key_word) == path_id:
                # 深入到找到的元素的子元素
                current_data = item.get(children_key_word) or []
                return_data = item
                found = True
                # 增加已达到的深度
                depth_reached += 1
                break
        if not found:
            # 如果未找到匹配的 ID，则返回空列表
            return {}
    # 检查是否达到了完整的路径深度
    if depth_reached == len(path_list):
        # 返回匹配路径的最终子孙数据
        return return_data
    else:
        # 如果未达到完整路径深度，返回空列表
        return {}


# async def add_tenant(fast_token: str, tenant_code: str, tenant_alias: str):
#     """
#     description: # /api/fast-go/Tenant/addTenant 创建租户
#     param {str} fast_token
#     param {str} tenant_code
#     param {str} tenant_alias
#     return {*}
#     """

#     url = f"{configs.settings.fast_go_api_url}/api/fast-go/Tenant/addTenant"
#     headers = {"Fast-Token": fast_token}
#     body = {
#         "tenantInfo": {
#             "tenantCode": tenant_code,
#             "tenantAlias": tenant_alias,
#             "isEnterprise": False,
#             "isVendor": False,
#             "isArea": False,
#             "isManageAcc": True,
#         },
#         "clientIds": [configs.settings.fast_go_system_id],
#     }
#     response = await httpx_utils.httpx_client.post(url, headers=headers, json=body)
#     if response.status_code != 200:
#         log_util.logger.error(f"请求增加租户报错,header:{headers},body:{body},response:{response.text}")
#         return "请求增加租户报错"
#     response_json = response.json()
#     if response_json["code"] != 0:
#         log_util.logger.error(f"请求增加租户报错,header:{headers},body:{body},response:{response_json}")
#         return "请求增加租户报错"
#     return None


# 退出登录
async def login_out(fast_token):
    login_out_url = f"{configs.settings.fast_go_api_url}/api/fast-go/user/doExit"
    headers = {"Fast-Token": fast_token}
    response = await httpx_utils.httpx_client.post(login_out_url, headers=headers)
    if response.status_code != status.HTTP_200_OK:
        log_util.logger.error("fastgo退出登录失败")
        response_utils.server_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "fastgo退出登录失败")
    return response.json()


def clean_menu_fields(menu_list, fields_to_remove):
    """
    递归删除菜单数据结构中指定的字段
    :param menu_list: List[dict]  菜单树结构
    :param fields_to_remove: List[str]  需要删除的字段名
    :return: List[dict]  清理后的菜单结构
    """
    for item in menu_list:
        # 删除字段
        for field in fields_to_remove:
            field_value = item.pop(field, None)
            if field == "parentId":
                item["parent_id"] = field_value
        # 递归children
        children = item.get("children")
        if isinstance(children, list) and children:
            clean_menu_fields(children, fields_to_remove)
    return menu_list


async def get_tenant_list(fast_token: str, clientCode: str):
    url = f"{configs.settings.fast_go_api_url}/api/fast-go/api/user/auth/getTenantList?clientCode={clientCode}"
    headers = {"Fast-Token": fast_token}
    response = await httpx_utils.httpx_client.get(url, headers=headers)
    return response.json()


async def switch_tenant(fast_token, tenant_id: int):
    url = f"{configs.settings.fast_go_api_url}/api/fast-go/user/switchTenantDoLogin?tenantId={tenant_id}&clientCode="
    headers = {"Fast-Token": fast_token}
    response = await httpx_utils.httpx_client.post(url, headers=headers)
    return response.json()
