# Locally running pixels batch jobs
For local testing of new functionality or debugging failing jobs, it is possible to run jobs locally in a docker container.
In our cloud systems we run all jobs in containers based on a single Docker image. So to run jobs locally,
we need to make a copy of the image and run the tasks in there.

# Download the tesselo image
First, you have to pull the Tesselo pixels docker image from our private Docker repository on AWS.

To download it, first log into the AWS docker repository and then pull the image.

We have a [utility script](https://github.com/tesselo/pixels/blob/main/pixels/batch/pull_ecs_image.sh) that you can use.

```
# cd into the batch directory in the pixels repo, then run
./pull_ecs_image.sh
```

This image is based on one of the images in a [list of available AWS managed base images](https://github.com/aws/deep-learning-containers/blob/master/available_images.md).
Note that you need to have Docker installed and your AWS credentials setup for this to work.

# Running jobs locally
To run jobs locally, and having control over the source version used, there Docker container
needs to have a specific setup.

## Use your local version of the pixels code
You can link the local pixels repository with the correct location in the image through a volume.
This can be done using the `-v` argument of the `docker run` command. It will substitute the code
in the image with your local version of the repository.

## Connect the image to the database and S3
The image needs the passwords of the DB that you want to connect to and AWS credentials. This
is handled through environment variables that are passed to the image through the `--env` command.

## Enabling GPU
If you have a GPU on your computer, enable the docker container to access it through the `--gpus all` flag.
Note that this will require the correct CUDA drivers to be installed locally too. So its not guaranteed to
work out of the box.

## Prepare the command to run
Our batch commands are executed through the [`runpixels.py`](https://github.com/tesselo/pixels/blob/main/pixels/batch/runpixels.py) script.
This is the command that needs to be evoked to reproduce the same software stack as in the online batch job. 
So we need to specify the right input for the runpixels script.

## Complete example
The code snipped below shows an example of running existing training job in a local container

```
docker run\
  --rm \
  -it \
  --gpus all\
  --env BATCH_FILE_S3_URL=s3://tesselo-pixels-scripts/batch.zip\
  --env BATCH_FILE_TYPE=zip\
  --env GDAL_DISABLE_READDIR_ON_OPEN=YES\
  --env CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,.jp2\
  --env DB_USER=tesselo\
  --env DB_NAME=$DB_NAME\
  --env DB_HOST=$DB_HOST\
  --env DB_PASSWORD=$DB_PASSWORD\
  --env AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY\
  --env AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID\
  --env AWS_REQUEST_PAYER=requester\
  --env SENTRY_DSN=\
  --entrypoint /usr/local/bin/python3.7\
  -v /home/tam/Documents/repos/pixels/pixels:/pixels\
  -v /home/tam/Documents/repos/pixels/batch/runpixels.py:/runpixels.py\
  595064993071.dkr.ecr.eu-central-1.amazonaws.com/tesselo-pixels:latest\
  /runpixels.py \
  pixels.generator.stac_training.train_model_function\
  s3://pxapi-media-dev/pixelsdata/5421dd44-2991-41de-b01c-d85c4d14f71b/data/collection.json\
  s3://pxapi-media-dev/kerasmodel/878b42f4-d914-48c6-b9cc-749cba823029/model.json\
  s3://pxapi-media-dev/kerasmodel/878b42f4-d914-48c6-b9cc-749cba823029/compile_arguments.json\
  s3://pxapi-media-dev/kerasmodel/878b42f4-d914-48c6-b9cc-749cba823029/fit_arguments.json\
  s3://pxapi-media-dev/kerasmodel/878b42f4-d914-48c6-b9cc-749cba823029/generator_arguments.json

```
