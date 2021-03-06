# encoding: utf-8
from __future__ import unicode_literals

import os
from os.path import join

import pytest
from osgeo import gdal

# These need to be in your environment.
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

BUCKET = 'public-bucket-gdal-vsis3-tests'
REGION = 'ap-southeast-2'
AWS_S3_ENDPOINT = 's3.{}.amazonaws.com'.format(REGION)

ROOT = join('/vsis3', BUCKET)

STAT_PARAMS = [
    ('a/a.txt', 13, 0),
    ('b/_.txt', 13, 0),
    ('b/+.txt', 13, 0),
    ('b/c c.txt', 13, 0),
    (u'b/ü.txt', 13, 0),
    ('c/$.txt', 13, 0),
    ('c/=.txt', 13, 0),
    ('c/p().txt', 13, 0),
    ('d/utf8.txt', 14, 0),
    ('z.zip', 279, 0),
    (u'macrons/\u0101\u0113\u012b\u014d\u016b/\u0101\u0113\u012b\u014d\u016b.txt', 13, 0),
]

CONTENT_PARAMS = [
    ('a/a.txt', b'Hello world!\n'),
    ('b/+.txt', b'Hello world!\n'),
    ('b/_.txt', b'Hello world!\n'),
    ('b/ü.txt', b'Hello world!\n'),
    ('b/c c.txt', b'Hello world!\n'),
    ('c/$.txt', b'Hello world!\n'),
    ('c/=.txt', b'Hello world!\n'),
    (u'macrons/\u0101\u0113\u012b\u014d\u016b/\u0101\u0113\u012b\u014d\u016b.txt', b'Hello world!\n'),
    ('d/utf8.txt', '¯\_(ツ)_/¯\n'.encode('utf-8')),
]


@pytest.fixture()
def init():
    gdal.SetConfigOption(b'AWS_VIRTUAL_HOSTING', b'NO')
    gdal.SetConfigOption(b'AWS_S3_ENDPOINT', AWS_S3_ENDPOINT.encode())
    gdal.SetConfigOption(b'AWS_ACCESS_KEY_ID', AWS_ACCESS_KEY_ID.encode())
    gdal.SetConfigOption(b'AWS_SECRET_ACCESS_KEY', AWS_SECRET_ACCESS_KEY.encode())
    gdal.SetConfigOption(b'CPL_CURL_VERBOSE', b'YES')


@pytest.fixture()
def uncached():
    print ">>> gdal.VSICurlClearCache()"
    result = gdal.VSICurlClearCache()
    print result


@pytest.fixture()
def cached():
    print '>>> gdal.ReadDirRecursive({})'.format(
        repr(ROOT)
    )
    result = gdal.ReadDirRecursive(ROOT)
    print result


@pytest.mark.parametrize('path,size,is_directory', STAT_PARAMS)
def test_uncached_VSIFStatL(init, uncached, path, size, is_directory):
    """Run VSIFStatL on paths that haven't been cached."""
    vsi_path = join(ROOT, path).encode('utf-8')
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    stat = gdal.VSIStatL(vsi_path)
    print stat
    assert stat is not None
    assert stat.size == size
    assert stat.IsDirectory() == is_directory


@pytest.mark.parametrize('path,size,is_directory', STAT_PARAMS)
def test_cached_VSIFStatL(init, cached, path, size, is_directory):
    """Run VSIFStatL on paths that are already cached by ReadDirRecursive."""
    vsi_path = join(ROOT, path).encode('utf-8')
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    stat = gdal.VSIStatL(vsi_path)
    print stat
    assert stat is not None
    assert stat.size == size
    assert stat.IsDirectory() == is_directory
    assert stat.mtime != 0


