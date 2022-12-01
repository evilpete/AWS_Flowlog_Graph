# AWS_Flowlog_Graph Utilities

Data Acquisition

Needed:

* hour or two worth of vpc flowlog data, be sure logs include the [optional](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-log-fields) 
with *tcp-flags* fields (**version 3 fields** or higher ).


* AWS resource descriptions fron the same tile period

the script [download_configs.py](download_configs.py) can be used download the AWS info, and save the data into the folder FlowLogs/\<acct-num\>-\<region\>

Before running be sure to edit the script and change the following [config vars](download_configs.py#L39-L42)

https://github.com/evilpete/AWS_Flowlog_Graph/blob/504a4a83538324e7d3e1c0b84c3f9c177dcc5332/Util/download_configs.py#L39-L42
