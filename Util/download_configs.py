#!/usr/bin/python3


#
#   Download AWS info into the folder FlowLogs/<acct-num>-<region>
#   eg: FlowLogs/ 123456789012-west-2/
#
#   To use:
#
#   edit values for
#       aws_vpc = 'vpc-XXXXXXXXXXXXXXXXX'
#       aws_profile = 'default'
#       aws_region = 'us-west-2'


# describe_auto_scaling_groups describe_auto_scaling_instances describe_cache_clusters
# describe_db_cluster_endpoints describe_db_instances describe_egress_only_internet_gateways
# describe_endpoints describe_flow_logs describe_hosts describe_instances
# describe_internet_gateways describe_listeners describe_load_balancer (elbv2)
# describe_load_balancers describe_local_gateways describe_log_streams
# describe_nat_gateways describe_network_interfaces describe_subnets
# describe_target_groups describe_target_health describe_transit_gateways
# describe_vpc_endpoint_connections describe_vpc_endpoints
# # describe_file_systems describe_mount_targets


# pylint: disable=invalid-name,missing-function-docstring,missing-class-docstring,missing-module-docstring

import os
import sys
import time
import json
import datetime
# import socket
# import re
import pprint

import boto3
from botocore.config import Config

# from pygraphviz import *

keep_file = False
max_line = 50000
skip_strm = 50

no_vpc_filter = True

aws_vpc = None
aws_profile = 'default'
aws_region = 'us-west-2'

# aws_profile = 'duchess'  # 'default'
# aws_vpc = "vpc-0122d63674ae5ffb6"
# aws_region = 'us-west-2'

# aws_profile = 'duchess'  # 'default'
# aws_vpc = "vpc-0864337a94cba8997"
# aws_region = 'us-west-1'

#logGroup = 'vpc-flow-logs'
logGroup = 'FlowLogs'

boto_config = Config(
    retries={
        'max_attempts': 20,
        'mode': 'adaptive',   # legacy (default), standard, and adaptive
    }
)

# expressed as the number of milliseconds after Jan 1, 1970 00:00:00 UTC
log_days = 0
log_hours = 0
log_minutes = 0 #60
log_duration = int((3600 * 24 * log_days) + (3600 * log_hours) + (60 * log_minutes))

# describe_load_balancers
def get_elb(vpc_list):
    full_resp = []
    throttle = False
    paginator = elb_client.get_paginator("describe_load_balancers")
    response_iterator = paginator.paginate()

    for resp in response_iterator:

        # pprint.pprint(resp)
        if vpc_list:
            elbs = [lb for lb in resp['LoadBalancerDescriptions'] if lb['VPCId'] in vpc_list]
        else:
            elbs = resp['LoadBalancerDescriptions']

        full_resp.extend(elbs)
        # print("\t+get_elb", len(resp['LoadBalancerDescriptions']), len(elbs))

        # if resp['ResponseMetadata']['RetryAttempts'] > 0:
        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# describe_load_balancer (elbv2)
def get_elbv2(vpc_list):
    full_resp = []
    throttle = False
    paginator = elbv2_client.get_paginator("describe_load_balancers")
    response_iterator = paginator.paginate()
    # resp = elbv2_client.describe_load_balancers()
    for resp in response_iterator:
        # pprint.pprint(resp)
        if vpc_list:
            elbs = [lb for lb in  resp['LoadBalancers'] if lb['VpcId'] in vpc_list]
        else:
            elbs = resp['LoadBalancers']

        # print("\t+get_elbv2", len(resp['LoadBalancers']), len(elbs))
        full_resp.extend(elbs)

        # if resp['ResponseMetadata']['RetryAttempts'] > 0:
        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# describe_listeners
#        targ_grps_rep = elbv2_client.describe_target_groups(LoadBalancerArn=lb['LoadBalancerArn'])
#        target_groups_by_elb[lb['LoadBalancerArn']] = listeners_rep['TargetGroups']
def get_listeners(balv2_rep):
    full_resp = {}
    throttle = False
    # print("Listeners")
    for lb in balv2_rep:
        paginator = elbv2_client.get_paginator("describe_listeners")
        response_iterator = paginator.paginate(LoadBalancerArn=lb['LoadBalancerArn'])
        # resp = elbv2_client.describe_listeners(LoadBalancerArn=lb['LoadBalancerArn'])
        for resp in response_iterator:

            # print("\t", lb['LoadBalancerName'], len(resp['Listeners']))
            full_resp[lb['LoadBalancerArn']] = resp['Listeners']

            if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
                print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
                throttle = True

            if throttle:
                time.sleep(0.2)

    print("Listeners", len(full_resp))
    return full_resp

