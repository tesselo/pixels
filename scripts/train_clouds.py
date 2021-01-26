import pickle

import h5py
import numpy
from sklearn.metrics import cohen_kappa_score, confusion_matrix
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

data = numpy.load(
    open(
        "/media/tam/rhino/work/projects/tesselo/data/cloud_training_data/classifier-collected-pixels-694.npz",
        "rb",
    )
)

X = data["X"]
Y = data["Y"]

clf = make_pipeline(RobustScaler(), MLPClassifier())
clf = clf.fit(X, Y)

with open(
    "/home/tam/Documents/repos/pixels/train/clouds_mlpclassifier_v2.pickle", "wb"
) as fl:
    pickle.dump(clf, fl)


clf_re = pickle.load(
    open("/home/tam/Documents/repos/pixels/train/clouds_mlpclassifier_v2.pickle", "rb")
)
res = []
for i in range(23):
    st = int(i * 1e6)
    en = int((i + 1) * 1e6)
    print(st)
    res.append(
        clf_re.predict(
            X[
                st:en,
            ]
        )
    )

Yh = numpy.hstack(res)

print(cohen_kappa_score(Y, Yh))
print(confusion_matrix(Y, Yh))

##############################
filename = "/media/tam/rhino/work/projects/tesselo/data/cloud_training_data/points/20170710_s2_manual_classification_data.h5"

fl = h5py.File(filename, "r")

print("Keys: %s" % list(fl.keys()))

class_lookup = dict(zip(fl["class_ids"], fl["class_names"]))
print("Class lookup", class_lookup)

Y = numpy.array(fl["classes"]).astype("int")
X = numpy.array(numpy.array(fl["spectra"]))

# Convert Y into normal array.
Y[Y == 10] = 1
Y[Y == 20] = 2
Y[Y == 30] = 3
Y[Y == 40] = 4
Y[Y == 50] = 5
Y[Y == 60] = 6

# mask = Xo[:, 3] != 0
# Y = Yo[mask]
# X = Xo[mask]
# X = numpy.delete(X, 10, 1) * 10000

clf = make_pipeline(RobustScaler(), MLPClassifier())
clf = clf.fit(X, Y)

with open(
    "/home/tam/Documents/repos/pixels/pixels/clf/classifier-l1c.pickle", "wb"
) as fl:
    pickle.dump(clf, fl)
