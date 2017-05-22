""" This module should be used for functions that null out values in an array
    based on a condition. Primarily used for masking.
"""

import numpy as np

from ..qtim_utilities.format_util import convert_input_2_numpy

def crop_with_mask(input_data, label_data, mask_value=0, replacement_value=0):

    """ Crops and image with a predefined mask image. Values equal to mask value
        are replaced with replacement_value.

        TODO: Add support for not-equal-to masking.
        TODO: Add support for other replacement_values, a-la scikit-learn.

        Parameters
        ----------

        input_data: N-dimensional array or str
            The volume to be cropped. Can be filename or numpy array.
        label_data: N-dimensional array or str
            A label mask. Must be the same size as input_data
        mask_value: int or float
            Values equal to mask_value will be replaced with replacement_value.
        replacement_value: int or float
            Values equal to mask_value will be replaced with replacement_value.
    """

    input_numpy, label_numpy = convert_input_2_numpy(input_data), convert_input_2_numpy(label_data)

    input_numpy[label_numpy == mask_value] = replacement_value

    return input_numpy

def run_test():
    return

if __name__ == '__main__':
    run_test()