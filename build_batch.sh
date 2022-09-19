#!/bin/bash

STAGE=${1:- "dev"}

echo "$STAGE"

exit

# Reset build dir.
rm -rf build
mkdir build

# Copy pixels app.
cp -r pixels build

# Copy batch scripts.
cp batch/runpixels.py build

# Remove pyc files.
find build -name "*.pyc" -exec rm -f {} \;

cd build/ && zip -r "batch-$STAGE.zip" ./*

# Update script online.
aws s3api put-object --bucket tesselo-pixels-scripts --key "batch-$STAGE.zip" --body "batch-$STAGE.zip"
