#!/usr/bin/env python3
"""
@project: object_detection
@file: train
@time: 2021/3/4
 
@function:
"""
import keras.backend as K
from models.SSD7 import SSD7
from keras.optimizers import Adam
from loss.loss import SSDLoss
from generator.data_generator import DataGenerator
from generator.data_augmentation_chain_constant_input_size import DataAugmentationConstantInputSize

# 1) Set the configs
img_height = 300
img_width = 480
img_channels = 3
# Set this to your preference (maybe `None`).
# The current settings transform the input pixel values to the interval `[-1,1]`.
intensity_mean = 127.5
intensity_range = 127.5
n_classes = 5  # Number of positive classes
# An explicit list of anchor box scaling factors.
# If this is passed, it will override `min_scale` and `max_scale`.
scales = [0.08, 0.16, 0.32, 0.64, 0.96]
aspect_ratios = [0.5, 1.0, 2.0]  # The list of aspect ratios for the anchor boxes
two_boxes_for_ar1 = True  # Whether or not you want to generate two anchor boxes for aspect ratio 1
steps = None  # In case you'd like to set the step sizes for the anchor box grids manually; not recommended
offsets = None  # In case you'd like to set the offsets for the anchor box grids manually; not recommended
clip_boxes = False  # Whether or not to clip the anchor boxes to lie entirely within the image boundaries
variances = [1.0, 1.0, 1.0, 1.0]  # The list of variances by which the encoded target coordinates are scaled
normalize_coords = True  # Whether or not the model is supposed to use coordinates relative to the image size
batch_size = 16

# 2) Create the model
K.clear_session()  # Clear previous models from memory.
model = SSD7(image_size=(img_height, img_width, img_channels),
             n_classes=n_classes,
             mode='training',
             l2_reg=0.0005,
             scales=scales,
             aspect_ratios_global=aspect_ratios,
             aspect_ratios_per_layer=None,
             two_boxes_for_ar1=two_boxes_for_ar1,
             steps=steps,
             offsets=offsets,
             clip_boxes=clip_boxes,
             variances=variances,
             normalize_coords=normalize_coords,
             subtract_mean=intensity_mean,
             divide_by_stddev=intensity_range)
print(model.summary())

# 3) Compile the model
adam = Adam(lr=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0)
ssd_loss = SSDLoss(neg_pos_ratio=3, alpha=1.0)
model.compile(optimizer=adam, loss=ssd_loss.compute_loss)

# 4) Set up the data generators for the training
train_dataset = DataGenerator(load_images_into_memory=False, hdf5_dataset_path=None)
val_dataset = DataGenerator(load_images_into_memory=False, hdf5_dataset_path=None)

# Parse the image and label lists for the training and validation datasets.
# Images
images_dir = ''
# Ground Truth
train_labels_filename = ''
val_labels_filename = ''

train_dataset.parse_csv(images_dir=images_dir,
                        labels_filename=train_labels_filename,
                        input_format=['image_name', 'xmin', 'xmax', 'ymin', 'ymax', 'class_id'],
                        include_classes='all')
val_dataset.parse_csv(images_dir=images_dir,
                      labels_filename=val_labels_filename,
                      input_format=['image_name', 'xmin', 'xmax', 'ymin', 'ymax', 'class_id'],
                      include_classes='all')

train_dataset.create_hdf5_dataset()
val_dataset.create_hdf5_dataset()

# Get the number of samples in the training and validation datasets.
trail_dataset_size = train_dataset.get_dataset_size()
val_dataset_size = val_dataset.get_dataset_size()
print(f'Number of images in the training dataset: \t{trail_dataset_size:>6}')
print(f'Number of images in the validation dataset: \t{val_dataset_size:>6}')

# 5) Define the image processing chain.
data_augmentation_chain = DataAugmentationConstantInputSize()  # todo
