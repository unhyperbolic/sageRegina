#!/usr/bin/env python

# A packaging of Regina that allows easy installation using python's pip, see
# http://sageRegina.unhyperbolic.org/ for more information.
#
# Matthias Goerner, 09/24/2016
# enischte@gmail.com
#
# Run "python setup.py package" and it will automatically download all the
# necessary sources and create a tar ball suitable for pip.
#
# We can upload with "twine register -r pypi sageRegina-...tar.gz"
# and "twine upload ..."
#
# TODO: extras/regina/engine/regina-config.h still needs to be updated
# manually to reflect REGINA/SNAPPY version.
# 
# Needed downgrade from boost 1.60 to boost 1.59 to not have
# missing to_python converter for NContainer.getFirstTreeChild()
#
# Error when GMP <= 5.1.3 and gcc >= 4.9:
# '::max_align_t' has not been declared
# see https://gcc.gnu.org/gcc-4.9/porting_to.html

# Get version from version.py
exec(open('extras/sageRegina/version.py').read())
exec(open('extras/sageRegina/config.py').read())

import glob, os, sys

# Some of this is copied from SnapPy

# Without the next line, we get an error even though we never
# use distutils as a symbol
from setuptools import distutils

from distutils import sysconfig, log
from distutils.core import Extension
from setuptools import setup, Command

def recursive_glob(path, extension, depth = 0, predicate = None):
    """
    Find all files with the given extension under path up until
    the given depth (defaults to 0). If predicate is given, filter out
    results for which prediate returns False.
    """

    result = []
    for l in range(depth + 1):
        path_components = path.split('/') + l * ['*'] + ['*.' + extension]
        result += glob.glob(os.path.join(*path_components))

    if predicate:
        return [ file_path for file_path in result
                 if predicate(file_path) ]

    #if not result:
    #    raise Exception("No files to compile found. Something is wrong.")

    return result

boost_python_library = {
    'language' : 'c++',
    'sources' : recursive_glob(
        boost_dir + '/libs/python/src', 'cpp', depth = 1),
    # Needs Python.h, so we need to add the python include dir.
    # Extension's do this automatically, but build_clib does not -
    # should this be fixed in distutils?
    'include_dirs' : [ boost_dir, sysconfig.get_python_inc() ]
}

boost_regex_library = {
    'language' : 'c++',
    'sources' : recursive_glob(boost_dir + '/libs/regex/src', 'cpp'),
    'include_dirs' : [ boost_dir]
}

boost_iostreams_library = {
    'language' : 'c++',
    'sources' : recursive_glob(boost_dir + '/libs/iostreams/src', 'cpp'),
    'include_dirs' : [ boost_dir]
}

def tokyocabinet_predicate(file_path):
    files_with_main = ['tcucodec.c', 'test.c']

    file_name = os.path.basename(file_path)

    return not (file_name in files_with_main)

tokyocabinet_library = {
    'language' : 'c',
    'sources' : recursive_glob(tokyocabinet_dir, 'c',
                               predicate = tokyocabinet_predicate),
    'include_dirs' : [ tokyocabinet_dir ],
    'extra_compile_args' : [ '-std=gnu99' ]
}

def libxml_predicate(file_path):

    file_name = os.path.basename(file_path)

    # Filter out files containing main and those supporting
    # xzlib since we don't need it.
    return not ((file_name in ['trio.c', 'xzlib.c']) or
                file_name.startswith('test') or
                file_name.startswith('run'))

libxml_library = {
    'language' : 'c',
    'sources' : recursive_glob(libxml_dir, 'c', predicate = libxml_predicate),
    'include_dirs' : [ libxml_dir + '/include' ],
    # Not exactly sure what is going on with that THREAD_ENABLED, but
    # it didn't seem to build without
    'extra_compile_args' : ['-std=gnu99', '-DLIBXML_THREAD_ENABLED=1']
}

libraries = [
    ('boost_python_regina', boost_python_library),
    ('boost_regex_regina', boost_regex_library),
    ('boost_iostreams_regina', boost_iostreams_library),
    ('tokyocabinet_regina', tokyocabinet_library),
    ('libxml_regina', libxml_library)
]

def regina_predicate(file_path):
    library_path, file_name = os.path.split(file_path)
    library_name = os.path.basename(library_path)

    if 'syntax/' in file_path:
        # Syntax is only used by UI and sageRegina doesn't support UI (yet?)
        # Excluding it so that we don't need to pull in jansson
        return False

    if library_name == 'unused':
        return False

    if library_name == 'libnormaliz':
        # Normaliz needs special behavior.
        # libnormaliz-templated includes other .cpp files in that
        # directory which we should not include to avoid clashes

        file_name_base, ext = os.path.splitext(file_name)
        
        return file_name_base in [
            'HilbertSeries',
            'bottom',
            'cone_property',
            'libnormaliz-templated',
            'offload_handler'
             ]

    return True

