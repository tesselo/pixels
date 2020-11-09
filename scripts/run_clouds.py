import numpy
from PIL import Image

from pixels.clouds import composite_index

data = numpy.load('/home/tam/Desktop/esb/combined_data/pixels_9.npz', allow_pickle=True)

X = data['data']
X = X[20:30]
print(X.shape)

# "bands": ["B11", "B8A", "B08", "B07", "B06", "B05", "B04", "B03", "B02", "B12"],

dat = composite_index(X[:, 8], X[:, 7], X[:, 6], X[:, 2], X[:, 1], X[:, 0], X[:, 9], composite=True)

print(dat)
result = []
idx1, idx2 = numpy.indices(dat.shape)
for i in range(X.shape[1]):
    # result.append(X[:, i, :, :][dat, idx1, idx2])
    result.append(X[dat, i, idx1, idx2])

result = numpy.array(result)
scale = 1000
rgb = numpy.dstack([
    255 * (numpy.clip(result[8], 0, scale) / scale),
    255 * (numpy.clip(result[7], 0, scale) / scale),
    255 * (numpy.clip(result[6], 0, scale) / scale),
]).astype('uint8')
img = Image.fromarray(rgb)
img.save('/home/tam/Desktop/bla.jpg')
