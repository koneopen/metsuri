from metsuri.log_download import parse_period, parse_interval
import datetime
import pytest
import re
from freezegun import freeze_time


def test_parse_interval():
    assert parse_interval("1d") == datetime.timedelta(days=1)
    assert parse_interval("1s") == datetime.timedelta(seconds=1)

    with pytest.raises(ValueError, match=re.compile("invalid", re.I)):
        parse_interval("foo")

    assert parse_interval("2d12h30m15s") == \
           datetime.timedelta(days=2, hours=12, minutes=30, seconds=15)


def test_parse_period():
    from_value, to_value = parse_period(
        None, "1d", "2020-02-10T10:10")
    assert to_value == datetime.datetime(year=2020, month=2, day=10, hour=10,
                                         minute=10).astimezone()
    assert from_value == datetime.datetime(year=2020, month=2, day=9, hour=10,
                                           minute=10).astimezone()

    from_value, to_value = parse_period(
        None, "1d", "2020-02-10T10:10:00+04:00")
    assert to_value == datetime.datetime(year=2020, month=2, day=10, hour=10,
                                         minute=10, tzinfo=datetime.timezone(datetime.timedelta(seconds=14400), "test"))
    assert from_value == datetime.datetime(year=2020, month=2, day=9, hour=10,
                                           minute=10, tzinfo=datetime.timezone(datetime.timedelta(seconds=14400), "test"))

    from_value, to_value = parse_period(
        "2020-02-08T10:10:00+04:00", "1d", "2020-02-11T10:10:00+04:00")
    assert to_value == datetime.datetime(year=2020, month=2, day=11, hour=10,
                                         minute=10, tzinfo=datetime.timezone(datetime.timedelta(seconds=14400), "test"))
    assert from_value == datetime.datetime(year=2020, month=2, day=8, hour=10,
                                           minute=10, tzinfo=datetime.timezone(datetime.timedelta(seconds=14400), "test"))

    from_value, to_value = parse_period(
        "2020-02-08T10:10:00+04:00", None, "2020-02-11T10:10:00+04:00")
    assert to_value == datetime.datetime(year=2020, month=2, day=11, hour=10,
                                         minute=10, tzinfo=datetime.timezone(datetime.timedelta(seconds=14400), "test"))
    assert from_value == datetime.datetime(year=2020, month=2, day=8, hour=10,
                                           minute=10, tzinfo=datetime.timezone(datetime.timedelta(seconds=14400), "test"))

    from_value, to_value = parse_period(
        "2020-02-10T10:10", "1d", None)
    assert to_value == datetime.datetime(year=2020, month=2, day=11, hour=10,
                                         minute=10).astimezone()
    assert from_value == datetime.datetime(year=2020, month=2, day=10, hour=10,
                                           minute=10).astimezone()

    from_value, to_value = parse_period(None, None, None)
    assert to_value - from_value == datetime.timedelta(days=1)

    with freeze_time("2020-02-10T10:10:00+04:00"):
        from_value, to_value = parse_period("2020-02-07T10:10:00+04:00", None, None)
        assert to_value - from_value >= datetime.timedelta(days=3)

        from_value, to_value = parse_period("2020-02-07T10:10", "1d", None)
        assert to_value - from_value <= datetime.timedelta(days=1)

        from_value, to_value = parse_period(None, None, None)
        assert to_value - from_value == datetime.timedelta(days=1)
        # assert