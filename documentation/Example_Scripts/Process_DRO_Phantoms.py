import os
from qtim_tools.qtim_dce.tofts_parameter_calculator import calc_DCE_properties_single

def Test_Noiseless_v6_Tofts_Phantom(output_folder=''):

    # See more details at the following link: https://sites.duke.edu/dblab/files/2015/05/Dynamic_v6_beta1_description_Rev1.pdf

    input_DCE = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','qtim_tools', 'test_data','test_data_dce','tofts_v6.nii.gz'))

    input_AIF = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','qtim_tools', 'test_data','test_data_dce','tofts_v6-AIF-label.nii.gz'))

    outfile_prefix = os.path.join(output_folder, 'tofts_v6_')

    # Increase this number for parallel processing. Speed is greatly increased with parallelization.
    # Note that processing takes an especially long amount of time for the noiseless phantoms, as they have 1300+ timepoints.
    processes = 4

    calc_DCE_properties_single(input_DCE, label_file=[], param_file=[], AIF_label_file=[], AIF_value_data=[], convert_AIF_values=False, outputs=['ktrans','ve','auc'], T1_tissue=1000, T1_blood=1440, relaxivity=.0045, TR=5, TE=2.1, scan_time_seconds=(11*60), hematocrit=0.45, injection_start_time_seconds=60, flip_angle_degrees=30, label_suffix=[], AIF_mode='label_average', AIF_label_suffix='-AIF-label', AIF_label_value=1, label_mode='separate', default_population_AIF=False, initial_fitting_function_parameters=[.01,.1], outfile_prefix=outfile_prefix, processes=processes, mask_threshold=20, mask_value=-1, gaussian_blur=0, gaussian_blur_axis=-1)

def Test_Noiseless_Gradient_Tofts_Phantom(output_folder=''):

    # A continuous gradient version of the Phatnom described at: https://sites.duke.edu/dblab/files/2015/05/Dynamic_v6_beta1_description_Rev1.pdf

    input_DCE = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','qtim_tools', 'test_data','test_data_dce','gradient_tofts_v6.nii'))

    input_AIF = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','qtim_tools', 'test_data','test_data_dce','gradient_tofts_v6-AIF-label.nii.gz'))

    outfile_prefix = os.path.join(output_folder, 'gradient_tofts_v6_')

    # Increase this number for parallel processing. Speed is greatly increased with parallelization.
    # Note that processing takes an especially long amount of time for the noiseless phantoms, as they have 1300+ timepoints.
    processes = 4

    calc_DCE_properties_single(input_DCE, label_file=[], param_file=[], AIF_label_file=[], AIF_value_data=[], convert_AIF_values=False, outputs=['ktrans','ve','auc'], T1_tissue=1000, T1_blood=1440, relaxivity=.0045, TR=5, TE=2.1, scan_time_seconds=(11*60), hematocrit=0.45, injection_start_time_seconds=60, flip_angle_degrees=30, label_suffix=[], AIF_mode='label_average', AIF_label_suffix='-AIF-label', AIF_label_value=1, label_mode='separate', default_population_AIF=False, initial_fitting_function_parameters=[.01,.1], outfile_prefix=outfile_prefix, processes=processes, mask_threshold=20, mask_value=-1, gaussian_blur=0, gaussian_blur_axis=-1)

def Test_Noisy_v9_Tofts_Phantom(output_folder=''):

    # See more details at the following link: https://sites.duke.edu/dblab/files/2015/05/Dynamic_v6_beta1_description_Rev1.pdf
    # This phantom is meant to have a relatively high signal to noise ratio. Other, even noisier phantoms can be found at the link above.

    input_DCE = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','qtim_tools', 'test_data','test_data_dce','tofts_v9.nii'))

    input_AIF = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','qtim_tools', 'test_data','test_data_dce','tofts_v9-AIF-label.nii'))

    outfile_prefix = os.path.join(output_folder, 'tofts_v9_')

    # Increase this number for parallel processing. Speed is greatly increased with parallelization.
    processes = 4

    calc_DCE_properties_single(input_DCE, label_file=[], param_file=[], AIF_label_file=[], AIF_value_data=[], convert_AIF_values=False, outputs=['ktrans','ve','auc'], T1_tissue=1000, T1_blood=1440, relaxivity=.0045, TR=5, TE=2.1, scan_time_seconds=(6*60), hematocrit=0.45, injection_start_time_seconds=60, flip_angle_degrees=30, label_suffix=[], AIF_mode='label_average', AIF_label_suffix='-AIF-label', AIF_label_value=1, label_mode='separate', default_population_AIF=False, initial_fitting_function_parameters=[.3,.3], outfile_prefix=outfile_prefix, processes=processes, mask_threshold=-1, mask_value=-1, gaussian_blur=0, gaussian_blur_axis=-1)

def Run_Tests(output_folder=''):
    Test_Noiseless_v6_Tofts_Phantom(output_folder)
    Test_Noiseless_Gradient_Tofts_Phantom(output_folder)
    Test_Noisy_v9_Tofts_Phantom(output_folder)

if __name__ == "__main__":
    Run_Tests(output_folder='')



