#!/bin/sh

TAG=${1:- "latest"}

./build_ecs_image.sh "$TAG"

echo "Pushing the image to our ECS repository"
docker push "595064993071.dkr.ecr.eu-central-1.amazonaws.com/tesselo-pixels:$TAG"

echo "Done! :yay:"
echo ""
echo "Make sure that pxapi is pointing to the same version you just built"

