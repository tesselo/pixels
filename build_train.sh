# /bin/bash

# Reset build dir.
rm -r build
mkdir build

# Copy pixels app.
cp -r pixels build

# Copy batch scripts.
cp train/collect.py build
cp train/pack.py build
cp train/train.py build
cp train/pyramid.py build

# Remove pyc files.
find build -name "*.pyc" -exec rm -f {} \;

cd build/ && zip -r batch.zip ./*

# Update script online.
aws s3api put-object --bucket tesselo-pixels-scripts --key batch.zip --body batch.zip
