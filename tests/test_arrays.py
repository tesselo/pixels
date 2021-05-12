import numpy as np

# Simple3DCase
X_Simple3DCase = np.array(
    [
        [
            [
                [
                    [1063.0, 903.0, 740.0, 982.0],
                    [1053.0, 891.0, 715.0, 1001.0],
                    [1012.0, 852.0, 678.0, 1034.0],
                ],
                [
                    [1073.0, 894.0, 744.0, 979.0],
                    [1053.0, 862.0, 711.0, 997.0],
                    [1016.0, 836.0, 661.0, 995.0],
                ],
                [
                    [1069.0, 886.0, 740.0, 956.0],
                    [1047.0, 853.0, 710.0, 954.0],
                    [1064.0, 884.0, 734.0, 946.0],
                ],
            ],
            [
                [
                    [331.0, 539.0, 519.0, 916.0],
                    [308.0, 526.0, 524.0, 952.0],
                    [266.0, 561.0, 488.0, 1055.0],
                ],
                [
                    [342.0, 533.0, 541.0, 922.0],
                    [306.0, 492.0, 467.0, 944.0],
                    [220.0, 445.0, 396.0, 973.0],
                ],
                [
                    [315.0, 506.0, 513.0, 890.0],
                    [323.0, 503.0, 488.0, 887.0],
                    [305.0, 479.0, 469.0, 894.0],
                ],
            ],
            [
                [
                    [1173.0, 1011.0, 856.0, 1086.0],
                    [1130.0, 985.0, 801.0, 1106.0],
                    [1122.0, 948.0, 766.0, 1143.0],
                ],
                [
                    [1165.0, 980.0, 841.0, 1078.0],
                    [1140.0, 953.0, 793.0, 1086.0],
                    [1114.0, 925.0, 730.0, 1081.0],
                ],
                [
                    [1154.0, 955.0, 819.0, 1058.0],
                    [1154.0, 933.0, 814.0, 1055.0],
                    [1133.0, 961.0, 821.0, 1052.0],
                ],
            ],
        ]
    ]
)

Y_Simple3DCase = np.array(
    [[[[1.0], [1.0], [1.0]], [[0.0], [1.0], [1.0]], [[0.0], [0.0], [1.0]]]]
)

X_SimplePixelCase = np.array(
    [
        [
            [
                [1063.0, 903.0, 740.0, 982.0],
                [331.0, 539.0, 519.0, 916.0],
                [1173.0, 1011.0, 856.0, 1086.0],
            ],
            [
                [1053.0, 891.0, 715.0, 1001.0],
                [308.0, 526.0, 524.0, 952.0],
                [1130.0, 985.0, 801.0, 1106.0],
            ],
            [
                [1012.0, 852.0, 678.0, 1034.0],
                [266.0, 561.0, 488.0, 1055.0],
                [1122.0, 948.0, 766.0, 1143.0],
            ],
            [
                [1073.0, 894.0, 744.0, 979.0],
                [342.0, 533.0, 541.0, 922.0],
                [1165.0, 980.0, 841.0, 1078.0],
            ],
            [
                [1053.0, 862.0, 711.0, 997.0],
                [306.0, 492.0, 467.0, 944.0],
                [1140.0, 953.0, 793.0, 1086.0],
            ],
            [
                [1016.0, 836.0, 661.0, 995.0],
                [220.0, 445.0, 396.0, 973.0],
                [1114.0, 925.0, 730.0, 1081.0],
            ],
            [
                [1069.0, 886.0, 740.0, 956.0],
                [315.0, 506.0, 513.0, 890.0],
                [1154.0, 955.0, 819.0, 1058.0],
            ],
            [
                [1047.0, 853.0, 710.0, 954.0],
                [323.0, 503.0, 488.0, 887.0],
                [1154.0, 933.0, 814.0, 1055.0],
            ],
            [
                [1064.0, 884.0, 734.0, 946.0],
                [305.0, 479.0, 469.0, 894.0],
                [1133.0, 961.0, 821.0, 1052.0],
            ],
        ]
    ]
)

Y_SimplePixelCase = np.array([Y_Simple3DCase.ravel()])
