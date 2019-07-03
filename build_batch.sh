# /bin/bash

# Reset build dir.
rm -r build
mkdir build

# Copy pixels app.
cp -r pixels build

# Copy batch scripts.
cp batch/collect.py build
cp batch/pack.py build
cp batch/train.py build
cp batch/pyramid/pyramid.py build
cp batch/pyramid/pyramid_up.py build
cp batch/pyramid/tile_range.py build

# Remove pyc files.
find build -name "*.pyc" -exec rm -f {} \;

cd build/ && zip -r batch.zip ./*

# Update script online.
aws s3api put-object --bucket tesselo-pixels-scripts --key batch.zip --body batch.zip
