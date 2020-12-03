#!/usr/bin/env python3

import glob
import io
import os

import boto3
import numpy
import tensorflow
from tensorflow.keras import layers
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.utils import to_categorical

from pixels.clouds import combined_mask

# Setup tensorflow session for model to use GPU.
config = tensorflow.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
session = tensorflow.compat.v1.InteractiveSession(config=config)
### Remove in production.
# # Setup boto client.
# s3 = boto3.client("s3")
# # Fetch all data to memory.
# bucket = os.environ.get("AWS_S3_BUCKET", "tesselo-pixels-results")
# project_id = os.environ.get("PIXELS_PROJECT_ID", "replant")
# # config = s3.get_object(Bucket=bucket, Key=project_id + '/config.json')
# # config = json.loads(config['Body'].read())
# paginator = s3.get_paginator("list_objects_v2")
# pages = paginator.paginate(
#     Bucket=bucket,
#     Prefix="{}/training/".format(project_id),
# )
# result = []
# for page in pages:
#     print(page["KeyCount"])
#     for obj in page["Contents"]:
#         print(obj["Size"])
#         data = s3.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
#         data = numpy.load(io.BytesIO(data), allow_pickle=True)
#         result.append(data)
# numpy.savez_compressed('/home/tam/Desktop/replant_result_array.npz', result)
result = numpy.load("/home/tam/Desktop/replant_result_array.npz")["arr_0"].item()

Xs = []
Ys = []
ids = []
valuemap = {}
# for path in glob.glob("/home/tam/Desktop/esb/esblandcover/training/*.npz"):
#     with open(path, "rb") as fl:
#         data = numpy.load(fl, allow_pickle=True)
for data in result:
    X = data["data"]
    # Data shape is ("scenes", bands, height, width)
    # cloud_mask = combined_mask(
    #     X[:, 8], X[:, 7], X[:, 6], X[:, 2], X[:, 1], X[:, 0], X[:, 9],
    # )
    # Reorder the data to have
    X = X.swapaxes(0, 2).swapaxes(1, 3)
    # Flatten the 2D data into pixel level.
    X = X.reshape(X.shape[0] * X.shape[1], X.shape[2], X.shape[3])
    # Remove zeros.
    X = X[numpy.sum(X, axis=(1, 2)) != 0]
    # Compute cloud and snow mask.
    # Assuming band order: ["B11", "B8A", "B08", "B07", "B06", "B05", "B04", "B03", "B02", "B12"],
    # cloud_mask = combined_mask(
    #     X[:, :, 8],
    #     X[:, :, 7],
    #     X[:, :, 6],
    #     X[:, :, 2],
    #     X[:, :, 1],
    #     X[:, :, 0],
    #     X[:, :, 9],
    # )
    # Mute cloudy pixels by setting them to zero.
    # X[cloud_mask] = 0
    Xs.append(X)
    Y = data["feature"].item()["features"][0]["properties"]["class"]
    id = data["feature"].item()["features"][0]["id"]
    if Y not in valuemap:
        print(Y, len(valuemap))
        valuemap[Y] = len(valuemap)
    Ys.append([valuemap[Y]] * X.shape[0])
    ids.append([id] * X.shape[0])

# Stack the training samples into one array.
Xs = numpy.vstack(Xs).astype("float32")
Ys = numpy.hstack(Ys)
ids = numpy.hstack(ids)

# Split in training and evaluation dataset.
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
# model = Sequential()
# model.add(layers.BatchNormalization())
# model.add(layers.Conv1D(filters=64, kernel_size=3, activation='relu'))
# model.add(layers.Dropout(0.5))
# model.add(layers.BatchNormalization())
# model.add(layers.Conv1D(filters=64, kernel_size=3, activation='relu'))
# model.add(layers.Dropout(0.3))
# model.add(layers.BatchNormalization())
# model.add(layers.MaxPooling1D(pool_size=2))
# model.add(layers.Flatten())
# model.add(layers.Dense(100, activation='relu'))
# model.add(layers.Dense(len(valuemap), activation='softmax'))

# model = Sequential()
# model.add(layers.BatchNormalization())
# model.add(layers.GRU(300, return_sequences=False, return_state=False, dropout=0.5, recurrent_dropout=0.5))
# model.add(layers.BatchNormalization())
# model.add(layers.Dense(100, activation='relu'))
# model.add(layers.Dense(len(valuemap), activation='softmax'))

visible = layers.Input(shape=X_train.shape[1:])
normed = layers.BatchNormalization()(visible)
# first feature extractor
conv1 = layers.Conv1D(filters=64, kernel_size=3, activation="relu")(normed)
normed1 = layers.BatchNormalization()(conv1)
dropped1 = layers.Dropout(0.5)(normed1)
convd1 = layers.Conv1D(filters=64, kernel_size=3, activation="relu")(dropped1)
normed11 = layers.BatchNormalization()(convd1)
pool1 = layers.MaxPooling1D(pool_size=2)(normed11)
flat1 = layers.Flatten()(pool1)
# second feature extractor
conv2 = layers.Conv1D(filters=64, kernel_size=6, activation="relu")(normed)
normed2 = layers.BatchNormalization()(conv2)
dropped2 = layers.Dropout(0.5)(normed2)
convd2 = layers.Conv1D(filters=64, kernel_size=6, activation="relu")(dropped2)
normed22 = layers.BatchNormalization()(convd2)
pool2 = layers.MaxPooling1D(pool_size=2)(normed22)
flat2 = layers.Flatten()(pool2)
# merge feature extractors
merge = layers.concatenate([flat1, flat2])
dropped = layers.Dropout(0.5)(merge)
# interpretation layer
hidden1 = layers.Dense(100, activation="relu")(dropped)
normed3 = layers.BatchNormalization()(hidden1)
dropped3 = layers.Dropout(0.5)(normed3)
# prediction output
output = layers.Dense(len(valuemap), activation="softmax")(dropped3)
model = Model(inputs=visible, outputs=output)

# Compile the model.
config = {}
compile_parms = config.get(
    "keras_compile_arguments",
    {
        "optimizer": "rmsprop",
        "loss": "categorical_crossentropy",
        "metrics": ["accuracy"],
    },
)
model.compile(**compile_parms)

# Fit the model.
fit_parms = config.get(
    "keras_fit_arguments",
    {
        "epochs": 50,
        "batch_size": 10000,
        "verbose": 1,
    },
)
model.fit(X_train, Y_train, **fit_parms)
# model.summary()

# Y_predicted = model.predict(X_test)
# Y_predicted = numpy.argmax(Y_predicted, axis=1) + 1

print("Evaluate on test data")
results = model.evaluate(X_test, Y_test, batch_size=1000)
print("test loss, test acc:", results)

# Compute accuracy matrix and coefficients.
# accuracy_matrix = confusion_matrix(y_test, y_predicted).tolist()
# cohen_kappa = cohen_kappa_score(y_test, y_predicted)
# accuracy_score = accuracy_score(y_test, y_predicted)