# describe_target_groups
def get_target_groups(balv2_rep):
    full_resp = {}
    throttle = False
    print("describe_target_groups")
    for lb in balv2_rep:
        paginator = elbv2_client.get_paginator("describe_target_groups")
        response_iterator = paginator.paginate(LoadBalancerArn=lb['LoadBalancerArn'])
        # resp = elbv2_client.describe_target_groups(LoadBalancerArn=lb['LoadBalancerArn'])

        for resp in response_iterator:
            print("\t" + lb['LoadBalancerName'], len(resp['TargetGroups']))
            full_resp[lb['LoadBalancerName']] = resp['TargetGroups']

            if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
                print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
                throttle = True

            if throttle:
                time.sleep(0.2)

    #print("target_group", len(full_resp))
    return full_resp

# describe_target_health
def get_target_health(targ_groups_rep):
    full_resp = {}
    throttle = False
    tgl = [y['TargetGroupArn'] for x in targ_groups_rep for y in targ_groups_rep[x]]
    # print("describe_target_health")
    for t in tgl:
        # no response_iterator for describe_target_health
        resp = elbv2_client.describe_target_health(TargetGroupArn=t)

        # print("\t", t, len(resp['TargetHealthDescriptions']))
        full_resp[t] = resp['TargetHealthDescriptions']

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata']['RetryAttempts'])
            throttle = True

        if throttle:
            time.sleep(0.2)

    #print("target_group", len(full_resp))
    return full_resp

def get_elbv2_tags(arns):
    full_resp = []
    throttle = False
    paginator = elbv2_client.get_paginator("describe_tags")
    response_iterator = paginator.paginate(ResourceArns=arns)
    for resp in response_iterator:

        full_resp.extend(resp["TagDescriptions"])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# describe_instances
def get_instances(ffilter=None):
    if ffilter is None:
        ffilter = []
    full_resp = []
    throttle = False
    paginator = ec2_client.get_paginator("describe_instances")
    response_iterator = paginator.paginate(Filters=ffilter)
    # resp = ec2_client.describe_instances(Filters=ffilter, MaxResults=500)
    # while resp:
    for resp in response_iterator:

        for r in resp['Reservations']:
            full_resp.extend(r['Instances'])

        # if resp['ResponseMetadata']['RetryAttempts'] > 0:
        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata']['RetryAttempts'])
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# 
# describe_workspaces
def get_workspaces_resource(func, index):
    # ffilter = ffilter or []
    full_resp = []
    throttle = False
    paginator = workspaces_client.get_paginator(func)
    response_iterator = paginator.paginate()
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True
        if throttle:
            time.sleep(0.2)

    return full_resp

# describe_auto_scaling_instances AutoScalingInstances
# describe_auto_scaling_groups AutoScalingGroups
def get_asg_resource(func, index, ffilter=None):
    ffilter = ffilter or []
    full_resp = []
    throttle = False
    paginator = asg_client.get_paginator(func)
    response_iterator = paginator.paginate()
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True
        if throttle:
            time.sleep(0.2)

    return full_resp

# list_functions Functions (lambda)
def get_lambda_resource(func, index):
    full_resp = []
    throttle = False
    paginator = lambda_client.get_paginator(func)
    response_iterator = paginator.paginate() # MasterRegion=aws_region)
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# describe_network_interfaces", "NetworkInterfaces"
# describe_hosts", "Hosts"
# describe_subnets", "Subnets"
# describe_flow_logs", "FlowLogs"
# describe-vpc-endpoints  VpcEndpoints
# describe_internet_gateways InternetGateways
def get_ec2_resource(func, index, ffilter=None):
    ffilter = ffilter or []
    full_resp = []
    throttle = False
    paginator = ec2_client.get_paginator(func)
    response_iterator = paginator.paginate(Filters=ffilter)
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp


