from datetime import datetime, timedelta


def get_previous_day(date_string: str) -> str:
    """
    Returns the previous day in string format.

    :param date_string: Date string in the format yyyy/mm/dd
    """
    date = datetime.strptime(date_string, "%Y/%m/%d")
    previous_day = date - timedelta(days=1)
    return previous_day.strftime("%Y/%m/%d")
