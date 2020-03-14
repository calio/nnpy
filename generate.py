from cffi import FFI
import os
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
NANOMSG_DYNAMIC_LIB = "nanomsg/build/dest/lib/libnanomsg.so"

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


def get_nanomsg_source():
    if not os.path.exists(lib):
        check_call("git clone https://github.com/nanomsg/nanomsg.git", shell=True)
    check_call("git checkout {}".format(NANOMSG_TAG), shell=True, cwd=lib)


def build_nanomsg_dynamic_lib():
    build_dir = os.path.join(lib, "build")
    if os.path.exists(build_dir):
        check_call("rm -r {}".format(build_dir), shell=True)

    check_call("mkdir -p {}".format(build_dir), shell=True)

    check_call('FLAGS=-fPIC cmake -G "Unix Makefiles" "-DCMAKE_INSTALL_PREFIX=dest" ..', shell=True, cwd=build_dir)
    check_call("make -j8 install", shell=True, cwd=build_dir)

def build_nanomsg_static_lib():
    build_dir = os.path.join(lib, "build")
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

def symbols(ffi, host_library):

    nanomsg = ffi.dlopen(host_library)
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

def create_module():
    ffi = FFI()

    get_nanomsg_source()
    build_nanomsg_static_lib()

    build_nanomsg_dynamic_lib()

    #host_library = DEFAULT_HOST_LIBRARY
    host_library = NANOMSG_DYNAMIC_LIB

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


    ffi.cdef(DEFINITIONS)
    ffi.cdef(functions(hfiles))
    ffi.set_source('_nnpy', '\n'.join('#include <%s>' % fn for fn in hfiles),
                   extra_objects=[NANOMSG_STATIC_LIB],
                   libraries = ['pthread', 'anl'],
                   **set_source_args)

    library_symbols = symbols(ffi, host_library)

    with open('nnpy/constants.py', 'w') as f:
        f.write(library_symbols)

    return ffi

ffi = create_module()

if __name__ == '__main__':
    ffi.compile()
