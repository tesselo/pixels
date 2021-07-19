#!/bin/sh

cd docker

echo "Logging in external ECS where our base image is"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 763104351884.dkr.ecr.us-east-1.amazonaws.com

echo "Building the image"
docker build -t tesselo-pixels .

echo "Logging in our private docker repository in AWS"
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 595064993071.dkr.ecr.eu-central-1.amazonaws.com

echo "Tagging the newly built image"
docker tag tesselo-pixels:latest 595064993071.dkr.ecr.eu-central-1.amazonaws.com/tesselo-pixels:latest

echo "Pushing the image to our ECS repository"
docker push 595064993071.dkr.ecr.eu-central-1.amazonaws.com/tesselo-pixels:latest

echo "Done! :yay:"
echo ""
echo "Make sure that pxapi is pointing to the same version you just built"

