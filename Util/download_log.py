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

aws_vpc = 'vpc-00000000000000001'
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
        print("\t+get_elb", len(resp['LoadBalancerDescriptions']), len(elbs))

        # if resp['ResponseMetadata']['RetryAttempts'] > 0:
        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

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

        print("\t+get_elbv2", len(resp['LoadBalancers']), len(elbs))
        full_resp.extend(elbs)

        # if resp['ResponseMetadata']['RetryAttempts'] > 0:
        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

#        targ_grps_rep = elbv2_client.describe_target_groups(LoadBalancerArn=lb['LoadBalancerArn'])
#        target_groups_by_elb[lb['LoadBalancerArn']] = listeners_rep['TargetGroups']

def get_listeners(balv2_rep):
    full_resp = {}
    throttle = False
    print("Listeners")
    for lb in balv2_rep:
        paginator = elbv2_client.get_paginator("describe_listeners")
        response_iterator = paginator.paginate(LoadBalancerArn=lb['LoadBalancerArn'])
        # resp = elbv2_client.describe_listeners(LoadBalancerArn=lb['LoadBalancerArn'])
        for resp in response_iterator:

            print("\t", lb['LoadBalancerName'], len(resp['Listeners']))
            full_resp[lb['LoadBalancerArn']] = resp['Listeners']

            if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
                print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
                throttle = True

            if throttle:
                time.sleep(0.2)

    print("listeners", len(full_resp))
    return full_resp

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

def get_target_health(targ_groups_rep):
    full_resp = {}
    throttle = False
    tgl = [y['TargetGroupArn'] for x in targ_groups_rep for y in targ_groups_rep[x]]
    print("tdescribe_target_health")
    for t in tgl:
        # no response_iterator for describe_target_health
        resp = elbv2_client.describe_target_health(TargetGroupArn=t)

        print("\t", t, len(resp['TargetHealthDescriptions']))
        full_resp[t] = resp['TargetHealthDescriptions']

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata']['RetryAttempts'])
            throttle = True

        if throttle:
            time.sleep(0.2)

    #print("target_group", len(full_resp))
    return full_resp

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

# list_functions Functions
def get_lambda_resource(func, index):
    full_resp = []
    throttle = False
    paginator = lambda_client.get_paginator(func)
    response_iterator = paginator.paginate()
    for resp in response_iterator:

        full_resp.extend(resp[index])

        if resp.get('ResponseMetadata', {}).get('RetryAttempts', 0) > 0:
            print("\tRetryAttempts:", resp['ResponseMetadata'].get('RetryAttempts', '?'))
            throttle = True

        if throttle:
            time.sleep(0.2)

    return full_resp

# "describe_network_interfaces", "NetworkInterfaces"
# "describe_hosts", "Hosts"
# "describe_subnets", "Subnets"
# "describe_flow_logs", "FlowLogs"
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


# "describe_cache_clusters", "CacheClusters"
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
# def get_dynamodb_endpoints():
#     full_resp = []
#     resp = dynamodb_client.describe_endpoints()
#     while resp:
#         full_resp.extend(resp['Endpoints'])
#
#         if 'NextMarker' in resp:
#             resp = dynamodb_client.describe_endpoints(Marker=resp['NextMarker'])
#         else:
#             break
#     return full_resp

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
    fname = "{}/{}.json".format(dirn, n)
    # fname = "{}/{}_{}.json".format(filen, n, logGroup)
    print("Save", fname)
    with open(fname, 'w') as qfd:
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

        with open(filen, 'w') as fd:

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
                    print("\tlast  tm = {} {} {:0.3f} min".format(
                        lts, ltm, ts_diff))

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
                print("\t{:d}:{:02d}:{:02d}".format(h, m, s))
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
    dirn = "FlowLogs/{}".format(LogDir)
    if not os.path.isdir(dirn):
        os.mkdir(dirn)

    x = f"{dirn}/flowlogs"
    if not os.path.exists(x):
        os.mkdir(x)

    x = f"FlowLogs/{aws_profile}"
    if not os.path.exists(x):
        os.symlink(LogDir, x)


    with open(f"{dirn}/info.txt", 'w') as ffd:
        print(f"Account: {acct}", file=ffd)
        print(f"Account Alias: {acctname}", file=ffd)
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mytime)), "GMT", file=ffd)
        print(time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(mytime)), file=ffd)


    # create Sessions
    log_client = session.client('logs', config=boto_config)
    ec2_client = session.client('ec2', config=boto_config)
    elbv2_client = session.client('elbv2', config=boto_config)
    elb_client = session.client('elb', config=boto_config)
    asg_client = session.client('autoscaling', config=boto_config)
    rds_client = session.client('rds', config=boto_config)
    lambda_client = session.client('lambda', config=boto_config)
    elasticache_client = session.client('elasticache', config=boto_config)
    # dynamodb_client = session.client('dynamodb', config=boto_config)


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

