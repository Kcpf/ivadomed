import numpy as np
import time
import sys
import matplotlib.pyplot as plt

import torch.backends.cudnn as cudnn
from torch.utils.data import DataLoader
from torchvision import transforms

from medicaltorch.filters import SliceFilter
from medicaltorch import datasets as mt_datasets
from medicaltorch import transforms as mt_transforms
from torch import optim

from tqdm import tqdm

from ivadomed import loader as loader
from ivadomed import models
from ivadomed import losses
from ivadomed.utils import *
import ivadomed.transforms as ivadomed_transforms

cudnn.benchmark = True

GPU_NUMBER = 5
BATCH_SIZE = 8
DROPOUT = 0.4
BN = 0.1
N_EPOCHS = 10
INIT_LR = 0.01
PATH_BIDS = 'testing_data/'
PATH_TMP = 'tmp_test_dilateGT/'


def save_im_gt(im, gt, fname_out):
    plt.figure()
    plt.subplot(1, 2, 1)
    plt.axis("off")

    i_zero, i_nonzero = np.where(gt==0.0), np.nonzero(gt)
    img_jet = plt.cm.jet(plt.Normalize(vmin=0, vmax=1)(gt))
    img_jet[i_zero] = 0.0
    bkg_grey = plt.cm.binary_r(plt.Normalize(vmin=np.amin(im), vmax=np.amax(im))(im))
    img_out = np.copy(bkg_grey)
    img_out[i_nonzero] = img_jet[i_nonzero]

    plt.subplot(1, 2, 1)
    plt.axis("off")
    plt.imshow(bkg_grey, interpolation='nearest', aspect='auto')

    plt.subplot(1, 2, 2)
    plt.axis("off")
    plt.imshow(img_out, interpolation='nearest', aspect='auto')

    plt.savefig(fname_out, bbox_inches='tight', pad_inches=0)
    plt.close()


def test_dilateGT():
    training_transform_list = [
        ivadomed_transforms.Resample(wspace=0.75, hspace=0.75),
        ivadomed_transforms.DilateGT(dilation_factor=2),
        ivadomed_transforms.ROICrop2D(size=[48, 48]),
        ivadomed_transforms.ToTensor()
    ]
    train_transform = transforms.Compose(training_transform_list)

    train_lst = ['sub-test001']

    ds_train = loader.BidsDataset(PATH_BIDS,
                                  subject_lst=train_lst,
                                  target_suffix="_lesion-manual",
                                  roi_suffix="_seg-manual",
                                  contrast_lst=['T2w'],
                                  metadata_choice="without",
                                  contrast_balance={},
                                  slice_axis=2,
                                  transform=train_transform,
                                  multichannel=False,
                                  slice_filter_fn=SliceFilter(filter_empty_input=True, filter_empty_mask=True))

    ds_train.filter_roi(nb_nonzero_thr=10)

    train_loader = DataLoader(ds_train, batch_size=BATCH_SIZE,
                              shuffle=True, pin_memory=True,
                              collate_fn=mt_datasets.mt_collate,
                              num_workers=1)

    if not os.path.isdir(PATH_OUT):
        os.makedirs(PATH_OUT)

    for i, batch in enumerate(train_loader):
        input_samples, gt_samples = batch["input"], batch["gt"]
        for b_idx in range(len(batch['input'])):
            fname_out = os.path.join(PATH_OUT, 'im_'+str(i).zfill(2)+'_'+str(b_idx).zfill(2)+'.png')
            save_im_gt(input_samples[b_idx], gt_samples[b_idx], fname_out)
