"""
通用工具函数模块

提供日期时间处理、JSON编解码、随机字符串生成、字典处理等常用工具函数
"""

import asyncio
import functools
import re
import string
import uuid
import json
import hashlib
import secrets
import datetime
import random
import decimal
from collections import Counter, defaultdict
from urllib import parse
import aiofiles
from fastapi.responses import JSONResponse
from openpyxl import Workbook
import orjson

from vrm.tomo.utils import log_util


# 随机字符串生成字符集：字母、数字、下划线
CHARACTERS = string.ascii_letters + string.digits + "_"
# 预定义格式列表，按精度从高到低排列
DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",  # 2026-05-22T19:00:00.123456+08:00
    "%Y-%m-%dT%H:%M:%S%z",  # 2026-05-22T19:00:00+08:00
    "%Y-%m-%dT%H:%M:%S.%f",  # 2026-05-22T19:00:00.123456
    "%Y-%m-%dT%H:%M:%S",  # 2026-05-22T19:00:00
    "%Y-%m-%dT%H:%M",  # 2026-05-22T19:00
    "%Y-%m-%d %H:%M:%S.%f",  # 2026-05-22 19:00:00.123456
    "%Y-%m-%d %H:%M:%S",  # 2026-05-22 19:00:00
    "%Y-%m-%d %H:%M",  # 2026-05-22 19:00
    "%Y-%m-%d",  # 2026-05-22
    "%Y/%m/%d %H:%M:%S.%f",  # 2026/05/22 19:00:00.123456
    "%Y/%m/%d %H:%M:%S",  # 2026/05/22 19:00:00
    "%Y/%m/%d %H:%M",  # 2026/05/22 19:00
    "%Y/%m/%d",  # 2026/05/22
]


def datetime_to_string(d_time=None):
    """将当前日期时间转换为字符串格式 YYYY-MM-DD HH:MM:SS"""
    if not d_time:
        d_time = datetime.datetime.now()
    return d_time.strftime("%Y-%m-%d %H:%M:%S")


def date_to_string():
    """将当前日期转换为字符串格式 YYYY-MM-DD"""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def ws_datetime():
    """获取格式化的当前日期时间和星期信息"""
    current = datetime.datetime.now()
    current_date_time = current.strftime("%Y-%m-%d %H:%M:%S")
    weekday = current.strftime("%A")
    return f"今天是：{current_date_time}, {weekday}"


def timestamp_to_string():
    """获取当前时间戳（毫秒级）"""
    return str(int(datetime.datetime.now().timestamp() * 1000))


class JsonExtendEncoder(json.JSONEncoder):
    """扩展的JSON编码器，支持日期时间、日期、小数、字节等类型"""

    def default(self, obj):
        # 处理元组、列表、日期时间
        if isinstance(obj, (tuple, list, datetime.datetime)):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        # 处理日期
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        # 处理小数
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        # 处理字节
        elif isinstance(obj, bytes):
            return obj.decode("utf-8")
        return super().default(obj)


class JsonExtendResponse(JSONResponse):
    """使用扩展编码器的JSON响应"""

    def render(self, content):
        return json.dumps(content, cls=JsonExtendEncoder).encode("utf-8")


def dict_to_json(data):
    """将字典转换为JSON字符串"""
    if not data:
        data = {}
    return json.dumps(data, cls=JsonExtendEncoder)


def dict_to_json_ea(data=None):
    """将字典转换为JSON字符串（保留中文字符）"""
    return json.dumps(data, cls=JsonExtendEncoder, ensure_ascii=False)


def json_to_dict(json_data):
    """将JSON字符串转换为字典"""
    return json.loads(json_data)


def generate_uuid():
    """生成MD5格式的UUID（32位小写）"""
    random_uuid = str(uuid.uuid4())
    md5 = hashlib.md5()
    md5.update(random_uuid.encode("utf-8"))
    return md5.hexdigest().lower()


def generate_trace_id():
    """生成追踪ID（标准UUID格式）"""
    return str(uuid.uuid4())


def trigger_butterfly(probability=0.3):
    """根据概率触发蝴蝶效应，默认30%概率"""
    return random.random() < probability