# describe_cache_clusters", "CacheClusters"
def get_elasticache_resource(func, index, ffilter=None):
    ffilter = ffilter or []
    full_resp = []
    throttle = False
    paginator = elasticache_client.get_paginator(func)
    response_iterator = paginator.paginate()
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# describe_endpoints Endpoints
def get_dynamodb_endpoints():
    full_resp = []
    resp = dynamodb_client.describe_endpoints()
    while resp:
        full_resp.extend(resp['Endpoints'])

        if 'NextMarker' in resp:
            resp = dynamodb_client.describe_endpoints(Marker=resp['NextMarker'])
        else:
            break
    return full_resp


def get_elbv2_resource(func, index, ffilter=None):
    ffilter = ffilter or []
    full_resp = []
    throttle = False
    paginator = elbv2s_client.get_paginator(func)
    response_iterator = paginator.paginate(Filters=ffilter)
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp


def get_redshift_resource(func, index):
    full_resp = []
    throttle = False
    paginator = redshift_client.get_paginator(func)
    response_iterator = paginator.paginate()
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp


def get_rds_resource(func, index, ffilter=None):
    ffilter = ffilter or []
    full_resp = []
    throttle = False
    paginator = rds_client.get_paginator(func)
    response_iterator = paginator.paginate(Filters=ffilter)
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp


# describe_file_systems FileSystems
# describe_mount_targets MountTargets
def get_efs_resource(func, index, fid=None):
    # ffilter = ffilter or []
    full_resp = []
    throttle = False
    paginator = efs_client.get_paginator(func)
    if fid:
        response_iterator = paginator.paginate(FileSystemId=fid)   # Filters=ffilter)
    else:
        response_iterator = paginator.paginate()   # Filters=ffilter)
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# MasterRegion=aws_region
# def _get_lambda_functions():
#     full_resp = []
#     paginator = lambda_client.get_paginator('list_functions')
#     response_iterator = paginator.paginate()
#
#     for resp in response_iterator:
#         full_resp.extend(resp['Functions'])
#     return full_resp


class JSONSetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(list(obj))
            # return dict(_set_object=list(obj))

        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)

def qdump(n, d):
    fname = f"{dirn}/{n}.json"
    # fname = "{}/{}_{}.json".format(filen, n, logGroup)
    print("Save", fname)
    with open(fname, 'w', encoding="utf8") as qfd:
        json.dump(d, qfd, cls=JSONSetEncoder, sort_keys=True, indent=4, separators=(',', ': '))

def write_events(efd, event):
    ev = None
    for ev in event:
        efd.write(ev['message'] + "\n")
    return ev

def next_stream(lgroup=None):

    if lgroup is None:
        lgroup = logGroup

    load_cnt = 0

    log_arg = {
        'logGroupName': lgroup,
        'orderBy': 'LastEventTime',
        'descending': True,
        # 'limit': 50,
    }

    throttle = False
    paginator = log_client.get_paginator('describe_log_streams')
    response_iterator = paginator.paginate(**log_arg)
    for log_streams in response_iterator:

        #print(log_streams)
        load_cnt += 1
        print('describe_log_streams', len(log_streams['logStreams']))

        if log_streams.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", log_streams['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

        if skip_strm < load_cnt:
            print("skip_strm < load_cnt", skip_strm, load_cnt)
        #     print("next stream set")
        #     continue

        for logStm in log_streams['logStreams']:
            if logStm['storedBytes'] == 0:
                continue
            yield logStm


