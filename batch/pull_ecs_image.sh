#!/bin/sh

echo "Logging in our private docker repository in AWS"
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 595064993071.dkr.ecr.eu-central-1.amazonaws.com

echo "Pulling the image to our ECS repository"
docker pull 595064993071.dkr.ecr.eu-central-1.amazonaws.com/tesselo-pixels:latest

echo "Done! :yay: you now have a copy of the latest image"
