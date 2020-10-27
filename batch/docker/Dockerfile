FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/

RUN apt-get -y update\
  && apt-get -y upgrade\
  && apt-get install -y python3-pip zip software-properties-common

RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable\
  && apt-get -y update\
  && apt-get -y install gdal-bin libgdal-dev

RUN pip3 install rasterio --no-binary rasterio

ENV GDAL_DISABLE_READDIR_ON_OPEN=YES
ENV CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN pip3 install boto3
RUN pip3 install Fiona==1.8.14

ADD fetch_and_run.sh /usr/local/bin/fetch_and_run.sh
RUN chmod +x /usr/local/bin/fetch_and_run.sh
WORKDIR /tmp
ENTRYPOINT ["/usr/local/bin/fetch_and_run.sh"]

RUN pip3 install\
  awscli\
  Pillow\
  requests\
  pyproj

RUN pip3 install sat-stac
