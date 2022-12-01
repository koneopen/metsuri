# Metsuri, a serial logger

Metsuri is a base component in a serial logging system. It makes it easy to 
monitor hardware that has an output that can be attached with, for example, a 
USB serial interface. 

As the monitoring hardware you will need something that runs the necessary
Python components. For example, a recent RaspberryPi will work splendidly.
16GB SD card is enough, probably a lot smaller will work, as the system tries
to upload the data to the cloud as soon as it is received.

The system comprises three main components, `serial-logger`, 
`log-uploader` and `log-download`. The `serial-logger` attaches to a serial 
line and logs the received data to a file, rotating files with requested 
intervals, `log-uploader` uploads the received events to AWS 
CloudWatch, and you download the logs from the desired internal from the 
cloud with `log-download`.

It is possible to just log the data locally, but AWS CloudWatch makes it
simple to share the updated logs with a team of people. It is also a very 
secure way to store the logs if the loggers are installed in a remote
location.

## Install needed packages

```shell script
% sudo apt-get update
% sudo apt-get install picocom supervisor python3-venv
```

## Create Python env

```shell script
% python3 -m venv ve
% . ve/bin/activate
(ve) % pip install metsuri-*.whl
```

## Copy supervisor config

```shell script
% cd supervisord
% sudo cp *.conf /etc/supervisor/conf.d
```

Currently `log_uploader.conf` needs to be modified. 
Modify the command-line to use correct serial device, log group and log 
stream for the device. Each device should have its own log stream.

If you wish to test the configuration, you can attach the USB serial and call

```shell script
% sudo supervisorctl reload
```

which will start services. Both services should end up in `RUNNING` when
observed with 

```shell script
% sudo supervisorctl status
```

In case of problems, logs can be found under `/var/log/supervisor/`

## Setup connection configuration for AWS

The device should include credentials to allow logging into a CloudWatch log 
stream.

The `~/.aws/config` should include the `[default]` section to point out the
correct region for the CloudWatch target. Alternatively, you can specify, 
for example, `AWS_PROFILE` environment variable among others. 
See [AWS documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) for details. 

```ini
[default]
output = json
region = eu-central-1
```

By default, the credentials are found in `~/.aws/credentials`, and the 
location can be overridden with `AWS_SHARED_CREDENTIALS_FILE` environment 
variable.

Example `/home/pi/.aws/credentials` below.

```ini
[default]
aws_access_key_id=foo
aws_secret_access_key=bar
```

## Fetching the logs from CloudWatch

In the following example we gather all logs from log stream with names 
starting with `example` from the log group `EXAMPLE-LOG-GROUP` downloading them to files in  
`output-log-dir`.

This method reflects the state of the device logs exactly, but can be heavy
with lots of stream or log entries. Use `--interval` command-line option to
limit the amount of data, or specify a narrow time window with `--from` and 
`--to`. 

```shell script
AWS_SHARED_CREDENTIALS_FILE=creds log-download EXAMPLE-LOG-GROUP example output-log-dir
```
