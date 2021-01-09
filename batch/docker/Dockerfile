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
RUN pip install rasterio --no-binary rasterio

# Pip dependencies.
RUN pip install\
  awscli\
  boto3\
  matplotlib\
  Fiona\
  SQLAlchemy\
  pg8000==1.16.5\
  mercantile
