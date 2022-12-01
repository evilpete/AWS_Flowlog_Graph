# AWS_Flowlog_Graph Utilities

Data Acquisition

Needed:

* hour or two worth of vpc flowlog data, be sure logs include the (optional](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-log-fields) 
with *tcp-flags* fields (**version 3 fields** or higher ).


* AWS resource descriptions fron the same tile period

the script [download_configs.py](download_configs.py) can be used download the AWS info, it will save the data into the folder FlowLogs/<acct-num>-<region\>

Befor running be sure to edit the script and change the following congof vars

```python 
    aws_vpc = 'vpc-XXXXXXXXXXXXXXXXX'
    aws_profile = 'default'
    aws_region = 'us-west-2'
```
