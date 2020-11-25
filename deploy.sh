# /bin/bash

# Workon pixels-deploy
source ~/.virtualenvs/pixels-deploy-$1/bin/activate

# Go to repo.
cd /home/tam/Documents/repos/pixels

# Reset build dir.
rm -r build
mkdir build

# Copy pixels app.
cp -r pixels build
cp -r app build

# Copy zappa settings.
cp zappa_settings.json build

# Remove pyc files.
find ~/.virtualenvs/pixels-deploy-$1/ -name "*.pyc" -exec rm -f {} \;
find build -name "*.pyc" -exec rm -f {} \;

# Create docs template.
pandoc docs/index.md --output=build/app/templates/docs.html --to=html5 --css=docs/github.css --self-contained

# Update dev environment.
cd build
zappa update $1
