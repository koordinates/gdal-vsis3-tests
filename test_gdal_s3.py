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


@pytest.fixture()
def init():
    gdal.SetConfigOption(b'AWS_VIRTUAL_HOSTING', b'NO')
    gdal.SetConfigOption(b'AWS_S3_ENDPOINT', AWS_S3_ENDPOINT.encode())
    gdal.SetConfigOption(b'AWS_ACCESS_KEY_ID', AWS_ACCESS_KEY_ID.encode())
    gdal.SetConfigOption(b'AWS_SECRET_ACCESS_KEY', AWS_SECRET_ACCESS_KEY.encode())
    #gdal.SetConfigOption(b'CPL_CURL_VERBOSE', b'YES')


@pytest.fixture()
def clear():
    print ">>> gdal.VSICurlClearCache()"
    result = gdal.VSICurlClearCache()
    print result


@pytest.fixture()
def preread():
    print '>>> gdal.ReadDirRecursive({})'.format(
        repr(ROOT)
    )
    result = gdal.ReadDirRecursive(ROOT)
    print result


@pytest.mark.parametrize('path,size,is_directory', [
    ('a/a.txt', 13, 0),
    ('b/_.txt', 13, 0),
    (u'b/\xfc.txt', 13, 0),
])
def test_uncached_VSIFStatL(init, clear, path, size, is_directory):
    """Run VSIFStatL on paths that haven't been cached."""
    vsi_path = join(ROOT, path)
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    stat = gdal.VSIStatL(vsi_path)
    print stat
    assert stat is not None
    assert stat.size == size
    assert stat.IsDirectory() == is_directory


@pytest.mark.parametrize('path,size,is_directory', [
    ('a/a.txt', 13, 0),
    ('b/_.txt', 13, 0),
    (u'b/\xfc.txt', 13, 0),  # This is the unlaut: ü
])
def test_cached_VSIFStatL(init, preread, path, size, is_directory):
    """Run VSIFStatL on paths that are already cached by ReadDirRecursive."""
    vsi_path = join(ROOT, path)
    print ">>> gdal.VSIStatL({})".format(repr(vsi_path))
    stat = gdal.VSIStatL(vsi_path)
    print stat
    assert stat is not None
    assert stat.size == size
    assert stat.IsDirectory() == is_directory


@pytest.mark.parametrize('path,expected', [
    ('a', ['a.txt']),
    ('', ['a/', 'a/a.txt', 'b/', 'b/+.txt', 'b/_.txt', u'b/\xfc.txt']),
])
def test_ReadDirRecursive(init, clear, path, expected):
    vsi_path = join(ROOT, path)
    listing = gdal.ReadDirRecursive(vsi_path)
    listing.sort()
    print listing
    assert listing == expected
