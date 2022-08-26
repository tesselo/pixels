# Running the Generator
For rapid model testing and iterations, it is sometimes useful to to run the generator locally. This how-to guide shows how to do this on your machine.

The arguments definitions can be seen here:[Pixels Data Generator](../generator.md)

## Prediction mode
When running the generator locally multiple times, it can make sense to download the data so that subsequent runs are faster. To do so, use the following additional parameters: ```download_data``` and ```download_dir```.

```python
from pixels.stac_generator.generator import Generator

# Path to Collection dictionary.
# It can be on s3 or locally, it has to be a catalogs_dict.json representing the collection.
path_collection_catalog = 's3://bucket-key/pixelsdata/collection_id_key/data/catalogs_dict.json'

data_training_generator = Generator(
    path_collection_catalog=path_collection_catalog,
    random_seed = 23,
    split=0.8,
    usage_type="training",
    download_data=True,
    download_dir="/home/user/Desktop/local_generator_data",
    ...
)
```
The first time you instantiate the generator it will download the data to the download_dir and build a new catalogs_dict.json with the local paths.

Every other instantiation with the same paths after will just run a file check and use the already downloaded data.

## Evaluation mode
To run an evaluation using the remaining data from the same dataset a new generator must be instanciated. The ```usage_type``` must be changed to ```evaluation```,
training percentage must be the same as the split in the training generator, it is also important that the random_seed is the same as the training generator.
```split``` can be used here independently, one can have have a split lesser than the remaining dataset. Be aware that split is allways referent to the full dataset size.

In evalutation is also important the split not to be bigger than 1 - training_percentage.

Considering a dataset with 1000 samples.

```python
# This creates a generator with the remaining 20% that were not used in the training.
>>> data_evaluation_generator = Generator(
        ... # Same as in training
        split=0.2,
        usage_type="evaluation",
        training_percentage=0.8
        ...
    )
>>> len(data_evaluation_generator)
200
```

```python
# This creates a generator with the 10% of the full dataset, only fetching samples not used in the training.

>>> data_evaluation_generator = Generator(
        ... # Same as in training
        split=0.1,
        usage_type="evaluation",
        training_percentage=0.8
        ...
    )
>>> len(data_evaluation_generator)
100
```
