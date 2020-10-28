#!/usr/bin/env python3

import glob
import io
import json
import os

import boto3
import h5py
import numpy
from rasterio.io import MemoryFile
from tensorflow.keras import layers
from tensorflow.keras.models import Model, Sequential, load_model, model_from_json
from tensorflow.keras.utils import Sequence, plot_model, to_categorical

from pixels import utils

# Setup boto client.
s3 = boto3.client('s3')
# Fetch all data to memory.
bucket = os.environ.get('AWS_S3_BUCKET', 'tesselo-pixels-results')
project_id = os.environ.get('PROJECT_ID', 'test')
# config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
# config = json.loads(config['Body'].read())
paginator = s3.get_paginator('list_objects_v2')
pages = paginator.paginate(
    Bucket=bucket,
    Prefix='{}/training/'.format(project_id),
)
result = []
# for page in pages:
#     for obj in page['Contents']:
#         print(obj['Size'])
#         data = s3.get_object(
#             Bucket=bucket,
#             Key=obj['Key']
#         )['Body'].read()
#         data = numpy.load(io.BytesIO(data), allow_pickle=True)
#         result.append(data)
Xs = []
Ys = []
ids = []
valuemap = {}
for path in glob.glob('/home/tam/Desktop/pixels_test/pixels_data/*.npz'):
    with open(path, 'rb') as fl:
        data = numpy.load(fl, allow_pickle=True)
        X = data['data']
        X = X.swapaxes(0, 2).swapaxes(1, 3)
        X = X.reshape(X.shape[0] * X.shape[1], X.shape[2], X.shape[3])
        # Remove zeros.
        X = X[numpy.sum(X, axis=(1, 2)) != 0]
        Xs.append(X)
        Y = data['feature'].item()['features'][0]['properties']['Class']
        id = data['feature'].item()['features'][0]['id']
        if Y not in valuemap:
            valuemap[Y] = len(valuemap)
        Ys.append([valuemap[Y]] * X.shape[0])
        ids.append([id] * X.shape[0])

Xs = numpy.vstack(Xs).astype('float32')
Ys = numpy.hstack(Ys)
ids = numpy.hstack(ids)

unique_ids = numpy.unique(ids)
splitfraction = 0.2
selected_ids = numpy.random.choice(
    unique_ids,
    int(len(unique_ids) * (1 - splitfraction)),
    replace=False,
)
selector = numpy.in1d(ids, selected_ids)
X_train = Xs[selector]
Y_train = to_categorical(Ys[selector])
X_test = Xs[numpy.logical_not(selector)]
Y_test = to_categorical(Ys[numpy.logical_not(selector)])

# Build the model.
# model = model_from_json(json.dumps(config['keras_model']))
model = Sequential()
model.add(layers.BatchNormalization())
model.add(layers.Conv1D(filters=64, kernel_size=3, activation='relu'))
model.add(layers.Dropout(0.5))
model.add(layers.BatchNormalization())
model.add(layers.Conv1D(filters=64, kernel_size=3, activation='relu'))
model.add(layers.Dropout(0.3))
model.add(layers.BatchNormalization())
model.add(layers.MaxPooling1D(pool_size=2))
model.add(layers.Flatten())
model.add(layers.Dense(100, activation='relu'))
model.add(layers.Dense(len(valuemap), activation='softmax'))

visible = layers.Input(shape=(25, 10))
normed = layers.BatchNormalization()(visible)
# dropped = Dropout(0.2)(normed)
# first feature extractor
conv1 = layers.Conv1D(filters=64, kernel_size=3, activation='relu')(normed)
normed1 = layers.BatchNormalization()(conv1)
dropped1 = layers.Dropout(0.25)(normed1)
convd1 = layers.Conv1D(filters=64, kernel_size=3, activation='relu')(dropped1)
normed11 = layers.BatchNormalization()(convd1)
pool1 = layers.MaxPooling1D(pool_size=2)(normed11)
flat1 = layers.Flatten()(pool1)
# second feature extractor
conv2 = layers.Conv1D(filters=64, kernel_size=6, activation='relu')(normed)
normed2 = layers.BatchNormalization()(conv2)
dropped2 = layers.Dropout(0.25)(normed2)
convd2 = layers.Conv1D(filters=64, kernel_size=6, activation='relu')(dropped2)
normed22 = layers.BatchNormalization()(convd2)
pool2 = layers.MaxPooling1D(pool_size=2)(normed22)
flat2 = layers.Flatten()(pool2)
# merge feature extractors
merge = layers.concatenate([flat1, flat2])
dropped = layers.Dropout(0.5)(merge)
# interpretation layer
hidden1 = layers.Dense(100, activation='relu')(dropped)
normed3 = layers.BatchNormalization()(hidden1)
# prediction output
output = layers.Dense(13, activation='softmax')(normed3)
model = Model(inputs=visible, outputs=output)


# Compile the model.
config = {}
compile_parms = config.get('keras_compile_arguments', {
    'optimizer': 'rmsprop',
    'loss': 'categorical_crossentropy',
    'metrics': ['accuracy'],
})
model.compile(**compile_parms)

# Fit the model.
fit_parms = config.get('keras_fit_arguments', {
    'epochs': 5,
    'batch_size': 100,
})
model.fit(X_train, Y_train, **fit_parms)

print("Evaluate on test data")
results = model.evaluate(X_test, Y_test, batch_size=128)
print("test loss, test acc:", results)