def get_butterfly_task(dict_list):
    """从任务列表中随机获取一个任务并移除"""
    if not dict_list:
        return None
    index = random.randint(0, len(dict_list) - 1)
    return dict_list.pop(index)


def generate_random_str(length):
    """生成指定长度的安全随机字符串（包含字母、数字、下划线）"""
    return "".join(secrets.choice(CHARACTERS) for i in range(length))


def generate_app_key():
    """生成12位的应用密钥"""
    return generate_random_str(12)


def generate_app_secret():
    """生成32位的应用密钥"""
    return generate_random_str(32)


def find_value(data, key):
    """
    在嵌套字典/列表中递归查找指定键的值

    Args:
        data: 字典或列表
        key: 要查找的键名

    Returns:
        找到的值，未找到返回None
    """
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for k, v in data.items():
            result = find_value(v, key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_value(item, key)
            if result is not None:
                return result
    return None


def replace_null_values(data):
    """递归替换数据中的空值（None、空字符串、null）为'暂无'"""
    if isinstance(data, dict):
        return {k: replace_null_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_null_values(item) for item in data]
    elif not data or (isinstance(data, str) and data.lower() in ("null", "none")):
        return "暂无"
    else:
        return data


def get_today_info():
    """获取今天的信息：星期几（1-7）和一年中的第几周"""
    today = datetime.date.today()
    return {"weekday": today.isocalendar()[2], "week_number": today.isocalendar()[1]}


def get_last_month():
    """获取上个月的年月字符串，格式：YYYYMM"""
    today = datetime.datetime.today()
    year, month = today.year, today.month
    if month == 1:
        year, month = year - 1, 12
    else:
        month -= 1
    return f"{year}{month:02d}"


def get_time_period():
    """获取当前时间段：上午(am)、下午(pm)或其他(ng)"""
    hour = datetime.datetime.now().hour
    if 6 <= hour < 12:
        return "am"
    elif 12 <= hour < 18:
        return "pm"
    return "ng"


def find_common_elements(list_a, list_b):
    """查找两个列表的交集元素"""
    return [element for element in list_a if element in list_b]


def remove_elements_optimized(list_a, list_b):
    """从列表A中移除列表B中存在的元素"""
    return list(set(list_a) - set(list_b))


def insert_at_penultimate_position(lst: list, element):
    """在列表倒数第二位插入元素"""
    position = 0 if len(lst) < 1 else len(lst) - 1
    lst.insert(position, element)
    return lst


def select_random_by_category(data, dict_key):
    """从列表中按类别随机选择一个元素，每个类别选一个"""
    category_dict = defaultdict(list)
    for item in data:
        category_dict[item[dict_key]].append(item)
    return [random.choice(items) for items in category_dict.values()]


def group_by_daily(data, dict_key):
    """按日期分组数据"""
    result = defaultdict(list)
    for item in data:
        result[item[dict_key]].append(item)
    return dict(result)


def merge_lists(list_a, list_b):
    """合并两个列表"""
    list_a.extend(list_b)
    return list_a


def byte_to_int(byte_data: bytes) -> int:
    """将字节数据转换为整数"""
    return int(byte_data.decode("utf-8"))


def get_format_str(time_str: str) -> str:
    """根据时间字符串推断日期格式"""
    format_str = "%Y-%m-%d %H:%M:%S"
    if "T" in time_str:
        format_str = format_str.replace(" ", "T")
    if "Z" in time_str:
        format_str += "Z"
    return format_str


def time_str_to_datetime(time_str: str) -> datetime.datetime:
    """将时间字符串转换为datetime对象"""
    return datetime.datetime.strptime(time_str, get_format_str(time_str))


def trans_to_chinese(s: str):
    """将Unicode转义字符串转换回中文"""
    try:
        s = s.encode("unicode_escape")
        return parse.unquote(s.decode("utf-8").replace("\\x", "%"))
    except Exception as e:
        log_util.logger.exception(e)
        return ""


def is_strict_datetime_format(date_str):
    """验证日期字符串是否符合 YYYY-MM-DD HH:MM 格式"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False


def validate_time_format(time_str, format):
    """验证时间字符串是否符合指定格式"""
    try:
        datetime.datetime.strptime(time_str, format)
        return True
    except ValueError:
        return False


def get_random_string(length):
    """生成指定长度的随机字符串（字母+数字）"""
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def get_md5(s):
    """计算字符串的MD5值"""
    if not s:
        return ""
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def write_xlsx(
    data: list[dict],
    path: str,
    header: dict | None = None,
    exclude_field: list | None = None,
):
    """
    将数据写入Excel文件

    Args:
        data: 要写入的数据列表
        path: 文件保存路径
        header: 表头映射，key为原字段名，value为显示名称
        exclude_field: 要排除的字段列表
    """
    workbook = Workbook()
    worksheet = workbook.active
    i = 0
    for row in data:
        row_to_write = dict(row)
        for field in exclude_field or []:
            row_to_write.pop(field, None)
        if i == 0:
            if header:
                keys = list(row_to_write.keys())
                worksheet.append([header[k] for k in keys])
            else:
                worksheet.append(list(row_to_write.keys()))
            i += 1
        worksheet.append(list(row_to_write.values()))
    workbook.save(path)


def remove_duplicates(my_list: list):
    """去除列表中重复的元素，只保留出现一次的元素"""
    my_list.sort()
    counts = Counter(my_list)
    return [item for item in my_list if counts[item] == 1]


async def write_append_to_file(filename, data):
    """异步追加写入文件"""
    async with aiofiles.open(filename, mode="a+", encoding="utf-8") as file:
        await file.write(data)
        await file.write("\n\n")


def split_parameters(params_list: list[str]) -> list:
    """将参数列表（如['1-3', '5-7']）展开为单独的数字列表"""
    result = []
    for param in params_list:
        result.extend(int(s) for s in param.split("-"))
    return result


def judge_dict_is_same(dict1: dict, dict2: dict):
    """
    判断dict1中的键值对是否与dict2相等（只比较dict1中存在的键）

    Returns:
        True表示相同，False表示有差异
    """
    for k, v in dict1.items():
        if v != dict2.get(k):
            log_util.logger.debug(f"键 '{k}' 的值不匹配: {v} != {dict2.get(k)}")
            return False
    return True


def async_retry_on_error(max_attempts=3, delay=1):
    """
    异步函数重试装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 每次重试前等待的秒数

    Returns:
        装饰器函数
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                err, result = await func(*args, **kwargs)
                if not err:
                    return err, result
                last_error = err
                log_util.logger.error(f"尝试第{attempt}次调用{func.__name__}失败，{delay}秒后重试")
                if delay:
                    await asyncio.sleep(delay)
            log_util.logger.error(f"多次重试后仍失败: {last_error}")
            return last_error, result

        return wrapper

    return decorator


def get_chinese_level(level):
    """将数字级别转换为中文级别描述"""
    level_map = {1: "第一级", 2: "第二级", 3: "第三级"}
    return level_map.get(level, "")


def detect_language(text):
    """检测文本的主要语言：中文、英文或无法判断"""
    chinese_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fa5")
    english_count = sum(1 for char in text if char.isascii())
    if chinese_count > english_count:
        return "chinese"
    elif english_count > chinese_count:
        return "english"
    return "无法判断"


# 输入验证正则表达式：允许中英文、数字、常用标点
ALLOWED_PATTERN = re.compile(
    r"^[a-zA-Z0-9\u4e00-\u9fa5\s"
    r".,;:!\?\'\"()\[\]{}"
    r"，。、；：？！"
    r"''【】《》…—·"
    r"@#$%^&*\-_+=|\\\/~`<>]+$"
)


def validate_input(text: str) -> tuple[bool, str]:
    """
    验证输入是否只包含允许的字符（中英文、数字、标点）

    Returns:
        (是否有效, 错误消息)
    """
    if not text:
        return False, "输入不能为空"
    if not ALLOWED_PATTERN.match(text):
        return False, "输入只能包含中英文、数字和标点符号"
    return True, ""


def sanitize_for_db(text: str) -> str:
    """过滤数据库无法安全存储的字符（连接已为 utf8mb4）"""
    if not text:
        return text
    # 空字节：MySQL 遇到会截断字符串
    text = text.replace("\x00", "")
    # 不可见控制字符（保留 \t \n \r）
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


def clean_illegal_characters(value):
    """清除 openpyxl 不允许写入 Excel 的非法控制字符。"""

    ILLEGAL_CHARACTERS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    if isinstance(value, str):
        return ILLEGAL_CHARACTERS_RE.sub("", value)
    return value


def get_hash(secret_key: str):
    """计算字符串的SHA256哈希值"""
    return hashlib.sha256(secret_key.encode("utf-8")).hexdigest()


def is_transform_to_dict(data: str):
    """检查字符串是否为有效的JSON格式"""
    try:
        if isinstance(orjson.loads(data), dict):
            return True
        else:
            return False
    except Exception:
        return False


def is_exceeded(db_time, threshold_minutes=15):
    current_time = datetime.datetime.now()  # db_time type is datetime
    time_difference = current_time - db_time
    return time_difference > datetime.timedelta(minutes=threshold_minutes)


def trans_list_datetime_to_str(data_list: list[dict]):
    data_list_json = dict_to_json_ea(data_list)
    data_list_dict = json.loads(data_list_json)
    return data_list_dict


def parse_datetime(dt_string: str) -> datetime.datetime:
    """
    动态解析多种格式的日期时间字符串。

    注意：Python 的 %f 只支持微秒（6位），
    如果传入纳秒（9位），需要先截断到微秒。
    """
    if not dt_string or not isinstance(dt_string, str):
        raise ValueError(f"无效的日期时间字符串: {dt_string}")

    # 去除首尾空格
    dt_string = dt_string.strip()

    # 处理纳秒：Python datetime 最多支持微秒(6位)
    # 将超过6位的小数部分截断为6位
    dt_string = _truncate_subseconds(dt_string)

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.datetime.strptime(dt_string, fmt)
        except ValueError:
            continue

    raise ValueError(f"无法解析日期时间字符串: {dt_string}, 请使用支持的格式，如: 'YYYY-MM-DD HH:MM:SS'")


def _truncate_subseconds(dt_string: str) -> str:
    """
    将小数秒部分截断为6位（微秒精度）。

    处理场景：
    - 2026-05-22 19:00:00.123456789 -> 2026-05-22 19:00:00.123456
    - 2026-05-22T19:00:00.123456789+08:00 -> 2026-05-22T19:00:00.123456+08:00
    """
    # 匹配小数秒部分（可能后面跟时区信息）
    pattern = r"(\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2})\.(\d+)(.*)"
    match = re.match(pattern, dt_string)
    if match:
        base = match.group(1)
        fractional = match.group(2)[:6].ljust(6, "0")  # 截断到6位，不足补0
        suffix = match.group(3)
        return f"{base}.{fractional}{suffix}"
    return dt_string


def local_datetime_to_utc_str(local_dt: str) -> str:
    """将本地时间转换为UTC时间字符串"""
    local_time = parse_datetime(local_dt)
    utc_time = local_time.astimezone(datetime.timezone.utc)
    utc_time_str = utc_time.strftime("%Y-%m-%dT%H:%M:%S")
    return utc_time_str


def utc_str_to_local_datetime(utc_dt: str) -> str:
    """
    将 UTC 时间转换为系统本地时间。

    Args:
        utc_dt: UTC 时间的 datetime 对象

    Returns:
        转换后的本地时间 datetime 对象
    """
    # 如果传入的 datetime 没有时区信息，先标记为 UTC
    utc_dt = parse_datetime(utc_dt)
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=datetime.timezone.utc)

    # 转换为系统本地时间
    local_dt = utc_dt.astimezone(tz=None)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


def str_time_tran_file_name(time_str: str):
    return time_str.replace(" ", "_").replace("-", "_").replace(":", "_")


def stable_dumps(data: dict) -> str:
    """生成稳定的序列化字符串"""
    return json.dumps(data, sort_keys=True, ensure_ascii=False)
