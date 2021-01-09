#!/usr/bin/env python3.7

import logging
import os
import tempfile
import shutil

import boto3
import numpy
import numpy as np
import tensorflow
from rasterio import Affine
from tensorflow.keras.models import load_model

import pixels.generator.generator_class as gen
import pixels.utils as utils

# Setup tensorflow session for model to use GPU.
config = tensorflow.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
session = tensorflow.compat.v1.InteractiveSession(config=config)

# Logging.
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

s3 = boto3.client("s3")

bucket = os.environ.get("AWS_S3_BUCKET", "tesselo-pixels-results")
project_id = os.environ.get("PIXELS_PROJECT_ID", "test")
local_path = os.environ.get("PIXELS_LOCAL_PATH", None)
array_index = int(os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX", 0))
features_per_job = int(os.environ.get("BATCH_FEATURES_PER_JOB", 100))
logger.info(
    "Bucket {} | Project {} | ArrayIndex {} | FeatPerJob {}".format(
        bucket, project_id, array_index, features_per_job
    )
)

# Construct model.
if local_path:
    model = load_model(os.path.join(local_path, "model_3D_13epochs.h5"))
else:
    with tempfile.TemporaryDirectory() as dirpath:
        logger.info('Loading model from S3')
        filename = os.path.join(dirpath, 'model.h5')
        s3.download_file(
            Bucket=bucket,
            Key=project_id + "/model_3D_13epochs.h5",
            Filename=filename,
        )
        model = load_model(filename)

index_range = range(
    array_index * features_per_job, (array_index + 1) * features_per_job
)

for file_index in index_range:
    with tempfile.TemporaryDirectory() as dirpath:
        logger.info('Getting object {}'.format(file_index))
        filename = os.path.join(dirpath, 'data.npz')
        if local_path:
            shutil.copy(os.path.join(local_path, 'training/pixels_{}.npz'.format(file_index)), filename)
        else:
            # Get prediction data.
            s3.download_file(
                Bucket=bucket,
                Key=project_id + "/training/pixels_{}.npz".format(file_index),
                Filename=filename,
            )
        # Setup generator with only one file in it.
        full_set = gen.DataGenerator_NPZ(
            dirpath,
            train=True,
            split=1,
            mode="SQUARE",
            upsampling=10,
            bands=[0, 1, 2, 6, 7, 8, 9],
            cloud_mask_filter=False,
            seed=24,
            prediction_mode=True,
        )
        # Run generator using the only file with index 0.
        INDEX = 0
        # Get input path.
        in_path = full_set.get_item_path(INDEX)
        # Create ouput path.
        filename = "_".join(in_path.split("/")[-2:]).replace(".npz", ".tif")
        if local_path:
            out_path = os.path.join(
                local_path, "predicted/prediction_{}.tif".format(file_index)
            )
        else:
            out_path = os.path.join(
                dirpath,
                filename,
            )
        # Pre create variables.
        original_data = None
        data = None
        vstack = None
        hstack = None
        prediction = None
        # Load data from generator.
        data = full_set[INDEX]
        # Assume size 10x10.
        vstack = []
        for i in range(10):
            hstack = []
            for j in range(10):
                # Predict output.
                prediction = model.predict(
                    data[0][:, :, (i * 360) : ((i + 1) * 360), (j * 360) : ((j + 1) * 360)]
                )
                # Reduce dimensions.
                prediction = np.squeeze(prediction)
                hstack.append(prediction)
            hstack = np.hstack(hstack)
            vstack.append(hstack)
        prediction = np.vstack(vstack)
        # Get the orignal data for this item.
        original_data = np.load(in_path, allow_pickle=True)
        # Convert the creation args to the target size.
        try:
            args = original_data["args"][0]
        except IndexError:
            args = original_data["args"].item()
        except KeyError:
            args = original_data["creation_args"].item()

        args["width"] = 3600
        args["height"] = 3600
        args["count"] = 1
        args["transform"] = Affine(
            1,
            args["transform"][1],
            args["transform"][2],
            args["transform"][3],
            -1,
            args["transform"][5],
        )
        # Add date to args.
        args["date"] = original_data["dates"][-1]
        # Ensure output directory exists.
        if not os.path.exists(os.path.dirname(out_path)):
            os.makedirs(os.path.dirname(out_path))
        # Write raster file from prediction.
        utils.write_raster(prediction, args, out_path=out_path)
        # Upload result to bucket.
        if not local_path:
            logger.info('Uploading prediction to S3')
            s3.upload_file(
                Bucket=bucket,
                Key="{project_id}/predicted/prediction_{fid}.tif".format(
                    project_id=project_id,
                    fid=file_index,
                ),
                Filename=out_path,
            )
        # Ensure memory is released.
        del original_data
        del data
        del vstack
        del hstack
        del prediction
        del full_set
