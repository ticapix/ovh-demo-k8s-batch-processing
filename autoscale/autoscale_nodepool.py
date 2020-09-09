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
from collections import defaultdict


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.environ.get("LOGLEVEL", "INFO").upper()))

MANDATORY_ENV_VARS = ['NODEPOOL_NAME']


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


def is_pod_assigned_to_nodepool(pod, nodepool_name):
    if not hasattr(pod.spec, 'node_selector'):
        return False
    if pod.spec.node_selector is None:
        return False
    if 'nodepool' not in pod.spec.node_selector:
        return False
    if pod.spec.node_selector['nodepool'] != nodepool_name:
        return False
    return True


def count_unscheduled_pod(client, nodepool_name):
    count = 0
    for pod in client.list_pod_for_all_namespaces(watch=False).items:
        if not is_pod_assigned_to_nodepool(pod, nodepool_name):
            continue
        if pod.status.phase != 'Pending':
            continue
        if pod.status.conditions is None:
            continue
        if len(pod.status.conditions) == 0:
            continue
        condition = pod.status.conditions[0]
        if condition.type != 'PodScheduled' or condition.reason != 'Unschedulable':
            continue
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
    api.patch_cluster_custom_object("kube.cloud.ovh.com", "v1alpha1", "nodepools", nodepool_name, nodepool)


def is_nodepool_stable(api, nodepool_name):
    # get nodepool status
    nodepool = api.get_cluster_custom_object("kube.cloud.ovh.com", "v1alpha1", "nodepools", nodepool_name)
    return nodepool['spec']['desiredNodes'] == nodepool['status']['currentNodes'] and nodepool['spec']['desiredNodes'] == nodepool['status']['availableNodes']


def is_there_empty_node(client, nodepool_name):
    used_nodes = defaultdict(list)
    for pod in client.list_pod_for_all_namespaces(watch=False).items:
        if not is_pod_assigned_to_nodepool(pod, nodepool_name):
            continue
        used_nodes[pod.spec.node_name].append([pod.metadata.namespace, pod.metadata.name])
    if None in used_nodes:  # there are potentially unscheduled pods
        return False
    for node in client.list_node(label_selector="nodepool={}".format(nodepool_name)).items:
        if node.metadata.name in used_nodes:
            continue
        logger.info("found node {} without any pod.".format(node.metadata.name))
        return True
    return False


if __name__ == '__main__':
    missing_vars = [var for var in MANDATORY_ENV_VARS if var not in os.environ]
    if len(missing_vars):
        logger.error('missing environment variables: {}'.format(','.join(missing_vars)))
        time.sleep(5)
        os.sys.exit(1)

    logger.info("installing SIGINT and SIGTERM handlers")
    killer = GracefulKiller()
    logger.info("waiting to be drained ...")

    nodepool_name = os.environ['NODEPOOL_NAME']
    logger.info("monitoring nodepool {}".format(nodepool_name))

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
        unscheduled_pod = count_unscheduled_pod(k8sclient, nodepool_name)
        if unscheduled_pod == 0:
            if is_there_empty_node(k8sclient, nodepool_name):
                if is_nodepool_stable(k8sapi, nodepool_name):
                    scale_nodepool(k8sapi, nodepool_name, -1)
        else:
            logger.debug("There are {} unscheduled pod(s)".format(unscheduled_pod))
            if is_nodepool_stable(k8sapi, nodepool_name):
                scale_nodepool(k8sapi, nodepool_name, +1)
        # measure global activity
        # metrics = k8sapi.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes", label_selector="nodepool=compute")
    # w.stop()
    logger.info("End of the program. I was killed gracefully :)")
