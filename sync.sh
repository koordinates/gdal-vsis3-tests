#!/bin/sh

cd $(dirname $0)/public-bucket-gdal-vsis3-tests

aws s3 sync --delete . s3://public-bucket-gdal-vsis3-tests
