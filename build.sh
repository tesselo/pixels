# /bin/bash

target=/home/tam/Documents/repos/pixels/build
sen2cor=/home/tam/Documents/repos/sen2cor
pixels=/home/tam/Documents/repos/pixels

cd

rm -rf $target
mkdir $target
touch $target/__init__.py

mkdir $target/pixels
cp $pixels/pixels $target/pixels

mkdir $target/sen2cor
cp $sen2cor/*.py $target/sen2cor

pip install -r $pixels/requirements.txt --target $target
pip install -r $sen2cor/requirements.txt --target $target

# To save space, remove scipy libs and link to numpy libs instead.
rm $target/scipy/.libs/libgfortran-ed201abd.so.3.0.0
rm $target/scipy/.libs/libopenblasp-r0-382c8f3a.3.5.dev.so

ln -s $target/numpy/.libs/libgfortran-ed201abd.so.3.0.0 $target/scipy/.libs/libgfortran-ed201abd.so.3.0.0
ln -s $target/numpy/.libs/libopenblasp-r0-382c8f3a.3.5.dev.so $target/scipy/.libs/libopenblasp-r0-382c8f3a.3.5.dev.so

# Strip unnecessary scipy modules (scipy is there only for sen2cor).
rm -r $target/scipy/cluster
rm -r $target/scipy/fftpack
rm -r $target/scipy/io
rm -r $target/scipy/stats
rm -r $target/scipy/optimize
rm -r $target/scipy/integrate
rm -r $target/scipy/signal

find $target -name "*.pyc" -exec rm -f {} \;
find $target -name "*.txt" -exec rm -f {} \;
find $target -name tests -exec rm -rf {} \;

cp $pixels/zappa_settings.json $target

rm $target.zip

cd $target
zappa package dev

# Reduce size of zip file.
ZAPPA_PACKAGE=`find . -iname "pixels-dev-*.zip"`
zip -d $ZAPPA_PACKAGE \*.pyc
zip -d $ZAPPA_PACKAGE scipy/.libs/libgfortran-ed201abd.so.3.0.0
zip -d $ZAPPA_PACKAGE scipy/.libs/libopenblasp-r0-382c8f3a.3.5.dev.so
zip -u --symlinks $ZAPPA_PACKAGE scipy/.libs/libgfortran-ed201abd.so.3.0.0
zip -u --symlinks $ZAPPA_PACKAGE scipy/.libs/libopenblasp-r0-382c8f3a.3.5.dev.so

unzip -l $ZAPPA_PACKAGE

zappa deploy dev -z

#python -m compileall .

cd $target
zip --symlinks -r9 $target.zip ./*

unzip -l $target.zip
