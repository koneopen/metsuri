# Fetching the logs from AWS CloudWatch

## Installing project requirements

Install recent Python (3.8+) from https://www.python.org/downloads/

Using a virtual environment is recommended, it allows mixing and matching packages between different scripts if it becomes necessary

```shell script
% python3 -m venv ve
```

Activate the environment

```shell script
% . ve/bin/activate
```

The above is for unix-like environments. For Windows 
```shell script
C:\> ve\Scripts\activate.bat
```
see https://docs.python.org/3/library/venv.html

```shell script
% pip install metsuri-<version>-py3-none-any.whl
```

## Fetching the logs

Afterwards, you just need to activate the virtual environment and run the script from the package.

Concrete example, download from CloudWatch Logs

```shell script
AWS_SHARED_CREDENTIALS_FILE=creds python log-download test-logs logger1 20201223-logger1-logs
```
