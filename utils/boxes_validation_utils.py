#!/usr/bin/env python3
"""
@project: object_detection
@file: boxes_validation_utils
@author: mike
@time: 2021/3/10
 
@function:
"""
import numpy as np
from utils.bounding_box import iou


class BoundGenerator:
    pass


class BoxFilter:
    """
    Returns all bounding boxes that are valid with respect to the defined criteria.
    """

    def __init__(self,
                 check_overlap=True,
                 check_min_area=True,
                 check_degenerate=True,
                 overlap_criterion='center_point',
                 overlap_bounds=(0.3, 1.0),
                 min_area=16,
                 labels_format={'class_id': 0, 'xmin': 1, 'ymin': 2, 'xmax': 3, 'ymax': 4},
                 border_pixels='half'):
        """
        Arguments:
            check_overlap (bool): Whether or not to enforce the overlap requirements defined by `overlap_criterion`
                 and `overlap_bounds`. Sometimes you might want to use the box filter only to enforce a certain
                 minimum area for all boxes, in such cases you can turn the overlap requirements off.
            check_min_area (bool): Whether or not to enforce the minimum area requirement defined by `min_area`.
                If `True`, any boxes that have an area (in pixels) that is smaller than `min_area` will be removed
                from the labels of an image. Bounding boxes below a certain area aren't useful training examples.
                An object that takes up only, say, 5 pixels in an image is probably not recognizable anymore,
                neither for a human, nor for an object detection model. It makes sense to remove such boxes.
            check_degenerate (bool): Whether or not to check for and remove degenerate bounding boxes. Degenerate
                bounding boxes are boxes that have `xmax <= xmin` and/or `ymax <= ymin`. It is obviously important
                to filter out such boxes, so you should only set this option to `False` if you are certain that
                degenerate boxes are not possible in your data and processing chain.
            overlap_criterion: Can be either of 'center_point', 'iou', or 'area'. Determines which boxes are
                considered valid with respect to a given image. If set to 'center_point', a given bounding box is
                considered valid if its center point lies within the image. If set to `area`, a given bounding box
                is considered valid if the quotient of its intersection area with the image and its own area is
                within the given `overlap_bounds`. If set to `iou`, a given bounding box is considered valid if its
                IoU with the image is within the given `overlap_bounds`.
            overlap_bounds: Only relevant if `overlap_criterion` is `area` or `iou`. Determines the lower and upper
                bounds for `overlap_criterion`. Can either be a 2-tuple of scalars representing a lower bound and
                an upper bound, or a `BoundGenerator` object, which provides the possibility to generate bounds
                randomly.
            min_area: Only relevant if `check_min_area` is `True`. Defines the minimum area in pixels that a
                bounding box must have in order to be valid. Boxes with an area smaller than this will be removed.
            labels_format: A dictionary that defines which index in the last axis of the labels contains which
                bounding box coordinate. The dictionary maps at least the keywords 'xmin', 'ymin', 'xmin', and
                'ymax' to their respective indices within last axis of the labels array.
            border_pixels: How to treat the border pixels of the bounding boxes. Can be 'include', 'exclude', or
                'half'. If 'include', the border pixels belong to the boxes. If 'exclude', the border pixels do
                not belong to the boxes. If 'half', then one of each of the two horizontal and vertical borders
                belong to the boxes, but not the other.
        """
        # Value check.
        if not isinstance(overlap_bounds, (list, tuple, BoundGenerator)):
            raise ValueError("`overlap_bounds` must be either a 2-tuple of scales or a `BoundGenerator` object.")
        if isinstance(overlap_bounds, (list, tuple)) and overlap_bounds[0] > overlap_bounds[1]:
            raise ValueError("The lower bound must not be greater than the upper bound.")
        if overlap_criterion not in {'iou', 'area', 'center_point'}:
            raise ValueError("`overlap_criterion` must be one of 'iou', 'area', or 'center_point'.")
        self.overlap_criterion = overlap_criterion
        self.overlap_bounds = overlap_bounds
        self.min_area = min_area
        self.check_overlap = check_overlap
        self.check_min_area = check_min_area
        self.check_degenerate = check_degenerate
        self.labels_format = labels_format
        self.border_pixels = border_pixels

    def __call__(self,
                 labels,
                 image_height=None,
                 image_width=None):
        """
        Arguments:
            labels (array): The labels to be filtered. This is an array with shape `(m,n)`, where
                `m` is the number of bounding boxes and `n` is the number of element that defines
                each bounding box (box coordinates, class ID, etc.). The box coordinates are expected
                to be in the image's coordinate system.
            image_height: Only relevant if `check_overlap == True`. The height of the image (in pixels)
                to compare the box coordinates to.
            image_width: Only relevant if `check_overlap == True`. The width of the image (in pixels)
                to compare the box coordinates to.
        Returns:
            An array containing the labels of all boxes that are valid.
        """
        labels = np.copy(labels)
        xmin = self.labels_format['xmin']
        ymin = self.labels_format['ymin']
        xmax = self.labels_format['xmax']
        ymax = self.labels_format['ymax']

        # Record the boxes that pass all checks here.
        requirements_met = np.ones(shape=labels.shape[0], dtype=np.bool)

        if self.check_degenerate:
            non_degenerate = (labels[:, xmax] > labels[:, xmin]) * (labels[:, ymax] > labels[:, ymin])
            requirements_met *= non_degenerate

        if self.check_min_area:
            min_area_met = (labels[:, xmax] - labels[:, xmin]) * (labels[:, ymax] - labels[:, ymin]) >= self.min_area
            requirements_met *= min_area_met

        if self.check_overlap:
            # Get the lower and upper bounds.
            if isinstance(self.overlap_bounds, BoundGenerator):
                lower, upper = self.overlap_bounds()  # todo implementation
            else:
                lower, upper = self.overlap_bounds

            # Compute which boxes are valid.
            if self.overlap_criterion == 'iou':
                # Compute the patch coordinates.
                image_coords = np.array([0, 0, image_width, image_height])
                # Compute the IoU between the patch and all of the ground truth boxes.
                image_boxes_iou = iou(image_coords, labels[:, [xmin, ymin, xmax, ymax]],
                                      coords='corners',
                                      mode='element-wise',
                                      border_pixels=self.border_pixels)  # todo implementation
                requirements_met *= (image_boxes_iou > lower) * (image_boxes_iou <= upper)
            elif self.overlap_criterion == 'area':
                if self.border_pixels == 'half':
                    d = 0
                elif self.border_pixels == 'include':
                    # If border pixels are supposed to belong to the bounding boxes,
                    # we have to add one pixel to any difference `xmax - xmin` or `ymax - ymin`.
                    d = 1
                elif self.border_pixels == 'exclude':
                    # If border pixels are not supposed to belong to the bounding boxes,
                    # we have to subtract one pixel from any difference `xmax - xmin` or `ymax - ymin`.
                    d = -1
                # Compute the area of the boxes.
                box_areas = (labels[:, xmax] - labels[:, xmin] + d) * (labels[:, ymax] - labels[:, ymin] + d)
                # Compute the intersection area between the patch and all of the ground truth boxes.
                clipped_boxes = np.copy(labels)
                clipped_boxes[:, [ymin, ymax]] = np.clip(labels[:, [ymin, ymax]], a_min=0, a_max=image_height - 1)
                clipped_boxes[:, [xmin, xmax]] = np.clip(labels[:, [xmin, xmax]], a_min=0, a_max=image_width - 1)
                intersection_areas = (clipped_boxes[:, xmax] - clipped_boxes[:, xmin] + d) * \
                                     (clipped_boxes[:, ymax] - clipped_boxes[:, ymin] + d)
                # Check which boxes meet the overlap requirements.
                if lower == 0.0:
                    # If `lower == 0`, we want to make sure that boxes with area 0 don't count,
                    # hence the ">" sign instead of the ">=" sign.
                    mask_lower = intersection_areas > 0.0
                else:
                    mask_lower = intersection_areas >= lower * box_areas
                mask_upper = intersection_areas <= upper * box_areas
                requirements_met *= mask_lower * mask_upper
            elif self.overlap_criterion == 'center_point':
                # Compute the center points of the boxes.
                cy = (labels[:, ymin] + labels[:, ymax]) / 2
                cx = (labels[:, xmin] + labels[:, xmax]) / 2
                image_box_center = (cy >= 0.0) * (cy <= image_height - 1) * (cx >= 0.0) * (cx <= image_width - 1)
                requirements_met *= image_box_center
        return labels[requirements_met]