# AWS_Flowlog_Graph Utilities

Data Acquisition

Needed:

* hour or two worth of vpc flowlog data, be sure logs include the [optional](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-log-fields) 
with *tcp-flags* fields (**version 3 fields** or higher ).


* AWS resource descriptions on all resources on VPC fron the same time period. **IMPORTANT** 

the script [download_configs.py](download_configs.py) can be used download the AWS info, and save the data into the folder FlowLogs/\<acct-num\>-\<region\>

Before running be sure to edit the script and change the following [config vars](download_configs.py#L39-L42)

https://github.com/evilpete/AWS_Flowlog_Graph/blob/504a4a83538324e7d3e1c0b84c3f9c177dcc5332/Util/download_configs.py#L39-L42

script will record:

        describe_auto_scaling_groups describe_auto_scaling_instances
        describe_cache_clusters describe_db_cluster_endpoints
        describe_db_instances describe_egress_only_internet_gateways describe_endpoints
        describe_file_systems describe_flow_logs describe_hosts describe_instances
        describe_internet_gateways describe_listeners describe_load_balancer (elbv2)
        describe_load_balancers describe_local_gateways describe_log_streams
        describe_mount_targets describe_nat_gateways describe_network_interfaces
        describe_subnets describe_target_groups describe_target_health
        describe_transit_gateways describe_vpc_endpoint_connections describe_vpc_endpoints



