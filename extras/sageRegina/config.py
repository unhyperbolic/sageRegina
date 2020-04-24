# Boost stripped to python, iostreams and smart_ptr
#
# It was created by downloading boost, running
#    ./bootstrap.sh
#    ./bjam tools/bcp
#    mkdir /tmp/boost_1_68_0
#    dist/bin/bcp python iostreams smart_ptr /tmp/boost_1_68_0
#    cd /tmp
#    COPYFILE_DISABLE=1 tar -cjf boost_1_68_0__python__iostreams__smart_ptr.tar.bz2 boost_1_68_0

boost_uri         = 'http://sageRegina.unhyperbolic.org/sources/boost_1_68_0__python__iostreams__smart_ptr.tar.bz2'
boost_dir         = 'boost_1_68_0'

tokyocabinet_uri  = 'http://sageRegina.unhyperbolic.org/sources/tokyocabinet-1.4.48.tar.gz'
tokyocabinet_dir  = 'tokyocabinet-1.4.48'

libxml_uri        = 'http://sageRegina.unhyperbolic.org/sources/libxml2-2.9.3.tar.gz'
libxml_dir        = 'libxml2-2.9.3'

regina_hash      = '3a523aa'
regina_uri       = 'https://github.com/regina-normal/regina.git'
regina_dir       = 'regina_%s' % regina_hash
