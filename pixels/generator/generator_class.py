import glob


import numpy as np
from pixels.generator.generator_augmentation_2D import upscaling_sample
from tensorflow import keras
from pixels.generator.visualizer import visualize_in_item

from pixels.clouds import pixels_mask


# Defining cloud mask to apply
def cloud_filter(X):
    mask = pixels_mask(X[:, 8], X[:, 7], X[:, 6], X[:, 2], X[:, 1], X[:, 0], X[:, 9])
    return mask


# Defining class for generator
class DataGenerator_NPZ(keras.utils.Sequence):
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
    ):
        self.files_ID = self.get_files(path_work)
        self.DataBaseSize = len(self.files_ID)
        self.shuffle = shuffle
        self.steps_per_epoch = int(len(self.files_ID) * split)
        self.set_train_test(train, train_split, split, seed)
        self.cloud_cover = 0.7
        self.mode = mode
        self.num_time = num_time
        self.upsampling = upsampling

    def __len__(self):
        """Denotes the number of batches per epoch
        Each step is a file read, which means that the total number of steps is the number of files avaible
        (DataBaseSize * split).
        """
        return self.steps_per_epoch

    def get_files(self, path_work, sufix="npz"):
        """Returns the path to all npz files under path_work directory"""
        files = glob.glob(path_work + "**/*" + sufix, recursive=True)
        return files

    def on_epoch_end(self):
        """On epoch feature
        Updates indexes after each epoch
        Default is off, shuffle=True to turn on
        """
        indexes = np.random.choice(
            self.DataBaseSize, self.steps_per_epoch, replace=False
        )
        if self.shuffle:
            np.random.shuffle(self.indexes)
            self.list_IDs = [self.files_ID[k] for k in indexes]

    def set_train_test(self, train, train_split, split, seed=None):
        """
        Builds train or test list of files to open
        """
        # Build a list of indexes, steps_per_epoch size, choosing randomly
        np.random.seed(seed)
        indexes = np.random.choice(
            self.DataBaseSize, self.steps_per_epoch, replace=False
        )
        # If a for test, the indexes are update for the all the other ones left behind
        if not train:
            indexes = np.setdiff1d(np.arange(self.DataBaseSize), indexes)
        # Fetch the actual paths based on the indexes
        self.list_IDs = [self.files_ID[k] for k in indexes]
        # If it is a test and there is a given train dataset, fetches all the others
        if not train:
            if train_split:
                self.list_IDs = np.setdiff1d(self.files_ID, train_split)
            self.steps_per_epoch = len(self.list_IDs)

    def __getitem__(self, index):
        """Generate one batch of data"""
        # Generate the data from given file (index)
        # Find list of IDs
        IDs_temp = self.list_IDs[index]
        # Generate data
        # The try and excepts are in case a file does not have a single valid outuput
        try:
            X, y = self._data_generation([IDs_temp])
        except:
            # index = np.random.choice(len(self.list_IDs), 1, replace=False)[0]
            if index == 0:
                X, y = self.__getitem__(index + 2)
            else:
                X, y = self.__getitem__(index - 1)
        if self.upsampling:
            X = self.upscale_tiles(X, factor=self.upsampling)
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

    def get_array(self, array):
        """
        Get an all the data from given array of paths
        """
        tensor_X = []
        tensor_Y = []
        for path in array:
            try:
                X, y = self._data_generation([path])
            except:
                continue
            tensor_X.append(X)
            tensor_Y.append(y)
        return np.array(tensor_X), np.array(tensor_Y)

    def _data_generation(self, IDs_temp):
        """Generates data containing from a file"""
        # X : (n_samples, *dim, n_channels)
        # Initialization
        # Iterate over paths given. Important: There is always one path given, but it is important to have
        # an iteration to be able to use continue on no data cases
        # TODO: Find better way around this
        for path in IDs_temp:
            # Loading data from file. TODO: pass the file labels to class as an argument
            data = np.load(path, allow_pickle=True)
            # Make cloud mask
            mask = cloud_filter(data["x_data"])
            # Extract images
            X = data["x_data"]
            # Apply mask
            for i in range(X.shape[1]):
                X[:, i][mask] = 0

            # input data here
            # choose type of generator
            Y = data["y_data"]
            if self.mode == "SQUARE":
                tensor_X, tensor_Y = generator_augmentation_2D.generator_2D(X, Y, mask)
            if self.mode == "PIXEL":
                # Build results on a pixel level
                tensor_X, tensor_Y = self._pixel_generation(X, Y, mask)

            if not np.any(np.array(tensor_X)):
                # TODO: change the way it acts when encounter a empty response
                continue
            return np.array(tensor_X), np.array(tensor_Y)

    def upscale_tiles(self, X, factor=10):
        shp = np.array(X[0, 0, :, :, 0].shape) * 10
        X_res = np.zeros((*X.shape[:2], *shp, *X.shape[-1:]))
        for time in range(len(X[0])):
            X_res[0][time] = upscaling_sample(X[0][time], factor)
        return X_res

    def visualize_item(self, index, mode="SQUARE", in_out="IN", model=False):
        original_mode = self.mode
        self.mode = mode
        prediction = False
        if in_out == "IN":
            IDs_temp = self.list_IDs[index]
            data = np.load(IDs_temp, allow_pickle=True)
            X, Y = data["x_data"], data["y_data"]
        if in_out == "OUT":
            X, Y = self.__getitem__(index)
            if model:
                prediction = model.predict(X)
        visualize_in_item(X, Y, prediction, in_out=in_out)
        self.mode = original_mode