def get_flowlog_streams(log_grp=None):    # pylint: disable=too-many-locals, too-many-statements
    instances_name_list = [i['NetworkInterfaceId'] for i in net_inter_rep]

    if log_grp is None:
        log_grp = logGroup

    startTime = (mytime - log_duration) * 1000
    print("log_duration =", log_duration/60, "min")
    print('startTime =', startTime, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(startTime/1000)))
    print('instances_name_list:', len(instances_name_list))


    print("Sleep 5..")
    time.sleep(5)

    file_cnt = 0

    print("Starting Log Streams")
    for sl in next_stream(log_grp):

        ls = sl['logStreamName']
        ni_name = ls[:-4]

        file_cnt += 1

        if ni_name not in instances_name_list:
            print("\nSKIP not in list", ni_name, file_cnt)
            continue

        lets = sl.get('lastEventTimestamp', 0)
        letm = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(lets/1000))
        if sl['storedBytes'] == 0:
            print("\nSKIP zeroBytes", ni_name, file_cnt, letm)
            continue

        if lets and startTime > lets:
            print("\nSKIP TimeStamp", ni_name, file_cnt, letm)
            continue

        filen = f"{dirn}/flowlogs/{ni_name}"

        if keep_file and os.path.exists(filen):
            print("\nSKIP Exist    ", ni_name, file_cnt, letm)
            continue

        # print("\nfilen = ", filen, file_cnt)
        # print("storedBytes = ", sl['storedBytes'])


        kargs = {
            'logGroupName': log_grp,
            'logStreamName': ls,
            'limit': 10000,
            'startFromHead': False,
        }

        if log_duration:
            kargs['startTime'] = startTime

        with open(filen, 'w', encoding="utf8") as fd:

            line_count = 0
            nextTok = True
            currTok = False
            start_tm = None
            lts = 0

            print('\n', ni_name, file_cnt, letm)
            print('\tstoredBytes =', sl['storedBytes'])

            while nextTok != currTok:

                currTok = nextTok
                log_events = log_client.get_log_events(**kargs)
                # if 'startTime' in kargs:
                #     del kargs['startTime']

                nextTok = log_events['nextForwardToken']
                kargs['nextToken'] = nextTok

                x = len(log_events['events'])
                line_count += x
                #lts = 0

                if max_line and line_count > max_line:
                    print("\tmax_line", line_count, '>', max_line)
                    currTok = nextTok
                    continue

                # print("x =", x)
                # print('currTok = nextTok',currTok, nextTok)

                if x:
                    print("\twriting", x, line_count)

                    sts = log_events['events'][0].get('timestamp', 1000)
                    stm = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(sts/1000))
                    print("\tstart tm =", sts, stm)
                    if start_tm is None:
                        start_tm = sts

                    lev = write_events(fd, log_events['events'])

                    lts = lev.get('timestamp', 1000)
                    ltm = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(lts/1000))
                    ts_diff = (lts - sts) / 60000.0
                    print(f"\tlast  tm = {lts} {ltm} {ts_diff:0.3f} min")

                # print('\tnextBackwardToken', log_events['nextBackwardToken'])
                # print('\tcurrTok          ', currTok)
                # print('\tnextForwardToken ', nextTok)
            #else:
            if start_tm:
                # print("lts - start_tm", lts, start_tm)
                tm_len = (lts - start_tm) / 1000
                # print('tm_len', tm_len)
                m, s = divmod(tm_len, 60)
                # print('m s', m, s)
                h, m = divmod(m, 60)
                # print('h m', h, m)
                print(f"\t{h:d}:{m:02d}:{s:02d}")
            if line_count == 0:
                print("\tWritten Lines", line_count)
                # os.remove(filen)
            print("\tDone")
            # print('sleep 5')
            # time.sleep(5)

        # print("x=", x)
        # print("line_count=", line_count)


