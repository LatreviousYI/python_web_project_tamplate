def division(numerator, denominator) -> float:
    """
    description: 分母为0时不报错
    param {*} numerator
    param {*} denominator
    return {*}
    """
    if not denominator:
        return 0
    return numerator / denominator


def calculate_ring_ratio(current_num, last_period_num, where_last_period_num_is_zero_ring_ratio_result=1) -> float:
    """
    description: 计算环比
    param {*} current_num 本期数据
    param {*} last_period_num 上期数据
    param {*} where_last_period_num_is_zero_ring_ratio_result 当上期数据为0时,本期有数据时应返回什么值,默认1 表示100%增长
    return {*}
    """
    if not last_period_num and current_num:
        return where_last_period_num_is_zero_ring_ratio_result
    elif not last_period_num and not current_num:
        return 0
    else:
        return (current_num - last_period_num) / last_period_num
