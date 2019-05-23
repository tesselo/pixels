#!/usr/bin/env python3

import io
import json
import os

import boto3
import h5py
import numpy
from keras.layers import Dense
from keras.models import Sequential, load_model, model_from_json
from rasterio.io import MemoryFile

from pixels import utils

# Get path from env.
project_id = os.environ.get('PROJECT_ID', 'test')
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
train_or_predict = 'predict' if os.environ.get('PREDICT', 'false').lower() == 'true' else 'train'
# Fetch config.
s3 = boto3.client('s3')
config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
config = json.loads(config['Body'].read())
# Fetch data package.
s3 = boto3.client('s3')
data = s3.get_object(
    Bucket=bucket,
    Key='{project_id}/{train_or_predict}.npz'.format(
        project_id=project_id,
        train_or_predict=train_or_predict,
    )
)['Body'].read()
data = numpy.load(io.BytesIO(data), allow_pickle=True)
X = data['X']

# Train or predict model.
if train_or_predict == 'train':
    Y = data['Y']
    # Generate lookup and replace Y values with index.
    num_classes = len(numpy.unique(Y))
    class_lookup = {}
    for index, y in enumerate(numpy.unique(Y)):
        # Store class dependency.
        class_lookup[str(index)] = str(y)
        # Replace values with lookup.
        Y[Y == y] = index

    # Build the model.
    model = model_from_json(json.dumps(config['keras_model']))
    # Ensure model is a sequential model.
    if not isinstance(model, Sequential):
        raise ValueError('Keras model needs to be of class Sequential.')

    # Ensure last layer is a Dense layer with correct output shape specification.
    if isinstance(model.layers[-1], Dense):
        if not model.layers[-1].output_shape[-1] == num_classes:
            raise ValueError('Number of classes in dense layer does not match input data.')
    else:
        model.add(Dense(num_classes, activation='softmax'))

    # Compile the model.
    compile_parms = config.get('keras_compile_arguments', {
        'optimizer': 'rmsprop',
        'loss': 'sparse_categorical_crossentropy',
        'metrics': ['accuracy'],
    })
    model.compile(**compile_parms)

    # Fit the model.
    fit_parms = config.get('keras_fit_arguments', {
        'epochs': 10,
        'batch_size': 1000,
    })
    model.fit(X, Y, **fit_parms)
    model.summary()

    # Store the model in bucket.
    with io.BytesIO() as fl:
        with h5py.File(fl) as h5fl:
            model.save(h5fl)
            h5fl.flush()
            h5fl.close()
        s3.put_object(
            Bucket=bucket,
            Key='{}/model.h5'.format(project_id),
            Body=fl.getvalue(),
        )

    # Store class lookup.
    with io.StringIO(json.dumps(class_lookup)) as fl:
        s3.put_object(
            Bucket=bucket,
            Key='{}/class_lookup.json'.format(project_id),
            Body=fl.getvalue(),
        )

else:
    # Prepare raster transform arguments to create target tif raster.
    config['geom'] = config['predict']['features'][0]
    config = utils.validate_configuration(config)
    transform, width, height, crs = utils.compute_transform(config['geom'], config['scale'])
    creation_args = {
        'driver': 'GTiff',
        'crs': crs,
        'transform': transform,
        'width': width,
        'height': height,
        'nodata': 0,
        'dtype': 'uint8',
        'count': 1,
    }
    # Fetch model
    s3 = boto3.client('s3')
    data = s3.get_object(Bucket=bucket, Key='{}/model.h5'.format(project_id),)['Body'].read()
    model = load_model(h5py.File(io.BytesIO(data)))
    # Predict.
    result = model.predict_classes(X)
    memfile = MemoryFile()
    with memfile.open(**creation_args) as rst:
        rst.write(result.reshape(1, height, width).astype('uint8'))
    memfile.seek(0)
    # Upload result to bucket.
    s3.put_object(
        Bucket=bucket,
        Key='{project_id}/result.tif'.format(
            project_id=project_id,
        ),
        Body=memfile,
    )
