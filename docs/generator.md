# Pixels Data Generator
A [Generator](https://github.com/tesselo/pixels/blob/main/pixels/generator/generator.py) is used to feed pixels data to our AI models. This generator transforms the raw imagery stacks from the pixels collection into a format that can be passed to an AI model.

For super-resolution models, the generator is able to change the resolution of the imagery data.

The generator can make data augmentation, which provides slightly altered copies of the imagery to the model for additional training (mirrored images, flipped images, etc).

The generator is also responsible to split the data into training and evaluation datasets.

The main difficulty in specifying the generator arguments are to properly align the input imagery with the model architecture.

## Arguments

### Collection

`path_collection_catalog`: string

Path to the dictionary containing the training set. Either remotely or locally. Has to be a catalogs_dict.json file.

`split`: float

Value between 0 and 1. Percentage of dataset to use.

`training_percentage`: float

Value between 0 and 1. Percentage of dataset to use if in training mode or percentage used for training if in evaluation mode.
In training it is the variable that decides the split.

`random_seed`: int

Numpy random seed. To randomize the dataset choice.

### Modes
There are 3 main modes for the generator, which define the core behavior:

`usage_type` : string
  - `training`→ For use on model training, the output is an X and a Y.
  - `prediction`→ Used for prediction, it only outputs the X.
  - `evaluation`→ For evaluation, outputs all the data left behind in the training.

### Model types
Then there are 3 current model types on use, each one making a different generator behavior.

`mode` : string
  - `3D_Model`→ An image with multiple time steps. X output shape: (N, time steps, height, width, number of bands)
  - `2D_Model`→ One image model. X output shape: (N, height, width, number of bands).
  - `Pixel_Model`→ Model pixel based. X output shape: (N, time steps, number of bands)
  - `RESNET_3D_Model`→ A Pixel with framed context with multiple time steps. X output shape: (N, time steps, 3, 3, number of bands)
  - `RESNET_2D_Model`→ A Pixel with framed context. X output shape: (N, 3, 3, number of bands).

### Image

`height`: int

Height of X image, in pixels. Value not considered in Pixel Mode.

`width`: int

Width of X image, in pixels. Value not considered in Pixel Mode.

`y_height`: int, optional

Height of Y image, in pixels. Only use if X and Y are different sizes. Value not considered in Pixel Mode.

`y_width`: int, optional

Width of y image, in pixels. Only use if X and Y are different sizes. Value not considered in Pixel Mode.

`num_bands`: int

Number of bands in the X images.
- Sentinel-2: 10
- LandSat-8: 7

`num_classes`: int

Number of classes in Y data. If the mode is Y-Image and there are nan_values to ignore, then the number of classes must include an additional last class for nan_values.

### Image Processing

`upsampling`: int

Number of time to up-sample the X data. This value needs to be set so that the
up-sampled X images will match exactly the input shape required by the model.

Default : 1

`padding`: int

Number of pixels to add as padding (a frame around the image).

Default : 0

`y_padding`: int

Number of pixels to add as padding on Y (a frame around the image).

Default : 0

`y_padding`: int
Number of pixels to add as padding on Y (a frame around the image).
Default : 0

`padding_mode`: string

Padding mode, from numpy.pad().

Default : "edge"

`framed_window`: int

Size of frame around pixel in ResNET.

Default : 3

`augmentation`: int

Number of augmentation to do.

Default : 0

`batch_number`: int

Number of batch to do.

Default : 1

`x_nan_value`: float

Value to ignore on X data. This either masks out the values on pixel mode, or informs the loss function of what is to ignore.

Default : 0

`y_nan_value`: float

Value to ignore on Y data. This masks out the values on pixel mode. This should
be set to -9999 if a custom loss function is used in the model.

`nan_value`: float

Same as y_nan_value, legacy argument still used in the pipeline.

`cloud_sort`: bool

Boolean to order x_imgs by cloud density.

### Classification

`class_definitions`: int or list

Values to define the Y classes. If int is a number of classes, if a list it is the classes.

`y_max_value`: float

Needed for class definition with number of classes.

`class_weights`: dict

Dictionary containing the weight of each class.

`one_hot`: bool

Boolean to set multiclass as sparse or one_hot.

Default: True

### Optimizing performance

`normalization`: numerical

This parameter is to normalize the input values to a range of 0 to 1. Neural
networks train better on normalized data. All the pixels data in the X value
will be normalized from 0 to 1 using the normalization value as the maximum
value. The normalization expressed as a numpy code snippet is the following:
`x_norm = numpy.clip(x, 0, normalization)`. Recommended values are 10000 for
Sentinel-2, and 65535 for Landsat-8.

`shuffle`: bool

Determines if the available data shall be shuffled randomly before each epoch.
Randomizing the order of the input data helps the model converge faster during
training. This is set to false if not in training mode. Default: True.

### Data storage

`download_data`: bool

If True, and the data is not local, it will first download everything locally.

`download_dir`: str

Path to for the downloaded data directory. If `download_dir` is not set and 
`download_data` is `True`, a temporary directory will be created automatically.

## Supporting arguments
This section documents a number of arguments that can be set as generator
arguments in the stac training algorithm, that are not direct arguments of the
Generator. These additional arguments are related with formatting the input
and output of the models, as well as handling special cases during prediction.

### Variable prediction image size
If the size of the input images for prediction is bigger than the model input,
there is going to be a moving window inside that image. For each window within
the image, a prediction will be made. For overlapping sections, an average from
the moving window predictions will be calculcated and stored as result. The
final output will have the size of the input image.

The arguments for using this feature are:

`jump_pad`: a padding done in the moving window. A frame around the actual image.

`jumping_ratio`: The ratio in which every step is given. For instance, with a value of 1 no two images will overlap, since the step will be the size of the window. With a value of 0.5 every half of window will overlap with the next, step being window size x 0.5.

### Output scaling
`extract_probabilities`:

Determine if the probability of each class will be storedin bands instead of
having a single band with the class DN.

Default: False

`rescale_probabilities`:

Determine if the probabilities will be rescaled to UInt8 integers from 0 to 255
(0.3% increments). This will save space and make things faster. It also applies
to single class predictions.

Default: False

`clip_range`: tuple

Tuple with a range to clip the predictions. If the range exists, apart from the clip it will be rescale to [0,255] and dtype to uint8.

Default: False

### Collecting pixels in one array
For specific cases it is beneficial to collect all available data into one
single array before training. This is possible with the following argument:

`train_with_array`: bool

Determine if all input data should be collected into a single array to perform
the model fit. This can increase training and convergence speeds substantially
Note that this will only work on small datasets that fit into memory on the
server instances, for instance for 1D models.

Default: False
