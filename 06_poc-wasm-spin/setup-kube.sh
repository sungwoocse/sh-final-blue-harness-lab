#!/bin/bash

# Kubernetes config setup script
export KUBECONFIG="$(dirname "$(realpath "$BASH_SOURCE")")/kube-config"

echo "KUBECONFIG set to: $KUBECONFIG"
echo ""
kubectl get nodes
