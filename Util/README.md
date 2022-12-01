# AWS_Flowlog_Graph Utilities

Data Acquisition

Needed:

hour or two worth of vpc flowlog data with [optional](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-log-records) 
with tcp-flags fields (version 3 fields or higher ).


AWS resource descriptions fron the same tile period

the script [download_configs.py](download_configs.py) can be used download the AWS info, it will save the data into the folder FlowLogs/<acct-num>-<region>

