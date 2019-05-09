# /bin/bash

# Workon pixels-deploy
source ~/.virtualenvs/pixels-deploy/bin/activate

# Go to repo.
cd ~/Documents/repos/pixels

# Reset build dir.
rm -r build
mkdir build

# Copy pixels app.
cp -r pixels build

# Copy zappa settings.
cp zappa_settings.json build

# Remove pyc files.
find ~/.virtualenvs/pixels-deploy/ -name "*.pyc" -exec rm -f {} \;
find build -name "*.pyc" -exec rm -f {} \;

# Create docs template.
pandoc docs/index.md --output=build/pixels/templates/docs.html --to=html5 --css=docs/github.css --self-contained

# Update dev environment.
cd build
zappa update $1
