import glob
import io
import math

import boto3
import numpy
import numpy as np
from tensorflow import keras

from pixels.clouds import pixels_mask
from pixels.generator import generator_augmentation_2D
from pixels.generator.visualizer import visualize_in_item

# S3 class instanciation.
s3 = boto3.client("s3")


# Defining cloud mask to apply
def cloud_filter(X, bands=[8, 7, 6, 2, 1, 0, 9]):
    mask = pixels_mask(
        X[:, bands[0]],
        X[:, bands[1]],
        X[:, bands[2]],
        X[:, bands[3]],
        X[:, bands[4]],
        X[:, bands[5]],
        X[:, bands[6]],
    )
    return mask


class DataGenerator_NPZ(keras.utils.Sequence):
    """
    Defining class for generator.
    """

    def __init__(
        self,
        path_work,
        split=1,
        train=True,
        train_split=[],
        shuffle=False,
        mode="PIXEL",
        num_time=12,
        seed=None,
        upsampling=False,
        bands=[8, 7, 6, 2, 1, 0, 9],
        cloud_mask_filter=True,
        augmentation=False,
        batch_size=None,
    ):
        self.length = None
        self.bucket = None
        self.shuffle = shuffle
        self.batch_size = batch_size
        self.cloud_cover = 0.7
        self.mode = mode
        self.num_time = num_time
        self.upsampling = upsampling
        self.bands = bands
        self.showerror = True
        self.cloud_mask_filter = cloud_mask_filter
        self.augmentation = augmentation
        self.auxind = None

        self.files_ID = self.get_files(path_work)
        self.data_base_size = len(self.files_ID)
        self.set_train_test(train, train_split, split, seed)

    def __len__(self):
        """
        Denotes the number of batches per epoch.
        Each step is a file read, which means that the total number of steps is the number of files avaible
        (data_base_size * split).
        """
        return self.length

    def set_train_test(self, train, train_split, split, seed):
        """
        Builds train or test list of files to open
        """
        if train_split:
            self.list_IDs = np.setdiff1d(self.files_ID, train_split)
        else:
            # Compute desired length based on slpit.
            split_length = math.floor(self.data_base_size * split)
            # Build a list of indexes, steps_per_epoch size, choosing randomly.
            np.random.seed(seed)
            indexes = np.random.choice(self.data_base_size, split_length, replace=False)
            # If a for test, the indexes are update for the all the other ones left behind.
            if not train:
                indexes = np.setdiff1d(np.arange(self.data_base_size), indexes)
            # Fetch the actual paths based on the indexes
            self.list_IDs = [self.files_ID[k] for k in indexes]
        # The default length of the iterator is the number of files available.
        self.length = len(self.list_IDs)
        # If a batch size was specified, reduce the length accordingly.
        if self.batch_size:
            self.length = math.floor(self.length / self.batch_size)
        # Increase size if augmentation is active.
        if self.augmentation:
            self.length *= generator_augmentation_2D.AUGMENTATION_FACTOR

        return self.length

    def get_files(self, path_work, sufix="npz"):
        """
        Returns the path to all npz files under path_work directory.

        If path_work starts with s3://my-bucket-name/my/prefix/path, files are searched on S3.
        """
        if path_work.startswith("s3://"):
            # Prepare files list.
            files = []
            # Split input path into bucket and prefix path.
            path_work_split = path_work.split("s3://")[1].split("/")
            self.bucket = path_work_split[0]
            prefix = "/".join(path_work_split[1:])
            # Create paginator.
            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
            )
            # Get keys using paginator.
            for page in pages:
                for obj in page["Contents"]:
                    files.append(obj["Key"])
        else:
            files = glob.glob(path_work + "**/*" + sufix, recursive=True)

        return files

    # def on_epoch_end(self):
    #     """On epoch feature
    #     Updates indexes after each epoch
    #     Default is off, shuffle=True to turn on
    #     """
    #     indexes = np.random.choice(self.data_base_size, self.length, replace=False)
    #     if self.shuffle:
    #         np.random.shuffle(self.indexes)
    #         self.list_IDs = [self.files_ID[k] for k in indexes]

    def get_item_path(self, index):
        if self.augmentation:
            return self.list_IDs[
                math.floor(index / generator_augmentation_2D.AUGMENTATION_FACTOR)
            ]
        else:
            return self.list_IDs[index]

    def __getitem__(self, index):
        """Generate one batch of data"""
        # Generate the data from given file (index)
        # Find list of IDs
        IDs_temp = self.get_item_path(index)
        IDs_temp = [IDs_temp]
        if self.batch_size:
            idx = self.list_IDs[: self.batch_size]
            if self.auxind:
                self.auxind = self.auxind + self.batch_size
                idx = self.list_IDs[self.auxind : self.auxind + self.batch_size]
            # np.random.randint(len(self.list_IDs), size=self.batch_size)
            # IDs_temp = np.take(self.list_IDs, idx).tolist()
            IDs_temp = idx
            self.auxind = 0
        # Generate data
        # The try and excepts are in case a file does not have a single valid outuput
        try:
            X, y = self._data_generation(IDs_temp)
            if self.upsampling:
                X = self.upscale_tiles(X, factor=self.upsampling)
            if self.augmentation:
                # Compute which augmentation version is required.
                augmentation_index = (
                    index % generator_augmentation_2D.AUGMENTATION_FACTOR
                )
                X, y = generator_augmentation_2D.augmentation(
                    X, y, augmentation_index=augmentation_index
                )
        except Exception as e:
            raise
            if self.showerror:
                print(e)
            # new_index = np.random.choice(len(self.list_IDs), 1, replace=False)[0]
            # X, y = self.__getitem__(new_index)
            if index == 0:
                X, y = self.__getitem__(index + 2)
            else:
                X, y = self.__getitem__(index - 1)
        return X, y

    def _pixel_generation(self, X, Y, mask):
        """
        Specific function to fecth the data pixel by pixel
        """
        # Shape -> (time_steps, bands, dim, dim)
        # Change shape
        X = np.swapaxes(X, 1, 2)
        X = np.swapaxes(X, 2, 3)
        # Shape -> (time_steps, dim, dim, bands)
        X = np.swapaxes(X, 0, 1)
        X = np.swapaxes(X, 1, 2)
        # Shape -> (dim, dim, time_steps, bands)
        # Tuple for flatten shape
        shp = list(X.shape[2:])
        shp.insert(0, np.prod(X.shape[:2]))
        # Reshape to ->(dim*dim, time_steps, bands)
        X = X.reshape(shp)
        Y = Y.reshape(np.prod(Y.shape))

        # Reshape mask
        mask = np.swapaxes(mask, 0, 1)
        mask = np.swapaxes(mask, 1, 2)
        shp = list(mask.shape[2:])
        shp.insert(0, np.prod(X.shape[:1]))
        mask = mask.reshape(shp)
        # Initiate empty arrays
        tensor_X = []
        tensor_Y = []
        # Iterate over the data and the cloud mask
        for (x, y, m) in zip(X, Y, mask):
            # if y not 0 or NAN carry on
            if y == np.nan or y == 9999 or y != y or y == 0:
                continue
            # Apply cloud mask
            x = x[np.logical_not(m)]
            # Pad short sequences.
            if x.shape[0] < self.num_time:
                x = np.vstack((x, np.zeros((self.num_time - x.shape[0], *x.shape[1:]))))
            # Append given results. self.num_time is the number of timeseries to include
            # TODO: include as a atribute in the class
            tensor_X.append(x[: self.num_time])
            tensor_Y.append(y)
        return np.array(tensor_X), np.array(tensor_Y)

    def get_array(self, array, only=None):
        """
        Get an all the data from given array of paths
        """
        # Create empty arrays
        tensor_X = []
        tensor_Y = []
        for path in array:
            try:
                X, y = self._data_generation([path])
                if self.upsampling:
                    X = self.upscale_tiles(X, factor=self.upsampling)
            except:
                continue
            if not only:
                tensor_X.append(X)
                tensor_Y.append(y)
            elif only == "X":
                tensor_X.append(X)
            elif only == "Y":
                tensor_Y.append(y)
        if not only:
            return np.array(tensor_X), np.array(tensor_Y)
        elif only == "X":
            return np.array(tensor_X)
        elif only == "Y":
            return np.array(tensor_Y)

    def upscale_tiles(self, X, factor=10):
        """
        Upscale incoming images by factor
        """
        if self.mode == "SINGLE_SQUARE":
            shp = np.array(X[0, :, :, 0].shape) * 10
            s = (*X.shape[:1], *shp, *X.shape[-1:])
            X_res = np.zeros(s)
            for time in range(len(X)):
                X_res[time] = generator_augmentation_2D.upscaling_sample(
                    X[time], factor
                )
        else:
            try:
                shp = np.array(X[0, 0, :, :, 0].shape) * 10
                s = (*X.shape[:2], *shp, *X.shape[-1:])
                X_res = np.zeros(s)
                for time in range(len(X[0])):
                    X_res[0][time] = generator_augmentation_2D.upscaling_sample(
                        X[0][time], factor
                    )
            except:
                if self.mode == "SINGLE_SQUARE":
                    shp = np.array(X[0, :, :, 0].shape) * 10
                    s = (*X.shape[:1], *shp, *X.shape[-1:])
                    X_res = np.zeros(s)
                    for time in range(len(X)):
                        X_res[time] = generator_augmentation_2D.upscaling_sample(
                            X[time], factor
                        )
                else:
                    shp = np.array(X[0, 0, :, :].shape) * 10
                    s = (*X.shape[:2], *shp)
                    X_res = np.zeros(s)
                    for time in range(len(X)):
                        for band in range(len(X[time])):
                            X_res[time][band] = generator_augmentation_2D.upscaling_sample(
                                X[time][band], factor
                            )
        return X_res

    def _data_generation(self, IDs_temp):
        """
        Generates data containing from a file.
        """
        # X : (n_samples, *dim, n_channels)
        # Initialization
        # Iterate over paths given. Important: There is always one path given, but it is important to have
        # an iteration to be able to use continue on no data cases
        # TODO: Find better way around this
        result_tensor_x = np.array([])
        result_tensor_y = np.array([])
        for path in IDs_temp:
            if self.bucket:
                data = s3.get_object(Bucket=self.bucket, Key=path)["Body"].read()
                data = numpy.load(io.BytesIO(data), allow_pickle=True)
            else:
                # Loading data from file. TODO: pass the file labels to class as an argument
                data = np.load(path, allow_pickle=True)
            # Extract images
            X = data["x_data"]
            X = np.array([np.array(x) for x in X if x.shape])
            # Make cloud mask
            mask = cloud_filter(X, self.bands)
            # Apply mask
            if self.cloud_mask_filter:
                for i in range(X.shape[1]):
                    X[:, i][mask] = 0
            # input data here
            # choose type of generator
            Y = data["y_data"]
            if self.mode == "SQUARE":
                # Build the output as a tensor of squares. Squares with all timesteps. (N, timesteps, size, bands)-> (1, 12, 360, 360, 10)
                tensor_X, tensor_Y = generator_augmentation_2D.generator_2D(X, Y, mask)
            if self.mode == "PIXEL":
                # Build output on a pixel level. (N, timesteps, bands)-> (1, 12, 10)
                tensor_X, tensor_Y = self._pixel_generation(
                    X, Y, mask, cloud_cover=self.cloud_cover
                )
            if self.mode == "SINGLE_SQUARE":
                # Build the output as as single image in time. (N, size, bands)-> (1, 360, 360, 10)
                tensor_X, tensor_Y = generator_augmentation_2D.generator_single_2D(
                    X, Y, mask, cloud_cover=(1 - self.cloud_cover)
                )
            if not np.any(np.array(tensor_X)):
                # TODO: change the way it acts when encounter a empty response
                continue
            if not result_tensor_x.any():
                result_tensor_x = np.array(tensor_X)
                result_tensor_y = np.array(tensor_Y)
            else:
                result_tensor_x = np.concatenate([result_tensor_x, np.array(tensor_X)])
                result_tensor_y = np.concatenate([result_tensor_y, np.array(tensor_Y)])
        return np.array(result_tensor_x), np.array(result_tensor_y)

    def visualize_item(
        self,
        index,
        in_out="IN",
        model=False,
        RGB=[8, 7, 6],
        scaling=1000,
        pred_show="not_binary",
    ):
        """
        Function to visualize image data
        """
        # Retain the original mode to change back in the end
        original_mode = self.mode
        if self.mode == 'PIXEL':
            print('Visualization not possibel in PIXEL mode')
            break
        # Initiate empty prediction
        prediction = False
        if in_out == "IN":
            IDs_temp = self.list_IDs[index]
            if self.bucket:
                data = s3.get_object(Bucket=self.bucket, Key=IDs_temp)["Body"].read()
                data = numpy.load(io.BytesIO(data), allow_pickle=True)
            else:
                # Loading data from file. TODO: pass the file labels to class as an argument
                data = np.load(IDs_temp, allow_pickle=True)
            X, Y = data["x_data"], data["y_data"]
            X = np.array([np.array(x) for x in X if x.shape])
            if self.upsampling:
                X = self.upscale_tiles(X, factor=self.upsampling)
        if in_out == "OUT":
            X, Y = self.__getitem__(index)
            if model:
                prediction = model.predict(X)
                # If the output is expected to be binary set prediciton to binary
                if pred_show == "binary":
                    prediction[prediction <= 0.5] = 0
                    prediction[prediction >= 0.5] = 1
        if original_mode == 'SINGLE_SQUARE':
            X = np.array([X])
        visualize_in_item(X, Y, prediction, in_out=in_out, RGB=RGB, scaling=scaling)
        self.mode = original_mode

    def get_prediction_inputs(self):
        """
        Yield only train data, used for predictions
        """
        for i in range(self.length):
            X, Y = self.__getitem__(i)
            yield X

    def flatten_time_len(self):
        counter = 0
        for i in range(self.length):
            X, Y = self.__getitem__(i)
            for t in range(len(X[0])):
                x = np.swapaxes(X[0][t], 1, 2)
                mask = cloud_filter(x, self.bands)
                if np.sum(mask) / (mask.size) > 1 - self.cloud_cover:
                    continue
                counter = counter + 1
        self.steps_no_time = counter

    def do_augmentation(self):
        if self.mode == 'SQUARE':
            print('s')
        elif self.mode == 'SINGLE_SQUARE':
            print('s')
