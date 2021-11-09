# Pixels Data Generator
A data generator is used to feed pixels data to our AI models. This generator transforms the raw imagery stacks from the pixels collection into a format that can be passed to an AI model.

For super-resolution models, the generator is able to change the resolution of the imagery data.

The generator can make data augmentation, which provides slightly altered copies of the imagery to the model for additional training (mirrored images, flipped images, etc).

The generator is also responsible to split the data into training and evaluation datasets.

The main difficulty in specifying the generator arguments are to properly align the input imagery with the model architecture.

## Prediction specific arguments
If the size of the input images for prediction is bigger than the model input, there is going to be a moving window inside that image. For each window within the image, a prediction will be made. For overlapping sections, an average from the moving window predictions will be calculcated and stored as result. The final output will have the size of the input image.

The arguments for using this feature are:

- jump_pad: a padding done in the moving window. A frame around the actual image.
- jumping_ratio: The ratio in which every step is given. For instance, with a value of 1 no two images will overlap, since the step will be the size of the window. With a value of 0.5 every half of window will overlap with the next, step being window size x 0.5.

## Normalization
The normalization parameter should be a numeric value. All the pixels data in
the X value will be normalized from 0 to 1, using the normalization value as
the maximum value. The normalization expressed as a numpy code snippet is the
following: `x_norm = numpy.clip(x, 0, normalization)`.

## Modes
There are 3 main modes for the generator, which define the core behavior:

- &quot;training&quot; → For use on model training, the output is an X and a Y.
- &quot;prediction&quot; → Used for prediction, it only outputs the X.
- &quot;evaluation&quot; → For evaluation, outputs all the data left behind in the training.

## Model types
Then there are 3 current model types on use, each one making a different generator behavior.

- &quot;3D_Model&quot; → An image with multiple time steps. X output shape: (N, time steps, height, width, number of bands)
- &quot;2D_Model&quot; → One image model. X output shape: (N, height, width, number of bands).
- &quot;Pixel_Model&quot; → Model pixel based. X output shape: (N, time steps, number of bands)

## Output formats
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
