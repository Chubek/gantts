# coding: utf-8
import sys
import numpy as np
from torch.autograd import Variable
import torch
from torch import nn
from torch import optim
from nnmnkwii.paramgen import unit_variance_mlpg_matrix

from gantts.models import In2OutHighwayNet, MLP
from gantts.seqloss import MaskedMSELoss, sequence_mask
from gantts.multistream import multi_stream_mlpg, get_static_features


def test_model():
    windows = [
        (0, 0, np.array([1.0])),
        (1, 1, np.array([-0.5, 0.0, 0.5])),
    ]

    model = In2OutHighwayNet()
    print(model)

    in_dim = 118
    static_dim = in_dim // 2
    T = 100
    x = Variable(torch.rand(1, T, in_dim))
    R = unit_variance_mlpg_matrix(windows, T)
    R = torch.from_numpy(R)
    _, y = model(x, R)

    print(y.size())
    assert y.size(-1) == static_dim

    # Mini batch
    batch_size = 32
    x = Variable(torch.rand(batch_size, T, in_dim))
    _, y_hat = model(x, R)
    y = Variable(torch.rand(batch_size, T, static_dim), requires_grad=False)

    lengths = [np.random.randint(50, T - 1) for _ in range(batch_size - 1)] + [T]
    lengths = Variable(torch.LongTensor(lengths), requires_grad=False)
    print(x.size(), y.size(), lengths.size())
    MaskedMSELoss()(y_hat, y, lengths).backward()
    print(y.size())
    assert y.size(-1) == static_dim
    assert y.size(0) == batch_size

    # cuda
    model = model.cuda()
    x = x.cuda()
    R = R.cuda()
    _, y_hat = model(x, R)


def test_multi_stream_mlpg():
    windows = [
        (0, 0, np.array([1.0])),
        (1, 1, np.array([-0.5, 0.0, 0.5])),
        (1, 1, np.array([1.0, -2.0, 1.0])),
    ]
    in_dim = 187
    T = 100
    R = unit_variance_mlpg_matrix(windows, T)
    R = torch.from_numpy(R)

    batch_size = 32
    x = Variable(torch.rand(batch_size, T, in_dim))

    stream_sizes = [180, 3, 1, 3]
    has_dynamic_features = [True, True, False, True]
    y = multi_stream_mlpg(x, R, stream_sizes, has_dynamic_features)
    assert y.size() == (batch_size, T, 60 + 1 + 1 + 1)

    static_features = get_static_features(
        x, len(windows), stream_sizes, has_dynamic_features)
    assert static_features.size() == y.size()
