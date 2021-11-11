# Running the Generator
For rapid model testing and iterations, it is sometimes useful to to run the generator locally. This how-to guide shows how to do this on your machine.

The arguments definitions can be seen here:[Pixels Data Generator](../generator.md)

```python
from pixels.stac_generator.generator import DataGenerator


# Path to Collection dictionary.
# It can be on s3 or locally, it has to be a catalogs_dict.json representing the collection.
path_collection_catalog = 's3://pxapi-media-dev/pixelsdata/5444055e-89d0-4fe8-a0b4-3abb1f0a6c5e/data/catalogs_dict.json'

gen_args = {
    'path_collection_catalog':path_collection_catalog,
    'random_seed' : 23,
    'split':0.8,
    'width':100,
    'height':100,
    'timesteps':12,
    'num_bands':10,
    'batch_number':1,
    'num_classes':1,
    'augmentation':0,
    'padding':2,
    'usage_type':"training",
    'mode':'3D_Model'
}


data_generator = DataGenerator(**gen_args)
```

To run locally how can set:

```python
'download_data':True,
'temp_dir':"/home/user/Desktop/local_generator_data",
```

The first time you instantiate the generator it will download the data to the temp_dir and build a new catalogs_dict.json with the local paths.

Every other instantiation with the same paths after will just run a file check and use the already downloaded data.
