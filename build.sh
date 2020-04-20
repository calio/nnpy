#!/usr/bin/env bash
set -o nounset
set -o errexit

#DOCKER_IMAGE=quay.io/pypa/manylinux1_x86_64
DOCKER_IMAGE=quay.io/pypa/manylinux2010_x86_64
PLAT=manylinux2010_x86_64
#PLAT=manylinux1_x86_64
PRE_CMD=

mkdir -p wheelhouse
docker pull $DOCKER_IMAGE
docker run --rm -e PLAT=$PLAT -v `pwd`:/io $DOCKER_IMAGE $PRE_CMD /io/travis/build-wheels.sh
