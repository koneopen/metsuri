from metsuri.log_uploader import upload_log, ChunkUploader, Event
from unittest import mock
import datetime
import freezegun
import pytest
import tempfile
from contextlib import contextmanager


@contextmanager
def mock_aws():
    with tempfile.NamedTemporaryFile() as timestamp_file:
        timestamp_file_name = timestamp_file.name

        with mock.patch('metsuri.log_uploader.get_next_sequence_token'), \
                mock.patch('metsuri.log_uploader.boto3'), \
                mock.patch('metsuri.log_uploader.upload_batch',
                           autospec=True) as mock_upload_batch:
            yield mock_upload_batch, timestamp_file_name


def test_upload_log(log_file_name):
    log_data = """\
    2021-01-24T19:13:15.501126+00:00 rsyslogd: [origin software="rsyslogd" swVersion="5.10.1" x-pid="1125" x-info="http://www.rsyslog.com"] start
    2021-01-24T19:12:35.143911+00:00 kernel: Booting Linux on physical CPU 0x0
    2021-01-24T19:12:35.143910+00:00 kernel: Linux version Fooest of foo
    2021-01-24T19:12:35.143910+00:00 kernel: CPU: ARMv12 Processor
    2021-01-24T19:12:35.143909+00:00 kernel: CPU: imaginary pipeline side-channel leakage prevention methods engaged
    2021-01-24T19:12:35.143909+00:00 kernel: OF: fdt: Machine model: The bestest
    2021-01-24T19:12:35.143909+00:00 kernel: bootconsole [earlycon0] enabled
    2021-01-24T19:12:35.143909+00:00 kernel: Memory policy: Data cache writeback
    2021-01-24T19:12:35.143909+00:00 kernel: On node 0 totalpages: so many\
    """
    with open(log_file_name, "w") as fp:
        fp.write(log_data)

    # AWS CloudWatch logs put_log_events API dislikes batches with events
    # with non-monotonous timestamps, so such cases should cause a new batch
    # to be started.
    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", min_time_between_requests=0,
                   timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 4
        assert len(mock_upload_batch.call_args_list[0][0][3]) == 1
        assert len(mock_upload_batch.call_args_list[1][0][3]) == 1
        assert len(mock_upload_batch.call_args_list[2][0][3]) == 2
        assert len(mock_upload_batch.call_args_list[3][0][3]) == 5

        assert datetime.datetime.fromisoformat(open(timestamp_file_name).read())

    # Deal with:
    # botocore.errorfactory.InvalidParameterException: An error occurred (
    # InvalidParameterException) when calling the PutLogEvents
    # operation: The batch of log events in a single PutLogEvents request
    # cannot span more than 24 hours.

    with open(log_file_name, "w") as fp:
        fp.write("""\
        2021-01-24T19:13:15.501126+00:00 aardvark
        2021-01-25T19:13:16.143911+00:00 beerdverk\
        """)

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", min_time_between_requests=0,
                   timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 2
        assert "aardvark" in mock_upload_batch.call_args_list[0][0][3][0].message
        assert "beerdverk" in mock_upload_batch.call_args_list[1][0][3][0].message


def test_upload_log_broken_input(log_file_name):
    with open(log_file_name, "w") as fp:
        fp.write("""\
        2021-01-24T19:13:15.501126+00:00 aardvark
        
        2021-01-25T19:13:16.143911+00:00 beerdverk
        
        """)

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", min_time_between_requests=0,
                   timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 2
        assert "aardvark" in mock_upload_batch.call_args_list[0][0][3][0].message
        assert "beerdverk" in mock_upload_batch.call_args_list[1][0][3][0].message