# botocore.errorfactory.AccessDeniedException: An error occurred (AccessDeniedException
if __name__ == '__main__':

    mytime = int(time.time())
    print("mytime :", mytime, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mytime)))

    session = boto3.session.Session(region_name=aws_region, profile_name=aws_profile)
    acct = session.client('sts').get_caller_identity().get('Account')

    xx = boto3.client('iam').list_account_aliases()['AccountAliases']
    if xx:
        acctname = xx[0]
    else:
        acctname = ""

    print("acct:", acct)

    LogDir = f"{acct or '000000'}-{aws_region[3:]}"

    if not os.path.isdir("FlowLogs"):
        os.mkdir("FlowLogs")
    dirn = f"FlowLogs/{LogDir}"
    if not os.path.isdir(dirn):
        os.mkdir(dirn)

    x = f"{dirn}/flowlogs"
    if not os.path.exists(x):
        os.mkdir(x)

    x = f"FlowLogs/{aws_profile}"
    if not os.path.exists(x):
        os.symlink(LogDir, x)


    with open(f"{dirn}/info.txt", 'w', encoding="utf8") as ffd:
        print(f"Account: {acct}", file=ffd)
        print(f"Account Alias: {acctname}", file=ffd)
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mytime)), "GMT", file=ffd)
        print(time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(mytime)), file=ffd)


    # create Sessions
    log_client = session.client('logs', config=boto_config)
    ec2_client = session.client('ec2', config=boto_config)
    ecs_client = session.client('ecs', config=boto_config)
    elbv2_client = session.client('elbv2', config=boto_config)
    elb_client = session.client('elb', config=boto_config)
    asg_client = session.client('autoscaling', config=boto_config)
    rds_client = session.client('rds', config=boto_config)
    # lambda_client = session.client('lambda', config=boto_config)
    lambda_client = None
    elasticache_client = session.client('elasticache', config=boto_config)
    efs_client = session.client('efs', config=boto_config)
    # efs_client = None
    dynamodb_client = session.client('dynamodb', config=boto_config)
    # dynamodb_client = None
    # workspaces_client = session.client('workspaces', config=boto_config)
    workspaces_client = None
    # redshift_client = session.client('redshift', config=boto_config)
    redshift_client = None

    print("\nVpcs")
    if aws_vpc is None or no_vpc_filter:
        vpc_filter = []
    else:
        vpc_filter = [{'Name': 'vpc-id', 'Values': [aws_vpc]}]
    vpc_rep = ec2_client.describe_vpcs(Filters=vpc_filter)['Vpcs']
    print("\tVpcs: ", len(vpc_rep))
    qdump('vpc', vpc_rep)
    if aws_vpc is None:
        if len(vpc_rep) == 1:
            aws_vpc = vpc_rep[0]['VpcId']
            print("Using VpcId", aws_vpc)

        aws_vpc_list = [v['VpcId'] for v in vpc_rep]
    else:
        aws_vpc_list = [aws_vpc]


    print("\nNetwork Interfaces")
    net_inter_rep = get_ec2_resource("describe_network_interfaces",
                                     "NetworkInterfaces")   # vpc_filter
    print("network_interfaces", len(net_inter_rep))
    qdump('network_interfaces', net_inter_rep)

    print("\nHosts")
    host_rep = get_ec2_resource("describe_hosts", "Hosts")
    print("Hosts", len(host_rep))
    qdump('hosts', host_rep)

    print("\nVpcEndpoints")
    vpc_endpoint_rep = get_ec2_resource("describe_vpc_endpoints", "VpcEndpoints")  # vpc_filter
    print("VpcEndpoints", len(vpc_endpoint_rep))
    qdump('vpc_endpoints', vpc_endpoint_rep)

    print("\nVpcEndpointConnections")
    vpc_endpoint_connections_rep = get_ec2_resource("describe_vpc_endpoint_connections", "VpcEndpointConnections")
    print("vpc_endpoint_connections", len(vpc_endpoint_connections_rep))
    qdump('vpc_endpoint_connections', vpc_endpoint_connections_rep)

    print("\nInternetGateways")
    internet_gateways_rep = get_ec2_resource("describe_internet_gateways", "InternetGateways")
    print("InternetGateways", len(internet_gateways_rep))
    qdump('internet_gateways', internet_gateways_rep)

    print("\nEgressOnlyInternetGateways")
    egress_only_gateways_rep = get_ec2_resource("describe_egress_only_internet_gateways",
                                                "EgressOnlyInternetGateways", vpc_filter)
    print("EgressOnlyInternetGateways", len(egress_only_gateways_rep))
    qdump('egress_only_gateways', egress_only_gateways_rep)

    print("\nNatGateways")
    nat_gateways_rep = get_ec2_resource("describe_nat_gateways", "NatGateways", vpc_filter)
    print("NatGateways", len(nat_gateways_rep))
    qdump('nat_gateways', nat_gateways_rep)

    print("\nSubnets")
    subnets_rep = get_ec2_resource("describe_subnets", "Subnets", vpc_filter)
    print("Subnets", len(subnets_rep))
    qdump('subnets', subnets_rep)

    print("\nTransitGateways")
    transit_gateways_rep = get_ec2_resource("describe_transit_gateways", "TransitGateways")
    print("TransitGateways", len(transit_gateways_rep))
    qdump('transit_gateways', transit_gateways_rep)

    print("\nEc2 describe_tags")
    ec2_describe_tags_rep = get_ec2_resource("describe_tags", "Tags")  # vpc_filter
    print("Tags", len(ec2_describe_tags_rep))
    qdump('ec2_describe_tags', ec2_describe_tags_rep)


    if dynamodb_client:
        print("\nDynamodb Endpoints")
        dynamodb_endpoints_rep = get_dynamodb_endpoints()
        print("dynamodb_endpoints", len(dynamodb_endpoints_rep))
        qdump('dynamodb_endpoints', dynamodb_endpoints_rep)

    print("\nLocalGateways")
    local_gateways_rep = get_ec2_resource("describe_local_gateways", "LocalGateways")
    print("LocalGateways", len(local_gateways_rep))
    qdump('local_gateways', local_gateways_rep)

    print("\nLocalGateway Virtual Interfaces")
    local_gateway_virtual_interfaces_rep = get_ec2_resource("describe_local_gateway_virtual_interfaces",
                                                            "LocalGatewayVirtualInterfaces")
    print("local_gateway_virtual_interfaces", len(local_gateway_virtual_interfaces_rep))
    qdump('local_gateway_virtual_interfaces', local_gateway_virtual_interfaces_rep)


    print(f"aws_vpc={aws_vpc}")
    print(f"aws_vpc_list={aws_vpc_list}")

    print("\nlambda-functions")
    lambda_functions_rep=[]
    if lambda_client:
        lambda_funct_rep = get_lambda_resource("list_functions", "Functions")
        # if vpc_id:
        #     lambda_funct_rep = [l for l in lambda_funct_rep if lb['VpcConfig']['VpcId'] == vpc_id]

        print("lambda-functions_rep", len(lambda_funct_rep))
        for la in lambda_funct_rep:
            if 'VpcConfig' not in la:
                continue
            try:
                lam_vpc = la['VpcConfig']['VpcId']
            except KeyError as _e:
                print(_e)
                pprint.pprint(la)
                sys.exit()
            if lam_vpc in aws_vpc_list:
                lambda_functions_rep.append(la)
    print("lambda-functions", len(lambda_functions_rep))
    qdump('lambda_functions', lambda_functions_rep)

    print("\nlambda-functions tags")
    lambda_tags = {}
    for lf in lambda_functions_rep:
        rtarg = lf['FunctionArn']
        lf_list = lambda_client.list_tags(Resource=rtarg)
        lambda_tags[rtarg] = lf_list.get("Tags", [])
    qdump('lambda_tags', lambda_tags)

    print("\nEc2 Instances")
    ec2_instances_rep = get_instances(vpc_filter)
    # ec2_instances_rep = ec2_client.describe_instances(Filters=vpc_filter)
    print('ec2_instances_rep', len(ec2_instances_rep))
    qdump('ec2_instances', ec2_instances_rep)

    ecs_clusters_rep = []
    if ecs_client:
        print('get ecs_clusters')
        paginator = ecs_client.get_paginator('list_clusters')

        response_iterator = paginator.paginate(PaginationConfig={'PageSize':50})
        for each_page in response_iterator:
            clusterArns = each_page['clusterArns']
            print(f"clusterArns = {len(clusterArns)}")
            ecs_response = ecs_client.describe_clusters(clusters=clusterArns, include=['TAGS'])
            ecs_clusters_rep.extend(ecs_response.get('clusters', []))
    else:
        print('skip ecs_clusters')
    print('ecs_clusters_rep', len(ecs_clusters_rep))
    qdump('ecs_clusters', ecs_clusters_rep)


    if redshift_client:
        print("\Redshift")
        # redshift_clusters_rep = get_redshift_resource("describe_clusters", "Clusters")
        redshift_clusters_rep = redshift_client.describe_clusters().get("Clusters", [])
        print('redshift_clusters_rep', len(redshift_clusters_rep))
        qdump('redshift_clusters', redshift_clusters_rep)

        print("\Redshift Tags")
        # get_redshift_resource("describe_tags", "TaggedResources")
        redshift_tags_rep = redshift_client.describe_tags().get("TaggedResources", [])
        print('redshift_tags_rep', len(redshift_tags_rep))
        qdump('redshift_tags', redshift_tags_rep)
    else:
        print('skip Redshift')

    if workspaces_client:
        print("\nWorkspaces")
        workspaces_rep = get_workspaces_resource("describe_workspaces", "Workspaces")
        print('workspaces_rep', len(workspaces_rep))
        qdump('workspaces_rep', workspaces_rep)

        workspaces_tags = {}
        for ws in workspaces_rep:
            WsID = ws['WorkspaceIds']
            ws_tag_list = efs_client.list_tags_for_resource(ResourceId=WsID)
            workspaces_tags[WsID] = ws_tag_list.get("Tags", [])
        qdump('workspaces_tags', workspaces_tags)
    else:
        print('skip Workspaces')

    if efs_client:
        print("\nEFS FileSystems")
        efs_filesystems_rep = get_efs_resource("describe_file_systems", "FileSystems")
        print('efs_filesystems_rep', len(efs_filesystems_rep))
        qdump('efs_filesystems', efs_filesystems_rep)

        if efs_filesystems_rep:
            print("\nEFS MountTargets")
            for mt in efs_filesystems_rep:
                efs_mounttargets_rep = get_efs_resource("describe_mount_targets", "MountTargets",
                    fid=mt['FileSystemId'])
            print('efs_mounttargets_rep', len(efs_mounttargets_rep))
            qdump('efs_mountTargets', efs_mounttargets_rep)

        efs_tags = {}
        for mt in efs_filesystems_rep:
            FsID = mt['FileSystemId']
            fs_tag_list = efs_client.list_tags_for_resource(FileSystemId=FsID)
            efs_tags[FsID] = fs_tag_list.get("Tags", [])
        qdump('efs_mountTargets_tags', efs_tags)
    else:
        print('skip EFS FileSystems')

    if rds_client:
        print("\nRds Instances")
        rds_instances_rep = get_rds_resource("describe_db_instances", "DBInstances")
        print('rds_instances_rep', len(rds_instances_rep))
        qdump('rds_instances', rds_instances_rep)

        print("\nRds Cluster Endpoints")
        rds_cluster_endpoints_rep = get_rds_resource("describe_db_cluster_endpoints", "DBClusterEndpoints")
        print('rds_cluster_endpoints', len(rds_cluster_endpoints_rep))
        qdump('rds_cluster_endpoints', rds_cluster_endpoints_rep)

        rds_tags = {}
        for db in rds_instances_rep:
            ttarg = db['DBInstanceIdentifier']
            t_list = rds_client.list_tags_for_resource(ResourceId=ttarg)
            rds_tags[ttarg] = t_list.get("Tags", [])
        qdump('rds_instances_tags', rds_tags)
    else:
        print('skip RDS')

    if elasticache_client:
        print("\nElasticache cache_clusters")
        elasticache_cache_clusters_rep = get_elasticache_resource("describe_cache_clusters", "CacheClusters")
        print('elasticache_cache_clusters', len(elasticache_cache_clusters_rep))
        qdump('elasticache_cache_clusters', elasticache_cache_clusters_rep)

        el_tags = {}
        for et in elasticache_cache_clusters_rep:
            etarg = et['CacheClusterId']
            el_list = elasticache_client.list_tags_for_resource(ResourceName=etarg)
            el_tags[mtarg] = el_list.get("Tags", [])
        qdump('elasticache_cache_clusters_tags', el_tags)
    else:
        print('skip Elasticache')

    print("\nASG Instances")
    asg_instances_rep = get_asg_resource("describe_auto_scaling_instances", "AutoScalingInstances")
    print('asg_instances_rep', len(asg_instances_rep))
    qdump('auto_scaling_instances', asg_instances_rep)

    print("\nASG Tags")
    asg_tags_rep = get_asg_resource("describe_tags", "Tags")
    print('asg_tags_rep', len(asg_tags_rep))
    qdump('auto_scaling_tags', asg_tags_rep)

    print("\nASG")
    asg_rep = get_asg_resource("describe_auto_scaling_groups", "AutoScalingGroups")
    print('asg_rep', len(asg_rep))
    qdump('auto_scaling_groups', asg_rep)

    if no_vpc_filter:
        elb_filter = []
    else:
        elb_filter = aws_vpc_list

    print("\nElbv2")
    load_balv2_rep = get_elbv2(elb_filter)
    print('load_balv2_rep', len(load_balv2_rep))
    qdump('elbv2', load_balv2_rep)

    print("\nElb")
    load_bal_rep = get_elb(elb_filter)
    print('load_bal_rep', len(load_bal_rep))
    qdump('elb', load_bal_rep)

    if load_bal_rep:
        print("\nElb describe_tags")
        arn_list = []
        arn_list.extend([x['LoadBalancerName'] for x in load_bal_rep])
        elb_describe_tags_rep = elb_client.describe_tags(LoadBalancerNames=arn_list).get('TagDescriptions', [])
        print("Elb Tags", len(elb_describe_tags_rep))
        qdump('elb_describe_tags', elb_describe_tags_rep)


    if load_balv2_rep:
        print("\nTarget Groups")
        target_groups_rep = get_target_groups(load_balv2_rep)
        print('target_groups_rep', len(target_groups_rep))
    else:
        target_groups_rep = {}
    qdump('target_groups', target_groups_rep)

    if target_groups_rep:
        print('\nTarget Health')
        target_health_rep = get_target_health(target_groups_rep)
        print('target_health_rep', len(target_health_rep))
    else:
        target_health_rep = {}
    qdump('target_health', target_health_rep)

    if load_balv2_rep:
        print("\nListeners")
        listeners_rep = get_listeners(load_balv2_rep)
        print('listeners_rep', len(listeners_rep))
    else:
        listeners_rep = {}
    qdump('listeners', listeners_rep)

    print("\nElbv2 describe_tags")
    arn_list = []
    arn_list.extend([x['LoadBalancerArn'] for x in load_balv2_rep])
    arn_list.extend([y['ListenerArn'] for x in listeners_rep.values() for y in x])
    arn_list.extend([y['TargetGroupArn'] for x in target_groups_rep.values() for y in x])

    elbv2_describe_tags_rep = elbv2_client.describe_tags(ResourceArns=arn_list)
    print("Elbv2 Tags", len(elbv2_describe_tags_rep))
    qdump('elbv2_describe_tags', elbv2_describe_tags_rep)

