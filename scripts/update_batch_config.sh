project=replant
src=/home/tam/Documents/work/tesselo/projects/replant/pixels
# /home/tam/Documents/work/tesselo/projects/replant/pixels/replant_samples_V0.gpkg
aws s3 sync $src s3://tesselo-pixels-results/$project