def test_upload_log_max_batch_size(log_file_name):
    with open(log_file_name, "w") as fp:
        fp.write("""\
    2021-01-24T19:13:15.501126+00:00 rsyslogd: [origin software="rsyslogd" swVersion="5.10.1" x-pid="1125" x-info="http://www.rsyslog.com"] start
    2021-01-24T19:14:35.143911+00:00 kernel: Booting Linux on physical CPU 0x0
    2021-01-24T19:12:35.143910+00:00 kernel: Linux version The bestest
""")

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", max_batch_size=1, min_time_between_requests=0, timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 3

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", max_batch_size=108+26, min_time_between_requests=0, timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 3

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", max_batch_size=108+26+49+26, min_time_between_requests=0, timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 2

    with open(log_file_name, "w") as fp:
        fp.write("""\
    2021-01-24T19:13:15.501126+00:00 rsyslogd: [origin software="rsyslogd" swVersion="5.10.1" x-pid="1125" x-info="http://www.rsyslog.com"] start
    2021-01-24T19:14:35.143911+00:00 kernel: Booting Linux on physical CPU 0x0
    2021-01-24T19:12:35.143910+00:00 kernel: Linux version The bestest 123456789 123456789 123456789 123456789 123456789 123456789 12345678901
    2021-01-24T19:12:36.143910+00:00 kernel: Linux version The bestest 123456789 123456789 123456789 123456789 123456789 123456789 12345678901
    2021-01-24T19:12:37.143910+00:00 kernel: Linux version The bestest 123456789 123456789 123456789 123456789 123456789 123456789 12345678901
""")

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", max_batch_size=2*105+2*26, min_time_between_requests=0, timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 3

    # first event message 81 bytes
    with open(log_file_name, "w") as fp:
        fp.write("""\
    2021-01-24T19:11:15.501126+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 1
    2021-01-24T19:12:35.143911+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 22
    2021-01-24T19:12:36.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 333
    2021-01-24T19:12:37.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 4444
    2021-01-24T19:12:38.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 55555
    2021-01-24T19:12:39.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 666666
    2021-01-24T19:12:40.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 7777777
""")

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", max_batch_size=3*82 + 3*26, min_time_between_requests=0, timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 3

    # first event message 81 bytes
    with open(log_file_name, "w") as fp:
        fp.write("""\
    2021-01-24T19:11:15.501126+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 1
    2021-01-24T19:12:35.143911+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 22
    2021-01-24T19:12:36.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 333
    2021-01-24T19:12:37.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 4444
    2021-01-24T19:12:38.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 55555
    2021-01-24T19:12:39.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 666666
    2021-01-24T19:12:40.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 7777777
    2021-01-24T19:12:41.143910+00:00 aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb aaaaa bbb 88888888
""")

    with mock_aws() as (mock_upload_batch, timestamp_file_name):
        upload_log(log_file_name, "foo", "bar", max_batch_size=3*82 + 3*26, min_time_between_requests=0, timestamp_file_name=timestamp_file_name)
        assert mock_upload_batch.call_count == 4


def test_empty_event():
    with mock.patch('metsuri.log_uploader.get_next_sequence_token'):
        uploader = ChunkUploader(mock.MagicMock(), "foo", "bar", "tsap",
                                 0, 5000, 1)
        assert not uploader.batch
        uploader.append(Event(timestamp=datetime.datetime.now(), message="foo"))
        assert len(uploader.batch) == 1
        uploader.append(Event(timestamp=datetime.datetime.now(), message=""))
        assert len(uploader.batch) == 1


def test_max_time_between_appends():
    with freezegun.freeze_time() as frozen_time:
        with mock.patch('metsuri.log_uploader.get_next_sequence_token'), \
             mock.patch('metsuri.log_uploader.upload_batch') as mock_upload_batch:
            uploader = ChunkUploader(mock.MagicMock(), "foo", "bar", "tsap",
                                     0, 5000, 1)
            assert not uploader.batch
            uploader.append(Event(timestamp=datetime.datetime.now(), message="foo"))
            assert len(uploader.batch) == 1

            frozen_time.tick(delta=datetime.timedelta(seconds=2))
            uploader.append(Event(timestamp=datetime.datetime.now(), message=""))
            assert len(uploader.batch) == 0
            mock_upload_batch.assert_called_once()


def test_upload_log_with_invalid_utf8(log_file_name):
    log_data = b"""\
    2021-01-24T19:13:15.501126+00:00 rsyslogd: [origin software="rsyslogd" swVersion="5.10.1" x-pid="1125" x-info="http://www.rsyslog.com"] start
    2021-01-24T19:13:17.501126+00:00 rsyslogd: this should be invalid \xc2
    """
    with open(log_file_name, "wb") as fp:
        fp.write(log_data)

    with pytest.raises(UnicodeDecodeError):
        open(log_file_name).read()

    with mock.patch('metsuri.log_uploader.get_next_sequence_token'), \
            mock.patch('metsuri.log_uploader.boto3'), \
            mock.patch('metsuri.log_uploader.upload_batch') as mock_upload_batch:
        upload_log(log_file_name, "foo", "bar", min_time_between_requests=0)
        assert len(mock_upload_batch.call_args_list[0][0][3]) == 2
        msg = mock_upload_batch.call_args_list[0][0][3][1].message
        assert "invalid \\xc2" in msg


def test_upload_log_with_invalid_timestamp(log_file_name):
    log_data = b"""\
    2021-01-24T19:11:17.501126+00:00 rsyslogd: this should be valid
    22021-01-24T19:13:15.501126+00:00 rsyslogd: [origin software="rsyslogd" swVersion="5.10.1" x-pid="1125" x-info="http://www.rsyslog.com"] start
    2021-01-24T19:13:17.501126+00:00 rsyslogd: this should be valid again
    """
    with open(log_file_name, "wb") as fp:
        fp.write(log_data)

    with mock.patch('metsuri.log_uploader.get_next_sequence_token'), \
            mock.patch('metsuri.log_uploader.boto3'), \
            mock.patch('metsuri.log_uploader.upload_batch') as mock_upload_batch:
        upload_log(log_file_name, "foo", "bar", min_time_between_requests=0)
        assert len(mock_upload_batch.call_args_list[0][0][3]) == 2
        msg = mock_upload_batch.call_args_list[0][0][3][1].message
        assert "valid again" in msg
