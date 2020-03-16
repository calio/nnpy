#!/bin/bash
set -e -x

# Install a system package required by our library
yum install -y cmake

# Compile wheels
for PYBIN in /opt/python/*/bin; do
    echo "PYBIN: $PYBIN"
    if [[ "${PYBIN}" =~ "cp27" ]]; then
        continue
    fi
    if [[ "${PYBIN}" =~ "cp34" ]]; then
        continue
    fi
    "${PYBIN}/pip" install -r /io/dev-requirements.txt
    "${PYBIN}/pip" wheel /io/ -w wheelhouse/
done

# Bundle external shared libraries into the wheels
#for whl in wheelhouse/*.whl; do
#    auditwheel repair "$whl" --plat $PLAT -w /io/wheelhouse/
#done

# HACK: libnanomsg relies on libanl.so but libanl.so cannot be fixed by
# auditwheel to build manylinux wheel. libanl.so is a part of glibc
# so as long as glibc version is support, most of the time it should work.
rename linux manylinux1 wheelhouse/*.whl
cp wheelhouse/*.whl /io/wheelhouse/

# Install packages and test
for PYBIN in /opt/python/*/bin/; do
    if [[ "${PYBIN}" =~ "cp27" ]]; then
        continue
    fi
    if [[ "${PYBIN}" =~ "cp34" ]]; then
        continue
    fi
    "${PYBIN}/pip" install nnpy-bundle --no-index -f /io/wheelhouse
    (cd "$HOME"; "${PYBIN}/python" /io/demo.py)
done