def library_include_dirs(libraries):
    return sum(
        [ library['include_dirs'] for name, library in libraries],
        [])

regina_extension = Extension(
    'regina.engine',
    sources = (
        recursive_glob(regina_dir + '/engine', 'cpp', depth = 2,
                       predicate = regina_predicate) +
        # Needed to be renamed .cpp for it to work
#        recursive_glob(regina_dir + '/engine/snappea/kernel', 'cpp') +
#        recursive_glob(regina_dir + '/engine/snappea/snappy', 'cpp') +
        recursive_glob(regina_dir + '/python', 'cpp', depth = 1)),
    include_dirs = [
            regina_dir + '/engine',
            regina_dir + '/python'
        ] + library_include_dirs(libraries),
    language = 'c++',
    extra_compile_args=['-fpermissive', '-std=c++11'],
    libraries = ['gmp','gmpxx','m'],

    # Adding bz2 to the libraries gives a command like 
    # g++ .... -lbz2 -lboost_iostreams_regina ...
    #
    # boost_iostreams_regina needs symbols from bz2 but g++ won't
    # link it unless -lbz2 follows -lboost_iostreams_regina
    #
    # Similarly for libxml and -lz.
    #
    # We achieve the right order by adding it to extra_link_args
    # instead.
    extra_link_args = ['-lbz2','-lz'])


# Monkey patch build_clib.build_libraries so that it takes extra_compile_args
# like Extension does.

from distutils.command import build_clib
from distutils.errors import DistutilsSetupError

def my_build_libraries(self, libraries):
    for (lib_name, build_info) in libraries:
        sources = build_info.get('sources')
        if sources is None or not isinstance(sources, (list, tuple)):
            raise DistutilsSetupError, \
                ("in 'libraries' option (library '%s'), " +
                 "'sources' must be present and must be " +
                 "a list of source filenames") % lib_name
        sources = list(sources)

        log.info("building '%s' library", lib_name)

        # First, compile the source code to object files in the library
        # directory.  (This should probably change to putting object
        # files in a temporary build directory.)
        macros = build_info.get('macros')
        include_dirs = build_info.get('include_dirs')
        objects = self.compiler.compile(
            sources,
            output_dir=self.build_temp,
            macros=macros,
            include_dirs=include_dirs,
            debug=self.debug,
            extra_postargs = build_info.get('extra_compile_args'))
        
        # Now "link" the object files together into a static library.
        # (On Unix at least, this isn't really linking -- it just
        # builds an archive.  Whatever.)
        self.compiler.create_static_lib(objects, lib_name,
                                        output_dir=self.build_clib,
                                        debug=self.debug)

build_clib.build_clib.build_libraries = my_build_libraries