# may be broke after this point

    print("\nFlowLog Info")
    # log_filter = [{'Name': 'resource-id', 'Values': [aws_vpc]}]
    log_filter = []
    flog_info_rep = get_ec2_resource("describe_flow_logs", "FlowLogs", log_filter)
    print('flow_log_info_rep', len(flog_info_rep))
    qdump('flow_log_info', flog_info_rep)

    if flog_info_rep and flog_info_rep[0].get('LogGroupName', None):
        log_name = flog_info_rep[0]['LogGroupName']
        log_grp_resp = log_client.describe_log_groups(logGroupNamePrefix=log_name)["logGroups"]
        qdump('log_groups', log_grp_resp)
    else:
        log_grp_resp = []

    if log_grp_resp:
        print("\nlogGroups")
        # pprint.pprint(log_grp_resp)
        for lg in log_grp_resp:
            print(f"\t{lg['logGroupName']}: retentionInDays = {lg['retentionInDays']}")

    print("\n")

    if not flog_info_rep:
        print("No FlowLogs found")
        print(flog_info_rep)
        sys.exit(0)

    if flog_info_rep[0]['LogDestinationType'] == 's3':
        print("LogDestination:", flog_info_rep[0]['LogDestinationType'],
              flog_info_rep[0]['LogDestination'])
    elif flog_info_rep[0]['LogDestinationType'] == 'cloud-watch-logs':
        print("LogDestination:", flog_info_rep[0]['LogDestinationType'],
              flog_info_rep[0]['LogGroupName'])
        logGroup = flog_info_rep[0]['LogGroupName']
        get_flowlog_streams(logGroup)
    else:
        print("LogDestination:", flog_info_rep[0]['LogDestinationType'])


    # LogDestinationType": "s3" cloud-watch-logs'
    # get_flowlog_streams()