#    print("\nDynamodb Endpoints")
#    dynamodb_endpoints_rep = get_dynamodb_endpoints()
#    print("dynamodb_endpoints", len(dynamodb_endpoints_rep))
#    qdump('dynamodb_endpoints', dynamodb_endpoints_rep)

    print("\nLocalGateways")
    local_gateways_rep = get_ec2_resource("describe_local_gateways", "LocalGateways")
    print("LocalGateways", len(local_gateways_rep))
    qdump('local_gateways', local_gateways_rep)

    print("\nLocalGateway Virtual Interfaces")
    local_gateway_virtual_interfaces_rep = get_ec2_resource("describe_local_gateway_virtual_interfaces",
                                                            "LocalGatewayVirtualInterfaces")
    print("local_gateway_virtual_interfaces", len(local_gateway_virtual_interfaces_rep))
    qdump('local_gateway_virtual_interfaces', local_gateway_virtual_interfaces_rep)

    print("\nlambda-functions")
    lambda_funct_rep = get_lambda_resource("list_functions", "Functions")
    # if vpc_id:
    #     lambda_funct_rep = [l for l in lambda_funct_rep if lb['VpcConfig']['VpcId'] == vpc_id]
    print("lambda-functions", len(lambda_funct_rep))
    qdump('lambda_functions', lambda_funct_rep)

    print("\nEc2 Instances")
    instances_rep = get_instances(vpc_filter)
    # instances_rep = ec2_client.describe_instances(Filters=vpc_filter)
    print('instances_rep', len(instances_rep))
    qdump('instances', instances_rep)

    print("\nRds Instances")
    rds_instances_rep = get_rds_resource("describe_db_instances", "DBInstances")
    print('rds_instances_rep', len(rds_instances_rep))
    qdump('rds_instances', rds_instances_rep)


    print("\nRds Cluster Endpoints")
    rds_cluster_endpoints_rep = get_rds_resource("describe_db_cluster_endpoints", "DBClusterEndpoints")
    print('rds_cluster_endpoints', len(rds_cluster_endpoints_rep))
    qdump('rds_cluster_endpoints', rds_cluster_endpoints_rep)


    print("\nElasticache cache_clusters")
    elasticache_cache_clusters_rep = get_elasticache_resource("describe_cache_clusters", "CacheClusters")
    print('elasticache_cache_clusters', len(elasticache_cache_clusters_rep))
    qdump('elasticache_cache_clusters', elasticache_cache_clusters_rep)

    print("\nASG Instances")
    asg_instances_rep = get_asg_resource("describe_auto_scaling_instances", "AutoScalingInstances")
    print('asg_instances_rep', len(asg_instances_rep))
    qdump('auto_scaling_instances', asg_instances_rep)

    print("\nASG")
    asg_rep = get_asg_resource("describe_auto_scaling_groups", "AutoScalingGroups")
    print('asg_rep', len(asg_rep))
    qdump('auto_scaling_groups', asg_rep)

    if no_vpc_filter:
        elb_filter = []
    else:
        elb_filter = [aws_vpc]

    print("\nElbv2")
    load_balv2_rep = get_elbv2(elb_filter)
    print('load_balv2_rep', len(load_balv2_rep))
    qdump('elbv2', load_balv2_rep)

    print("\nElb")
    load_bal_rep = get_elb(elb_filter)
    print('load_bal_rep', len(load_bal_rep))
    qdump('elb', load_bal_rep)

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