class SystemCommand(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        for cmd in self.system_commands:
            if os.system(cmd):
                raise Exception("When executing %s" % cmd)

class CompoundCommand(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        for cmd in self.commands:
            self.run_command(cmd)

class package_download_boost(SystemCommand):
    system_commands = ['cd /tmp; curl -O %s' % boost_uri]

class package_download_tokyocabinet(SystemCommand):
    system_commands = ['cd /tmp; curl -O %s' % tokyocabinet_uri]

class package_download_libxml(SystemCommand):
    system_commands = ['cd /tmp; curl -O %s' % libxml_uri]
    
class package_download(CompoundCommand):
    commands = [
        'package_download_boost',
        'package_download_tokyocabinet',
        'package_download_libxml'
        ]

class package_untar_boost(SystemCommand):
    system_commands = ['tar -xjf /tmp/%s' % boost_uri.split('/')[-1]]

class package_untar_tokyocabinet(SystemCommand):
    system_commands = ['tar -xzf /tmp/%s' % tokyocabinet_uri.split('/')[-1]]

class package_untar_libxml(SystemCommand):
    system_commands = ['tar -xzf /tmp/%s' % libxml_uri.split('/')[-1]]

class package_untar(CompoundCommand):
    commands = [
        'package_untar_boost',
        'package_untar_tokyocabinet',
        'package_untar_libxml'
        ]

class package_clone_regina(SystemCommand):
    system_commands = ['git clone %s regina_cloned' % (regina_uri)]

class package_fetch_regina(SystemCommand):
    system_commands = ['cd regina_*; git fetch']

class package_checkout_regina(SystemCommand):
    system_commands = [
        'mv regina_* regina_0000000',
        'cd regina_0000000; git checkout %s' % regina_hash,
        'mv regina_0000000 %s' % regina_dir
        ]

class package_retrieve_boost(CompoundCommand):
    commands = [
        'package_download_boost',
        'package_untar_boost'
        ]

class package_retrieve_tokyocabinet(CompoundCommand):
    commands = [
        'package_download_tokyocabinet',
        'package_untar_tokyocabinet'
        ]

class package_retrieve_libxml(CompoundCommand):
    commands = [
        'package_download_libxml',
        'package_untar_libxml'
        ]

class package_retrieve_regina(CompoundCommand):
    commands = [
        'package_clone_regina',
        'package_checkout_regina'
        ]

class package_retrieve(CompoundCommand):
    commands = [
        'package_retrieve_boost',
        'package_retrieve_tokyocabinet',
        'package_retrieve_libxml',
        'package_retrieve_regina'
        ]

class package_extras_libxml(SystemCommand):
    system_commands = ['cp -r extras/libxml/* %s' % libxml_dir]

class package_extras_regina(SystemCommand):
    system_commands = ['cp -r extras/regina/* %s' % regina_dir]

class package_extras(CompoundCommand):
    commands = [
        'package_extras_libxml',
        'package_extras_regina'
        ]

class package_move_info(SystemCommand):
    system_commands = [
        'mv sageRegina.egg-info/PKG-INFO .',
        'rm -rf sageRegina.egg-info'
        ]

class package_info(CompoundCommand):
    commands = [
        'egg_info',
        'package_move_info'
        ]

class package_assemble(CompoundCommand):
    commands = [
        'package_retrieve',
        'package_extras',
        'package_info'
        ]

version_name = 'sageRegina-%s' % version

class package_tar(SystemCommand):
    if 'linux' in sys.platform:
        transform_op = '--transform '
    else:
        # Mac
        transform_op = '-'
        
    system_commands = [
        ('COPYFILE_DISABLE=1 '
         'tar -czf %s.tar.gz '
         '%ss/./%s/ '
         '--exclude "*.tar.*" '
         '--exclude ".git" '
         '--exclude "*~" '
         '--exclude "dist" '
         '--exclude "build" '
         '--exclude "*.egg-info" '
         '.') % (version_name, transform_op, version_name)
        ]

class package(CompoundCommand):
    commands = [
        'package_assemble',
        'package_tar'
        ]

cmdclass = {
    'package_download_boost' : package_download_boost,
    'package_download_tokyocabinet' : package_download_tokyocabinet,
    'package_download_libxml' : package_download_libxml,
    'package_download' : package_download,
    'package_untar_boost' : package_untar_boost,
    'package_untar_tokyocabinet' : package_untar_tokyocabinet,
    'package_untar_libxml' : package_untar_libxml,
    'package_untar' : package_untar,
    'package_clone_regina' : package_clone_regina,
    'package_fetch_regina' : package_fetch_regina,
    'package_checkout_regina' : package_checkout_regina,
    'package_retrieve_boost': package_retrieve_boost,
    'package_retrieve_tokyocabinet': package_retrieve_tokyocabinet,
    'package_retrieve_libxml': package_retrieve_libxml,
    'package_retrieve_regina': package_retrieve_regina,
    'package_retrieve': package_retrieve,
    'package_extras_regina' : package_extras_regina,
    'package_extras_libxml' : package_extras_libxml,
    'package_extras' : package_extras,
    'package_move_info' : package_move_info,
    'package_info' : package_info,
    'package_assemble' : package_assemble,
    'package_tar' : package_tar,
    'package' : package}

setup(name = 'sageRegina',
      version = version,
      zip_safe = False,
      description = 'Regina for SageMath',
      keywords = 'triangulations, topology',
      author = 'Matthias Goerner',
      author_email = 'enischte@gmail.com',
      url = 'http://sageRegina.unhyperbolic.org/',
      license='GPLv2+',
      packages = [
          'regina',
          'regina/sageRegina',
          'regina/sageRegina/testsuite' ],
      package_dir = {
          # For the __init__.py file from regina which imports
          # regina.engine
          'regina' : regina_dir + '/python/regina',
          'regina/sageRegina' : 'extras/sageRegina',
          'regina/sageRegina/testsuite' : regina_dir + '/python/testsuite'
      },
      package_data = {
          'regina/sageRegina/testsuite' : ['*.*']
      },
      ext_modules = [ regina_extension ],
      libraries = libraries,
      cmdclass = cmdclass)
