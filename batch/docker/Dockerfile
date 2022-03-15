# List of aws images https://github.com/aws/deep-learning-containers/blob/master/available_images.md
FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-training:2.7.0-gpu-py38-cu112-ubuntu20.04-e3

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
ENV SENTRY_DSN=https://3d69110c01aa41f48f28cf047bfcbc91@o640190.ingest.sentry.io/5760850

# Apt dependencies.
RUN apt-get -y update\
  && apt-get install -y software-properties-common\
  && add-apt-repository ppa:ubuntugis/ubuntugis-unstable\
  && apt-get -y update\
  && apt-get -y install zip gdal-bin libgdal-dev

RUN pip install -U pip
ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt
