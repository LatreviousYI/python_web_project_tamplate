import httpx
import orjson

import configs
from utils import cipher_util, httpx_utils, log_util, tools


def process_json_data(data: dict | str | list, result_type: str = "dict") -> dict | list | str:
    """
    description: 获取想要的类型会进行转换
    param {tuple} data
    param {*} str
    param {*} list
    param {str} result_type
    return {*}
    """
    match result_type:
        case "str":
            if isinstance(data, str):
                return data
            elif isinstance(data, dict):
                return tools.dict_to_json(data)
            elif isinstance(data, list):
                return tools.dict_to_json(data)
            else:
                log_util.logger.error(f"betteryeah返回陌生格式报错:{data} {type(data)}")
                raise ValueError("不支持此格式")
        case "dict" | "list":
            if isinstance(data, str):
                processed_json_data = data.replace("'", '"').replace("`", "").replace("json", "").replace("\n", "")
                try:
                    dict_p = tools.json_to_dict(processed_json_data)
                    return dict_p
                except orjson.JSONDecodeError:
                    log_util.logger.error(f"json格式化错误,原内容:{processed_json_data}")
                    return {}
            elif isinstance(data, dict):
                return data
            elif isinstance(data, list):
                return data
            else:
                log_util.logger.error(f"betteryeah返回陌生格式报错:{data} {type(data)}")
                raise ValueError("不支持此格式")
        case _:
            raise ValueError(f"不支持此格式 {result_type}")


async def execute_flow(flow_id: str, data: dict) -> dict:
    """
    description: 执行better yeah 工作流
    param {str} flow_id 2aa62daf2bea4ce8ae4606371b0048cd
    param {dict} data
    data = {
        "inputs": {
            "message": content,
            "histories": histories,
            "datetime": dt,
            "params": params,
        }
    }
    return {*}
    """
    url = f"{configs.settings.better_yeah_url}/public_api/rest_api/{flow_id}/execute_flow"
    headers = {
        "Content-Type": "application/json",
        "Access-key": cipher_util.cipher.decrypt(configs.settings.access_key),
        "Workspace-Id": configs.settings.workspace_id,
    }
    try:
        response = await httpx_utils.httpx_client.post(url, headers=headers, json=data)
        if response.status_code != 200:
            log_util.logger.error(response.text)
            return {}
        response_json = response.json()
        if response_json.get("code") != 200:
            log_util.logger.error(f"betteryeah请求失败,{response_json}")
            return {}
        return response_json
    except httpx.TimeoutException as e:
        log_util.logger.exception(e)
        return {}
    except Exception as e:
        log_util.logger.exception(e)
        return {}


async def verfiy_content(content) -> dict | list | str:
    """
    description:
    param {str} msg
    return {
        "pass": false,
        "reason": "包含脏话"
    }
    内容由AI生成
    """
    flow_id = "45d892aca40940af99fc70fe914d6d20"
    data = {
        "inputs": {
            "message": content,
        }
    }
    response_json = await execute_flow(flow_id, data)
    return process_json_data(response_json["data"]["run_result"])
