#!/bin/sh

./build_ecs_image.sh

echo "Pushing the image to our ECS repository"
docker push 595064993071.dkr.ecr.eu-central-1.amazonaws.com/tesselo-pixels:latest

echo "Done! :yay:"
echo ""
echo "Make sure that pxapi is pointing to the same version you just built"

