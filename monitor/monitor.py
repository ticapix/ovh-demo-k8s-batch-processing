#!/usr/bin/env python3

import signal
import time
import os
import subprocess
import json
from urllib3.exceptions import ReadTimeoutError
from enum import Flag, auto
import logging
import kubernetes as k8s


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.environ.get("LOGLEVEL", "INFO").upper()))

MANDATORY_ENV_VARS = []

class DaemonState(Flag):
    RUNNING = auto()
    SHOULD_CLOSE = auto()
    MUST_CLOSE = auto()

class GracefulKiller:
    state = DaemonState.RUNNING
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.start_shuting_down)

    def start_shuting_down(self, signum, frame):
        logger.info("I should stop.")
        self.state = DaemonState.SHOULD_CLOSE

    def exit_gracefully(self, signum, frame):
        logger.warning("I really must stop now !")
        self.state = DaemonState.MUST_CLOSE


def count_unscheduled_pod(client):
    count = 0
    for pod in client.list_pod_for_all_namespaces(watch=False).items:
        if 'type' not in pod.metadata.labels:
            continue
        if pod.metadata.labels['type'] != 'batch-processing':
            continue
        if pod.status.phase != 'Pending':
            continue
        if pod.status.conditions is None:
            continue
        if len(pod.status.conditions) == 0:
            continue
        condition = pod.status.conditions[0]
        if condition.type != 'PodScheduled' or  condition.reason != 'Unschedulable':
            logger.info(condition.message)
        count += 1
    return count

def scale_nodepool(api, nodepool_name, delta=0):
    nodepool = k8sapi.get_cluster_custom_object("kube.cloud.ovh.com", "v1alpha1", "nodepools", nodepool_name)
    requested_nodes = nodepool['status']['currentNodes'] + delta
    if not(requested_nodes >= nodepool['spec']['minNodes'] and requested_nodes <= nodepool['spec']['maxNodes']):
        logger.info("Reaching nodepool size limits {}".format(requested_nodes))
        return
    del nodepool['metadata']
    nodepool.update({'metadata': {'name': nodepool_name}})
    del nodepool['status']
    nodepool['spec']['desiredNodes'] = requested_nodes
    logger.info("Scale nodepool to {}".format(requested_nodes))
    res = api.patch_cluster_custom_object("kube.cloud.ovh.com", "v1alpha1", "nodepools", nodepool_name, nodepool)
    print(res)
    assert(res)

def is_nodepool_stable(api, nodepool_name):
    # get nodepool status
    nodepool = k8sapi.get_cluster_custom_object("kube.cloud.ovh.com", "v1alpha1", "nodepools", nodepool_name)
    return nodepool['spec']['desiredNodes'] == nodepool['status']['currentNodes'] and nodepool['spec']['desiredNodes'] == nodepool['status']['availableNodes']


if __name__ == '__main__':
    missing_vars = [var for var in MANDATORY_ENV_VARS if var not in os.environ]
    if len(missing_vars):
        logger.error('missing environment variables: {}'.format(','.join(missing_vars)))
        time.sleep(5)
        os.sys.exit(1)

    logger.info("installing SIGINT and SIGTERM handlers")
    killer = GracefulKiller()
    logger.info("waiting to be drained ...")

    # Configs can be set in Configuration class directly or using helper utility
    if 'KUBECONFIG' in os.environ:
        logger.info('loading config from KUBECONFIG ({})'.format(os.environ['KUBECONFIG']))
        k8s.config.load_kube_config()
    else:
        logger.info('loading config from within the cluster')
        k8s.config.load_incluster_config()

    k8sclient = k8s.client.CoreV1Api()
    k8sapi = k8s.client.CustomObjectsApi()
    # w = k8s.watch.Watch()
    while killer.state == DaemonState.RUNNING:
        time.sleep(5)
        # helper: find correct params by browsing the api with kubectl get --raw '/apis/kube.cloud.ovh.com/v1alpha1/nodepools/compute' |jq .
        unscheduled_pod = count_unscheduled_pod(k8sclient)
        if unscheduled_pod == 0:
            # if node without pod:
            if is_nodepool_stable(k8sapi, 'compute'):
                scale_nodepool(k8sapi, 'compute', -1)
        else:
            logger.debug("There are {} unscheduled pod(s)".format(unscheduled_pod))
            if is_nodepool_stable(k8sapi, 'compute'):
                scale_nodepool(k8sapi, 'compute', +1)
        # measure global activity
        # data = k8sapi.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes", label_selector="nodepool=compute")
        # print(data)
    # w.stop()
    logger.info("End of the program. I was killed gracefully :)")
