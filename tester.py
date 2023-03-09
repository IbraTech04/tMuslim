def elapsed_time(start_hour, start_minute, end_hour, end_minute):
    """
    >>> elapsed_time(23, 59, 0, 0)
    (0, 1)
    >>> elapsed_time(0, 0, 0, 0)
    (0, 0)

    :param start_hour:
    :param start_minute:
    :param end_hour:
    :param end_minute:
    :return:
    """
    hour_left = 0
    min_left = 60 - start_minute
    end_hour -= 1
    min_left += end_minute
    if min_left >= 60:
        hour_left += 1
        min_left = min_left - 60
    hour_left = hour_left + (end_hour - start_hour)
    if hour_left < 0:
        hour_left += 24
    return hour_left, min_left
