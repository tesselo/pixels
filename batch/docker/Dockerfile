#FROM ubuntu:20.04
#FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-training:2.3.1-gpu-py37-cu110-ubuntu18.04
FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-training:2.3.1-gpu-py37-cu102-ubuntu18.04
#List of aws images https://github.com/aws/deep-learning-containers/blob/master/available_images.md

# Fetch-and-run setup.
# https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/
ADD fetch_and_run.sh /usr/local/bin/fetch_and_run.sh
RUN chmod +x /usr/local/bin/fetch_and_run.sh
WORKDIR /tmp
ENTRYPOINT ["/usr/local/bin/fetch_and_run.sh"]

# Environment.
ENV DEBIAN_FRONTEND=noninteractive
ENV GDAL_DISABLE_READDIR_ON_OPEN=YES
ENV CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,.jp2
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Apt dependencies.
RUN apt-get -y update\
  && apt-get install -y software-properties-common\
  && add-apt-repository ppa:ubuntugis/ubuntugis-unstable\
  && apt-get -y update\
  && apt-get -y install zip gdal-bin libgdal-dev

# Install rasterio without the binaries (use gdal from ubuntugis).
RUN pip install rasterio==1.2.0 --no-binary rasterio

# Pip dependencies.
RUN pip install\
  awscli==1.19.13\
  boto3==1.17.13\
  matplotlib==3.3.4\
  Fiona==1.8.18\
  SQLAlchemy==1.3.23\
  pg8000==1.17.0\
  mercantile==1.1.6\
  pystac==0.5.4\
  jsonschema==3.2.0\
  numpy==1.20.1\
  geopandas==0.8.2