@pytest.mark.parametrize('path,expected', [
    ('a', ['a.txt']),
    ('', [
        '2z.zip',
        'a/',
        'a/a.txt',
        'b/',
        'b/+.txt',
        'b/_.txt',
        'b/c c.txt',
        u'b/\xfc.txt',
        'c/',
        'c/$.txt',
        'c/=.txt',
        'c/p().txt',
        'd/',
        'd/utf8.txt',
        'macrons/',
        u'macrons/a\u0304e\u0304i\u0304o\u0304u\u0304.zip',
        u'macrons/\u0101\u0113\u012b\u014d\u016b/',
        u'macrons/\u0101\u0113\u012b\u014d\u016b/\u0101\u0113\u012b\u014d\u016b.txt',
        'z.zip',
        'z/',
        'z/a.txt',
    ]),
])
def test_ReadDirRecursive(init, uncached, path, expected):
    vsi_path = join(ROOT, path)
    listing = gdal.ReadDirRecursive(vsi_path)
    listing.sort()
    print listing
    assert listing == expected


@pytest.mark.parametrize('path,expected', [
    ('a', ['a.txt']),
])
def test_readdir(init, uncached, path, expected):
    vsi_path = join(ROOT, path)
    listing = gdal.ReadDirRecursive(vsi_path)
    listing.sort()
    print listing
    assert listing == expected


@pytest.mark.parametrize('path,expected_contents', CONTENT_PARAMS)
def test_file_read(init, uncached, path, expected_contents):
    vsi_path = join(ROOT, path)
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    stat = gdal.VSIStatL(vsi_path)
    print stat
    assert stat is not None, "VSIStatL({}) returned None".format(repr(vsi_path))
    file_handle = gdal.VSIFOpenExL(vsi_path, b'r', 1)
    if file_handle is None:
        error_no = gdal.VSIGetLastErrorNo()
        error_msg = gdal.VSIGetLastErrorMsg()
        print 'VSIFOpenExL() error {}, {}'.format(error_no, error_msg)
    assert file_handle is not None
    contents = gdal.VSIFReadL(1, stat.size, file_handle)
    closed_result = gdal.VSIFCloseL(file_handle)
    assert contents == expected_contents
    assert closed_result == 0


def test_zip_slash(init, uncached):
    vsi_path = '/vsizip/' + ROOT + '/z.zip'
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    # This pretends to be the file INSIDE z.zip
    stat = gdal.VSIStatL(vsi_path)
    assert stat.size == 13
    assert stat.mtime is not None
    assert stat.IsDirectory() == 0


def test_zip_noslash(init, uncached):
    vsi_path = '/vsizip' + ROOT + '/z.zip'
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    # This pretends to be the file INSIDE z.zip
    stat = gdal.VSIStatL(vsi_path)
    assert stat.size == 13
    assert stat.mtime is not None
    assert stat.IsDirectory() == 0


def test_zip_ReadDirRecursive(init, uncached):
    vsi_path = '/vsizip' + ROOT + '/z.zip'
    print '>>> gdal.ReadDirRecursive({!r})'.format(vsi_path)
    listing = gdal.ReadDirRecursive(vsi_path)
    print repr(listing)
    listing.sort()
    assert listing == ['z/', 'z/a.txt']


def test_two_zip_ReadDirRecursive(init, uncached):
    vsi_path = '/vsizip' + ROOT + '/2z.zip'
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    # This pretends to be the file INSIDE z.zip
    stat = gdal.VSIStatL(vsi_path)
    assert stat is not None
    assert stat.IsDirectory() == 1
    print '>>> gdal.ReadDirRecursive({!r})'.format(vsi_path)
    listing = gdal.ReadDirRecursive(vsi_path)
    print repr(listing)
    listing.sort()
    assert listing == ['2z/', '2z/one.txt', '2z/two.txt']


@pytest.mark.xfail
def test_zip_macrons(init, uncached):
    vsi_path = '/vsizip' + ROOT + u'/macrons/a\u0304e\u0304i\u0304o\u0304u\u0304.zip'
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    # This pretends to be the file INSIDE z.zip
    stat = gdal.VSIStatL(vsi_path)
    assert stat is not None
    assert stat.IsDirectory() == 0
    assert stat.mtime is not None
    assert stat.size == 13
    listing = gdal.ReadDir(vsi_path)
    listing.sort()
    assert listing == []
