#!/usr/bin/env bash
set -o nounset
set -o errexit

TAG=${1:-1.1.5}
rm -rf nanomsg
git clone https://github.com/nanomsg/nanomsg.git
cd nanomsg && git checkout $TAG
mkdir desk
./configure --prefix=dest
make
make install
