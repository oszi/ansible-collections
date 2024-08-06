#!/bin/bash
set -euo pipefail

if [ -n "${GOOGLE_APPLICATION_CREDENTIALS-}" ]; then
    gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
fi

if [ -n "${GOOGLE_PROJECT_ID-}" ]; then
    gcloud config set project "$GOOGLE_PROJECT_ID"
fi

_cluster="$(gcloud config get-value container/cluster 2>/dev/null)"
_region="$(gcloud config get-value compute/zone 2>/dev/null)"
_zone="$(gcloud config get-value compute/zone 2>/dev/null)"
_project="$(gcloud config get-value core/project 2>/dev/null)"

if [ -z "$_cluster" ] || [ -z "$_project" ]; then
    cat >/dev/stderr <<EOF
No cluster is set. Set the environment variables:
  CLOUDSDK_CONTAINER_CLUSTER=<cluster-name>
  CLOUDSDK_COMPUTE_REGION=<cluster-region> or CLOUDSDK_COMPUTE_ZONE=<cluster-zone>
  GOOGLE_PROJECT_ID=<project-id>
EOF
else
    # Either --region or --zone must be supplied
    if [ -n "$_region" ]; then
        _region_zone="--region=${_region}"
    else
        _region_zone="--zone=${_zone}"
    fi
    # Configure the authenticated kube context
    gcloud container clusters get-credentials --project="$_project" "$_region_zone" "$_cluster"
fi

# Configure the docker authentication plugin for gcr.io
if command -v docker &>/dev/null; then
    gcloud auth configure-docker --verbosity=error
fi

# Behave as an entrypoint
if [ $# -gt 0 ]; then
    echo "Executing $*" >&2
    exec "$@"
fi
