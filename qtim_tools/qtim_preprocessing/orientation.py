""" This module should be used for functions that null out values in an array
    based on a condition. Primarily used for masking.
"""

import subprocess
import os
import numpy as np

from ..qtim_utilities.format_util import convert_input_2_numpy
from ..qtim_utilities.nifti_util import save_numpy_2_nifti

def orient(input_data, output_filename='', method="slicer", command="Slicer", temp_dir='./', orientation='RAI'):

    """ A catch-all function for resampling. Will resample a 3D volume to given dimensions according
        to the method provided.

        TODO: Add resampling for 4D volumes.
        TODO: Add dimension, interpolation, reference parameter. Currently set to linear/isotropic.

        Parameters
        ----------
        input_data: str or array
            Can be a 3D volume or a filename.
        output_filename: str
            Location to save output data to. If left as '', will return numpy array.
        input_transform: str
            detatails TBD, unimplemented
        method: str
            Will perform motion correction according to the provided method.
            Currently available: ['fsl']
        command: str
            The literal command-line string to be inputted via Python's subprocess module.
        temp_dir: str
            If temporary files are created, they will be saved here.

        Returns
        -------
        output: array
            Output data, only if output_filename is left as ''.
    """

    orientation_methods = ['slicer']
    if method not in orientation_methods:
        print(('Input \"method\" parameter is not available. Available methods: ', orientation_methods))
        return

    if method == 'slicer':

        # A good reason to have a Class for qtim methods is to cut through all of this extra code.

        temp_input, temp_output = False, False

        if not isinstance(input_data, str):
            input_filename = os.path.join(temp_dir, 'temp.nii.gz')
            save_numpy_2_nifti(input_data, input_filename)
            temp_input = True
        else:
            input_filename = input_data

        if output_filename == '':
            temp_output = True
            output_filename = os.path.join(temp_dir, 'temp_out.nii.gz')

        orientation_command = [command, '--launch', 'OrientScalarVolume', '-o', orientation, input_filename, output_filename]
        print((' '.join(orientation_command)))
        subprocess.call(orientation_command)
        
        if temp_input:
            os.remove(input_filename)
            pass

        if temp_output:
            output = convert_input_2_numpy(output_filename)
            os.remove(output_filename)
            return output

def run_test():
    return

if __name__ == '__main__':
    run_test()