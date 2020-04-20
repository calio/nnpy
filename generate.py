from cffi import FFI
import os
import sys
from subprocess import check_call

try:
    import ConfigParser as cfgparser
except ImportError:
    # try py3 import
    import configparser as cfgparser

SITE_CFG = 'site.cfg'

DEFAULT_INCLUDE_DIRS = ['./nanomsg/build/dest/include/nanomsg']
DEFAULT_HOST_LIBRARY = 'nanomsg'
NANOMSG_STATIC_LIB = "libnanomsg.a"
NANOMSG_DYNAMIC_LIBS = [
    "nanomsg/build/dest/lib/libnanomsg.so",
    "nanomsg/build/dest/lib64/libnanomsg.so",
    "nanomsg/build/dest/lib/libnanomsg.dylib",
]

BLOCKS = {'{': '}', '(': ')'}
DEFINITIONS = '''
struct nn_pollfd {
    int fd;
    short events;
    short revents;
};
'''
NANOMSG_TAG="1.1.5"
lib="nanomsg"


def get_nanomsg_source(cwd):
    wd = os.path.join(cwd, lib)
    if os.path.exists(wd):
        check_call("rm -rf nanomsg", shell=True, cwd=cwd)
    if os.path.exists(NANOMSG_STATIC_LIB):
        check_call("rm -rf {}".format(NANOMSG_STATIC_LIB), shell=True, cwd=cwd)

    check_call("git clone https://github.com/nanomsg/nanomsg.git", shell=True, cwd=cwd)
    check_call("git checkout {}".format(NANOMSG_TAG), shell=True, cwd=wd)


def build_nanomsg_dynamic_lib(cwd):
    build_dir = os.path.join(cwd, lib, "build")

    #build_dir = os.path.join(lib, "build")
    if os.path.exists(build_dir):
        check_call("rm -r {}".format(build_dir), shell=True)

    check_call("mkdir -p {}".format(build_dir), shell=True)

    check_call('FLAGS=-fPIC cmake -G "Unix Makefiles" "-DCMAKE_INSTALL_PREFIX=dest" ..', shell=True, cwd=build_dir)
    check_call("make -j8 install", shell=True, cwd=build_dir)

def build_nanomsg_static_lib(cwd):
    build_dir = os.path.join(cwd, lib, "build")
    #build_dir = os.path.join(lib, "build")
    if os.path.exists(build_dir):
        check_call("rm -r {}".format(build_dir), shell=True)

    check_call("mkdir -p {}".format(build_dir), shell=True)

    check_call('cmake "-DCMAKE_C_FLAGS=-fPIC" "-DCMAKE_INSTALL_PREFIX=dest" "-DNN_STATIC_LIB=ON" ..', shell=True, cwd=build_dir)
    check_call("make -j8", shell=True, cwd=build_dir)
    check_call("cp libnanomsg.a ../../", shell=True, cwd=build_dir)

def header_files(include_paths):
    for dir in include_paths:
        if os.path.exists(dir):
            break
    return {fn: os.path.join(dir, fn) for fn in os.listdir(dir)
            if fn.endswith('.h')}

def functions(hfiles):

    lines = []
    for fn, path in hfiles.items():
        with open(path) as f:
            cont = ''
            for ln in f:

                if cont == ',':
                    lines.append(ln)
                    cont = ''
                if cont in BLOCKS:
                    lines.append(ln)
                    if BLOCKS[cont] in ln:
                        cont = ''
                if not (ln.startswith('NN_EXPORT')
                    or ln.startswith('typedef')):
                    continue

                lines.append(ln)
                cont = ln.strip()[-1]

    return ''.join(ln[10:] if ln.startswith('NN_') else ln for ln in lines)

def symbols(ffi, host_library, cwd):
    if isinstance(host_library, str):
        libpath = os.path.join(cwd, host_library)

        nanomsg = ffi.dlopen(libpath)
    else:
        for path in host_library:
            libpath = os.path.join(cwd, path)
            try:
                nanomsg = ffi.dlopen(libpath)
            except OSError:
                continue
            break
        else:
            raise RuntimeError("no libnanomsg.so found, searched: {}".format(host_library))

    lines = []
    for i in range(1024):

        val = ffi.new('int*')
        name = nanomsg.nn_symbol(i, val)
        if name == ffi.NULL:
            break

        name = ffi.string(name).decode()
        name = name[3:] if name.startswith('NN_') else name
        lines.append('%s = %s' % (name, val[0]))

    return '\n'.join(lines) + '\n'

def find_lib(libpath):
    if os.path.exists(libpath):
        return libpath
    head, tail = os.path.split(libpath)

def create_module():
    cwd = os.getcwd()

    ffi = FFI()

    get_nanomsg_source(cwd)
    build_nanomsg_static_lib(cwd)

    build_nanomsg_dynamic_lib(cwd)

    #host_library = DEFAULT_HOST_LIBRARY
    host_library = NANOMSG_DYNAMIC_LIBS

    set_source_args = {
        'include_dirs': DEFAULT_INCLUDE_DIRS
    }

    # Read overrides for cross-compilation support from site.cfg

    if os.path.isfile(SITE_CFG):
        parser = cfgparser.ConfigParser()

        if parser.read(SITE_CFG):

            parsed_cfg = parser.defaults()
            for param in ['include_dirs', 'library_dirs']:
                if param in parsed_cfg:
                    set_source_args[param] = parsed_cfg[param].split(',')

            if 'host_library' in parsed_cfg:
                host_library = parsed_cfg['host_library']

    # Add some more directories from the environment

    if 'CPATH' in os.environ:
        cpaths = os.getenv('CPATH').split(os.pathsep)
        set_source_args['include_dirs'] += [os.path.join(p, 'nanomsg')
                                            for p in cpaths]

    hfiles = header_files(set_source_args['include_dirs'])
    # remove ws.h due to https://github.com/nanomsg/nanomsg/issues/467
    hfiles.pop('ws.h', None)

    # Build FFI module and write out the constants

    libraries = ["pthread", "anl"]
    if sys.platform == "darwin":
        libraries.remove("anl")

    ffi.cdef(DEFINITIONS)
    ffi.cdef(functions(hfiles))
    ffi.set_source('_nnpy', '\n'.join('#include <%s>' % fn for fn in hfiles),
                   extra_objects=[NANOMSG_STATIC_LIB],
                   libraries=libraries,
                   **set_source_args)

    library_symbols = symbols(ffi, host_library, cwd)

    with open('nnpy/constants.py', 'w') as f:
        f.write(library_symbols)

    return ffi

ffi = create_module()

if __name__ == '__main__':
    ffi.compile()
