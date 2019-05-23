FROM ubuntu:18.04
# https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/
RUN apt-get -y update\
  && apt-get -y upgrade\
  && apt-get install -y python3-pip zip\
  && pip3 install\
  Keras==2.2.4\
  tensorflow==1.13.1\
  scipy==1.2.1\
  scikit-learn==0.20.3\
  awscli==1.16.150\
  boto3==1.9.140\
  rasterio==1.0.22\
  Pillow==6.0.0\
  requests==2.21\
  pyproj==1.9.6

ADD fetch_and_run.sh /usr/local/bin/fetch_and_run.sh
RUN chmod +x /usr/local/bin/fetch_and_run.sh
WORKDIR /tmp
ENTRYPOINT ["/usr/local/bin/fetch_and_run.sh"]
