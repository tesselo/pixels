FROM ubuntu:20.04

# Fetch-and-run setup.
# https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/
ADD fetch_and_run.sh /usr/local/bin/fetch_and_run.sh
RUN chmod +x /usr/local/bin/fetch_and_run.sh
WORKDIR /tmp
ENTRYPOINT ["/usr/local/bin/fetch_and_run.sh"]

# Environment.
ENV DEBIAN_FRONTEND=noninteractive
ENV GDAL_DISABLE_READDIR_ON_OPEN=YES
ENV CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Apt dependencies.
RUN apt-get -y update\
  && apt-get -y upgrade\
  && apt-get install -y software-properties-common\
  && add-apt-repository ppa:ubuntugis/ubuntugis-unstable\
  && apt-get -y update\
  && apt-get -y install python3-pip zip gdal-bin libgdal-dev

# Install rasterio without the binaries (use gdal from ubuntugis).
RUN pip3 install rasterio --no-binary rasterio

# Pip dependencies.
RUN pip3 install\
  awscli\
  boto3\
  Fiona\
  SQLAlchemy\
  tensorflow\
  pg8000==1.16.5\
  mercantile==1.1.6
