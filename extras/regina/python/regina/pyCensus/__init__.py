"""
Dummy module to obtain path for census files from python.

The TokyoCabinet database files .tdb are for versin version 1.0:910 and in
little endian encoding suitable. Note that sageRegina is compiling its own
version of TokyoCabinet so the files we supply should work on all operating
systems and little endian platforms. 

The .tdb files will be incompatible with the TokyoCabinet version shipped
with Debian/Ubuntu because of a stupid bug: on these systems, TokyoCabinet
is always using non-native (!) endianess (since --enable-swap was
accidentally supplied to configure).

"""
