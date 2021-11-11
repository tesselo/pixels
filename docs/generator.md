# Pixels Data Generator
A data generator is used to feed pixels data to our AI models. This generator transforms the raw imagery stacks from the pixels collection into a format that can be passed to an AI model.

For super-resolution models, the generator is able to change the resolution of the imagery data.

The generator can make data augmentation, which provides slightly altered copies of the imagery to the model for additional training (mirrored images, flipped images, etc).

The generator is also responsible to split the data into training and evaluation datasets.

The main difficulty in specifying the generator arguments are to properly align the input imagery with the model architecture.

## Arguments

### Collection
&quot;path_collection_catalog&quot; : string
Path to the dictonary containing the training set. Either in s3 or locally. Has to be a catalogs_dict.json file.
&quot;split&quot; : float
Value between 0 and 1. Percentage of dataset to use.
&quot;training_percentage&quot; : float
Value between 0 and 1. Percentage of dataset to use if in training mode or percentage used for training if in evaluation mode.
In training it is the variable that decides the split.
&quot;random_seed&quot; : int
Numpy random seed. To randomize the dataset choice.

### Modes
There are 3 main modes for the generator, which define the core behavior:

- &quot;training&quot; → For use on model training, the output is an X and a Y.
- &quot;prediction&quot; → Used for prediction, it only outputs the X.
- &quot;evaluation&quot; → For evaluation, outputs all the data left behind in the training.

### Model types
Then there are 3 current model types on use, each one making a different generator behavior.

- &quot;3D_Model&quot; → An image with multiple time steps. X output shape: (N, time steps, height, width, number of bands)
- &quot;2D_Model&quot; → One image model. X output shape: (N, height, width, number of bands).
- &quot;Pixel_Model&quot; → Model pixel based. X output shape: (N, time steps, number of bands)

### Image
&quot;height&quot; : int
Height of X image, in pixels. Value not considered in Pixel Mode.
&quot;width&quot; : int
Width of X image, in pixels. Value not considered in Pixel Mode.
&quot;num_bands&quot; : int
Number of bands in the X images.
Sentinel-2: 10
LandSat-8: 7
&quot;num_classes&quot; : int
Number of classes in Y data.
#### Image Processing
&quot;upsampling&quot; : int
Number of time to upsample the X data.
Standard : 1
&quot;padding&quot; : int
Number of pixels to add as padding (a frame around the image).
Standard : 0
&quot;padding_mode&quot; : string
Padding mode, from numpy.pad().
Standard : "edge"
&quot;augmentation&quot; : int
Number of augmentation to do.
Standard : 0
&quot;batch_number&quot; : int
Number of batch to do.
Standard : 1
&quot;x_nan_value&quot; : float
Value to ignore on X data. This either masks out the values on pixel mode, or informs the loss function of what is to ignore.
Standard : 0
&quot;y_nan_value&quot; : float
Value to ignore on Y data. This masks out the values on pixel mode.
&quot;nan_value&quot; : float
Same as y_nan_value, legacy argument still used in the pipeline.

### Classification
&quot;class_definitions&quot; : int or list
Values to define the Y classes. If int is a number of classes, if a list it is the classes.
&quot;y_max_value&quot; : float
Needed for class definition with number of classes.
&quot;class_weights&quot; : dict
Dictionary containing the weight of each class.

### Normalization
The normalization parameter should be a numeric value. All the pixels data in
the X value will be normalized from 0 to 1, using the normalization value as
the maximum value. The normalization expressed as a numpy code snippet is the
following: `x_norm = numpy.clip(x, 0, normalization)`.
Sentinel-2 : 10000
LandSat-8: 65535

### Data storage
&quot;download_data&quot; : bool
If True, and the data is not local, it will first download everything locally.
&quot;temp_dir&quot; : str
Path to temporary folder created in stac, for the download data.

### Prediction specific arguments
If the size of the input images for prediction is bigger than the model input, there is going to be a moving window inside that image. For each window within the image, a prediction will be made. For overlapping sections, an average from the moving window predictions will be calculcated and stored as result. The final output will have the size of the input image.

The arguments for using this feature are:

- jump_pad: a padding done in the moving window. A frame around the actual image.
- jumping_ratio: The ratio in which every step is given. For instance, with a value of 1 no two images will overlap, since the step will be the size of the window. With a value of 0.5 every half of window will overlap with the next, step being window size x 0.5.

#### Output formats
`extract_probabilities` will extract the probability of each class in bands instead of having a single band with the class DN.

`rescale_probabilities` will rescale the probabilities to 0 to 255 (0.3% increments). This will save space and make things faster. It also applies to single class predictions.


## Biggest concerns
The generator must be informed of the size of the images it is going to read as the X. For instance if squares of 10x10 pixels:

- height = 10
- width = 10

If the goal image is on a higher resolution, Y images being 100x100 pixels:

- upsampling = 10

Values with input needed:

- num_bands = 10 ( Sentinel2)
- timesteps = 12
- y_nan_value = -9999 (if custom loss function)

## Reference
The current accepted parameters for the [DataGenerator](https://github.com/tesselo/pixels/blob/main/pixels/generator/generator.py#L43) class and their defaults are:

```python
{
  path_collection_catalog="",
  split=1,
  random_seed=None,
  timesteps=None,
  width=None,
  height=None,
  num_bands=None,
  num_classes=1,
  upsampling=1,
  mode=GENERATOR_3D_MODEL,
  batch_number=1,
  padding=0,
  x_nan_value=0,
  y_nan_value=None,
  nan_value=None,
  padding_mode="edge",
  dtype=None,
  augmentation=0,
  training_percentage=1,
  usage_type=GENERATOR_MODE_TRAINING,
  class_definitions=None,
  y_max_value=None,
  class_weights=None,
  download_data=False,
  temp_dir=None,
  normalization=None,
}
```
