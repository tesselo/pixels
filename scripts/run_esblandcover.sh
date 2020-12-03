#!/bin/bash

export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export GDAL_DISABLE_READDIR_ON_OPEN=YES
export CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,.jp2
echo $CURL_CA_BUNDLE
echo $GDAL_DISABLE_READDIR_ON_OPEN
echo $CPL_VSIL_CURL_ALLOWED_EXTENSIONS

echo 1
AWS_BATCH_JOB_ARRAY_INDEX=1 PYTHONPATH=/home/tam/Documents/repos/pixels PIXELS_LOCAL_PATH=/home/tam/Desktop/esb/landcover/esblandcover PIXELS_PROJECT_ID=esblandcover python batch/collect.py &&
echo 2
AWS_BATCH_JOB_ARRAY_INDEX=2 PYTHONPATH=/home/tam/Documents/repos/pixels PIXELS_LOCAL_PATH=/home/tam/Desktop/esb/landcover/esblandcover PIXELS_PROJECT_ID=esblandcover python batch/collect.py &&
echo 3
AWS_BATCH_JOB_ARRAY_INDEX=3 PYTHONPATH=/home/tam/Documents/repos/pixels PIXELS_LOCAL_PATH=/home/tam/Desktop/esb/landcover/esblandcover PIXELS_PROJECT_ID=esblandcover python batch/collect.py &&
echo 4
AWS_BATCH_JOB_ARRAY_INDEX=4 PYTHONPATH=/home/tam/Documents/repos/pixels PIXELS_LOCAL_PATH=/home/tam/Desktop/esb/landcover/esblandcover PIXELS_PROJECT_ID=esblandcover python batch/collect.py &&
echo 5
AWS_BATCH_JOB_ARRAY_INDEX=5 PYTHONPATH=/home/tam/Documents/repos/pixels PIXELS_LOCAL_PATH=/home/tam/Desktop/esb/landcover/esblandcover PIXELS_PROJECT_ID=esblandcover python batch/collect.py
