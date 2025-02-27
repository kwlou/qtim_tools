""" Reusable utility functions associated with DCE analysis. TODO
    clean up this file.
"""


from qtim_tools.qtim_utilities.nifti_util import save_numpy_2_nifti
from multiprocessing import freeze_support

import numpy as np
import nibabel as nib
import math
import os

def parker_model_AIF(scan_time_seconds, injection_start_time_seconds, time_interval_seconds, image_numpy=None, timepoints=0, output_shape=None):

    """ Creates and AIF of a set duration and with a set bolus arrival time using the Parker model.
    """ 

    if timepoints == 0:
        timepoints = image_numpy.shape[-1]

    if output_shape is None:
        output_shape = (timepoints,)
    else:
        output_shape = output_shape + (timepoints,)

    AIF = np.zeros(output_shape)

    bolus_time = int(np.ceil((injection_start_time_seconds / scan_time_seconds) * timepoints))

    time_series_minutes = time_interval_seconds * np.arange(timepoints-bolus_time) / 60

    # Parker parameters. Taken from their orginal published paper.
    a1 = 0.809
    a2 = 0.330
    T1 = 0.17406
    T2 = 0.365
    sigma1 = 0.0563
    sigma2 = 0.132
    alpha = 1.050
    beta = 0.1685
    s = 38.078
    tau = 0.483

    term_0 = alpha*np.exp(-1 * beta * time_series_minutes) / (1 + np.exp(-s*(time_series_minutes-tau)))
    
    A1 = a1 / (sigma1 * ((2*np.pi)**.5))
    B1 = np.exp(-(time_series_minutes-T1)**2 / (2*sigma1**2))
    term_1 = A1 * B1

    A2 = a2 / (sigma2 * ((2*np.pi)**.5))
    B2 = np.exp(-(time_series_minutes-T2)**2 / (2*sigma2**2))
    term_2 = A2 * B2

    post_bolus_AIF = term_0 + term_1 + term_2

    AIF[..., bolus_time:] = post_bolus_AIF

    return AIF

def convert_intensity_to_concentration(data_numpy, T1_tissue, TR, flip_angle_degrees, injection_start_time_seconds, relaxivity, time_interval_seconds, hematocrit, T1_blood=0, T1_map = []):

    # error suppression
    old_settings = np.seterr(divide='ignore', invalid='ignore')

    flip_angle_radians = flip_angle_degrees*np.pi/180

    if T1_map != []:
        R1_pre = float(1) / float(T1_map)
        R1_pre = np.reshape(R1_pre.shape + (1,))
    elif T1_blood == 0:
        R1_pre = float(1) / float(T1_tissue)
    else:
        R1_pre = float(1) / float(T1_blood)

    a = np.exp(-1 * TR * R1_pre)
    relative_term = (1-a) / (1-a*np.cos(flip_angle_radians))

    dim = len(data_numpy.shape)

    if dim == 1:
        baseline = np.mean(data_numpy[0:int(np.round(injection_start_time_seconds/time_interval_seconds))])
        baseline = np.tile(baseline, data_numpy.shape[-1])
    elif dim > 1 and dim < 5:
        baseline = np.mean(data_numpy[...,0:int(np.round(injection_start_time_seconds/time_interval_seconds))], axis=dim-1)
        baseline = np.tile(np.reshape(baseline, (baseline.shape[0:dim-1] + (1,))), (1,)*(dim-1) + (data_numpy.shape[-1],))
    else:
        print('Dimension error. Please enter an array with dimensions between 1 and 4.')

    output_numpy = np.copy(data_numpy)

    output_numpy = np.nan_to_num(output_numpy / baseline)

    output_numpy = output_numpy * relative_term

    output_numpy = (output_numpy - 1) / (a * (output_numpy * np.cos(flip_angle_radians) - 1))

    output_numpy[output_numpy < 0] = 0

    output_numpy = -1 * (1 / (relaxivity * TR)) * np.log(output_numpy)

    output_numpy = np.nan_to_num(output_numpy)

    np.seterr(**old_settings)

    if T1_blood == 0:
        return output_numpy
    else:
        output_numpy = output_numpy / (1-hematocrit)
        return output_numpy

def estimate_concentration_general(params, contrast_AIF_numpy, time_interval_minutes):

    # A non-optimized version of estimate_concentration that uses numpy. Can take in arbitrary arrays of ktrans and ve.

    e = math.e

    ktrans = params[0]
    ve = params[1]
    kep = ktrans / ve

    time_points = len(contrast_AIF_numpy)

    if type(ktrans) is np.ndarray:
        estimated_concentration = np.zeros(ktrans.shape + (time_points,))
    else:
        estimated_concentration = np.zeros(time_points)

    time_series = np.arange(0, time_points) / (60 / time_interval_minutes)

    log_e = -1 * kep * time_interval_minutes
    capital_E = e**log_e
    log_e_2 = log_e**2

    block_A = (capital_E - log_e - 1)
    block_B = (capital_E - (capital_E * log_e) - 1)
    block_ktrans = ktrans * time_interval_minutes / log_e_2

    for i in range(1, len(contrast_AIF_numpy)):
        term_A = contrast_AIF_numpy[i] * block_A
        term_B = contrast_AIF_numpy[i-1] * block_B
        estimated_concentration[..., i] = estimated_concentration[..., i-1]*capital_E + block_ktrans * (term_A - term_B)

    return estimated_concentration

def estimate_concentration(params, contrast_AIF_numpy, time_interval_minutes):

    # Notation is very inexact here. Clean it up later.

    estimated_concentration = [0]

    append = estimated_concentration.append
    e = math.e
    time_series = np.arange(0, contrast_AIF_numpy.size) / (60 / time_interval_minutes)

    ktrans = params[0]
    ve = params[1]
    kep = ktrans / ve

    log_e = -1 * kep * time_interval_minutes
    capital_E = e**log_e
    log_e_2 = log_e**2

    block_A = (capital_E - log_e - 1)
    block_B = (capital_E - (capital_E * log_e) - 1)
    block_ktrans = ktrans * time_interval_minutes / log_e_2

    for i in range(1, np.size(contrast_AIF_numpy)):
        term_A = contrast_AIF_numpy[i] * block_A
        term_B = contrast_AIF_numpy[i-1] * block_B
        append(estimated_concentration[-1]*capital_E + block_ktrans * (term_A - term_B))

    # Quick, error prone convolution method
    # print estimated_concentration
    # res = np.exp(-1*kep*time_series)
    # estimated_concentration = ktrans * np.convolve(contrast_AIF_numpy, res) * time_series[1]
    # estimated_concentration = estimated_concentration[0:np.size(res)]

    return estimated_concentration

def revert_concentration_to_intensity(data_numpy, reference_data_numpy, T1_tissue, TR, flip_angle_degrees, injection_start_time_seconds, relaxivity, time_interval_seconds, hematocrit, T1_blood=0, T1_map = None, static_baseline=None):

    # Note that this function currently has a broken section.
    # Add functionality for a static baseline T1 i.e. reference_dat

    if T1_map is not None:
        R1_pre = 1 / T1_map
        R1_pre = np.reshape(R1_pre.shape + (1,))
    else:
        R1_pre = 1 / T1_tissue

    flip_angle_radians = flip_angle_degrees*np.pi/180
    a = np.exp(-1 * TR * R1_pre)
    relative_term = (1-a) / (1-a*np.cos(flip_angle_radians))

    if static_baseline is None:
        if len(reference_data_numpy.shape) == 1:
            baseline = np.mean(reference_data_numpy[0:int(np.round(injection_start_time_seconds/time_interval_seconds))])
            baseline = np.tile(baseline, reference_data_numpy.shape[-1])
        if len(reference_data_numpy.shape) == 2:
            baseline = np.mean(reference_data_numpy[:,0:int(np.round(injection_start_time_seconds/time_interval_seconds))], axis=1)
            baseline = np.tile(np.reshape(baseline, (baseline.shape[0], 1)), (1,reference_data_numpy.shape[-1]))
        if len(reference_data_numpy.shape) == 3:
            baseline = np.mean(reference_data_numpy[:,:,0:int(np.round(injection_start_time_seconds/time_interval_seconds))], axis=2)
            baseline = np.tile(np.reshape(baseline, (baseline.shape[0],baseline.shape[1], 1)), (1,1,reference_data_numpy.shape[-1]))        
        if len(reference_data_numpy.shape) == 4:
            baseline = np.mean(reference_data_numpy[:,:,:,0:int(np.round(injection_start_time_seconds/time_interval_seconds))], axis=3)
            baseline = np.tile(np.reshape(baseline, (baseline.shape[0],baseline.shape[1],baseline.shape[2], 1)), (1,1,1,reference_data_numpy.shape[-1]))
    else:
        baseline = static_baseline

    data_numpy = np.exp(data_numpy / (-1 / (relaxivity*TR)))
    data_numpy = (data_numpy * a -1) / (data_numpy * a * np.cos(flip_angle_radians) - 1)
    data_numpy = data_numpy / relative_term
    data_numpy = data_numpy * baseline
    ###

    return data_numpy

def generate_AIF(scan_time_seconds, injection_start_time_seconds, time_interval_seconds, image_numpy=[], AIF_label_numpy=[], AIF_value_data=[], AIF_mode='label_average', dimension=4, AIF_label_value=1):

    """ This function attempts to create AIFs both from 2D and 3D ROIs, or reroutes to population AIFs.
    """

    # It's not clear how to draw labels for 2-D DCE phantoms. For now, I assume that people draw their label at time-point zero.

    if AIF_mode == 'label_average':
        if image_numpy != []:
            if AIF_label_numpy != []:

                AIF_subregion = np.nan_to_num(np.copy(image_numpy))

                if dimension == 3:

                    # Acquiring label mask...
                    label_mask = (AIF_label_numpy[:,:,0] != AIF_label_value)

                    # Reshaped for array broadcasting purposes...
                    label_mask = label_mask.reshape((AIF_label_numpy.shape[0:-1] + (1,)))

                    # Making use of numpy's confusing array tiling dynamic to mask all time points with the label...
                    masked_AIF_subregion = np.ma.array(AIF_subregion, mask=np.tile(label_mask, (1,)*(dimension-1) + (AIF_subregion.shape[-1],)))

                    # Reshaping for ease of calculating the mean...
                    masked_AIF_subregion = np.reshape(masked_AIF_subregion, (np.product(masked_AIF_subregion.shape[0:-1]), masked_AIF_subregion.shape[-1]))

                    AIF = masked_AIF_subregion.mean(axis=0, dtype=np.float64)
                    return AIF

                elif dimension == 4:
                    label_mask = (AIF_label_numpy != AIF_label_value)
                    broadcast_label_mask = np.repeat(label_mask[:,:,:,np.newaxis], AIF_subregion.shape[-1], axis=3)
                    masked_AIF_subregion = np.ma.masked_array(AIF_subregion, mask=broadcast_label_mask)             
                    masked_AIF_subregion = np.reshape(masked_AIF_subregion, (np.product(masked_AIF_subregion.shape[0:-1]), masked_AIF_subregion.shape[-1]))
                    AIF = masked_AIF_subregion.mean(axis=0, dtype=np.float64)
                    return AIF
                else:
                    print('Error: too many or too few dimensions to calculate AIF currently. Unable to calculate AIF.')
                    return []
            else:
                'Error: no AIF label detected. Unable to calculate AIF.'
                return []
        else:
            print('No image provided to AIF function. Set AIF_mode to \'population\' to use a population AIF. Unable to calculate AIF.')
            return []

    if AIF_mode == 'population':
        AIF = parker_model_AIF(scan_time_seconds, injection_start_time_seconds, time_interval_seconds, image_numpy)
        return AIF

    return []

def create_gradient_phantom(output_prefix, output_shape=(20,20), ktrans_range=[.01,.5], ve_range=[.01,.8], scan_time_seconds=120, time_interval_seconds=1, injection_start_time_seconds=40, flip_angle_degrees=15, TR=6.8, relaxivity=.0045, hematocrit=.45, T1_tissue=1350, aif='population'):

    """ TO-DO: Fix the ktrans variation so that it correctly ends in 0.35, instead of whatever
        it currently ends in. Also parameterize and generalize everything for more interesting
        phantoms.
    """

    # Initialize variables
    timepoints = int(scan_time_seconds/time_interval_seconds)
    time_series_minutes = np.arange(0, timepoints) / (60 / time_interval_seconds)
    time_interval_minutes = time_interval_seconds / 60
    print(time_interval_minutes)

    # Create empty phantom, labels, and outputs
    output_phantom_concentration = np.zeros(output_shape + (2, int(scan_time_seconds/time_interval_seconds)), dtype=float)
    output_phantom_signal = np.zeros_like(output_phantom_concentration)

    output_AIF_mask = np.zeros(output_shape + (2,))
    output_region_mask = np.zeros_like(output_AIF_mask)
    output_AIF_mask[:,:,1] = 1
    output_region_mask[:,:,0] = 1
    output_ktrans = np.zeros_like(output_AIF_mask)
    output_ve = np.zeros_like(output_AIF_mask)

    # Create Parker AIF
    AIF = np.array(parker_model_AIF(scan_time_seconds, injection_start_time_seconds, time_interval_seconds, timepoints=int(scan_time_seconds/time_interval_seconds)))
    AIF = AIF[np.newaxis, np.newaxis, np.newaxis, :]
    output_phantom_concentration[:,:,1,:] = AIF

    # Fill in answers
    for ve_idx, ve in enumerate(np.linspace(ktrans_range[0], ktrans_range[1], output_shape[0])):
        for ktrans_idx, ktrans in enumerate(np.linspace(ve_range[0], ve_range[1], output_shape[1])):
            output_ktrans[ve_idx, ktrans_idx, 0] = float(ktrans)
            output_ve[ve_idx, ktrans_idx, 0] = float(ve)

            # print np.squeeze(AIF).shape
            print((ve_idx, ktrans_idx))
            print((ktrans, ve))
            # conc = estimate_concentration([ktrans,ve], np.squeeze(AIF)[:], time_series_minutes)
            # print len(conc)
            # print conc[-1]
            # print len(conc[-1])
            output_phantom_concentration[ve_idx, ktrans_idx,0,:] = estimate_concentration([ktrans,ve], np.squeeze(AIF), time_interval_minutes)

    save_numpy_2_nifti(output_phantom_concentration, None, output_prefix + '_concentrations.nii.gz')
    save_numpy_2_nifti(output_ktrans, None, output_prefix + '_ktrans.nii.gz')
    save_numpy_2_nifti(output_ve, None, output_prefix + '_ve.nii.gz')

    output_phantom_signal = revert_concentration_to_intensity(data_numpy=output_phantom_concentration, reference_data_numpy=None, T1_tissue=T1_tissue, TR=TR, flip_angle_degrees=flip_angle_degrees, injection_start_time_seconds=injection_start_time_seconds, relaxivity=relaxivity, time_interval_seconds=time_interval_seconds, hematocrit=hematocrit, T1_blood=0, T1_map = [], static_baseline=140)

    save_numpy_2_nifti(output_phantom_signal, None, output_prefix + '_phantom.nii.gz')


# def create_4d_from_3d(filepath, stacks=5):

# 	""" Mainly to make something work with NordicICE. TO-DO: Make work with anything but the Tofts phantom.
# 		Also move to nifti_util when that is finished.
# 	"""

# 	nifti_3d = nib.load(filepath)
# 	numpy_3d = nifti_3d.get_data()
# 	numpy_4d = np.zeros((numpy_3d.shape[0], numpy_3d.shape[1], stacks, numpy_3d.shape[2]), dtype=float)
# 	numpy_3d = np.reshape(numpy_3d, (numpy_3d.shape[0], numpy_3d.shape[1], 1, numpy_3d.shape[2]))

# 	numpy_4d = np.tile(numpy_3d, (1,1,stacks,1))

# 	t1_map = np.zeros((numpy_3d.shape[0], numpy_3d.shape[1], stacks), dtype=float)
# 	t1_map[0:50,0:70,:] = 1000
# 	t1_map[t1_map == 0] = 1440

# 	# t1_map = np.reshape(t1_map, (t1_map.shape[0], t1_map.shape[1], 1, t1_map.shape[2]))
# 	# t1_map = np.tile(t1_map, (1,1,5,1))

# 	nifti_util.save_numpy_2_nifti(numpy_4d, filepath, 'tofts_4d.nii')
# 	nifti_util.save_numpy_2_nifti(t1_map, filepath, 'tofts_t1map.nii')

# def revert_concentration_to_intensity(data_numpy, reference_data_numpy, T1_tissue, TR, flip_angle_degrees, injection_start_time_seconds, relaxivity, time_interval_seconds, hematocrit, T1_blood=0, T1_map = []):

# 	if T1_map != []:
# 		R1_pre = 1 / T1_map
# 		R1_pre = np.reshape(R1_pre.shape + (1,))
# 	else:
# 		R1_pre = 1 / T1_tissue

# 	flip_angle_radians = flip_angle_degrees*np.pi/180
# 	a = np.exp(-1 * TR * R1_pre)
# 	relative_term = (1-a) / (1-a*np.cos(flip_angle_radians))

# 	if len(reference_data_numpy.shape) == 1:
# 		baseline = np.mean(reference_data_numpy[0:int(np.round(injection_start_time_seconds/time_interval_seconds))])
# 		baseline = np.tile(baseline, reference_data_numpy.shape[-1])
# 	if len(reference_data_numpy.shape) == 2:
# 		baseline = np.mean(reference_data_numpy[:,0:int(np.round(injection_start_time_seconds/time_interval_seconds))], axis=1)
# 		baseline = np.tile(np.reshape(baseline, (baseline.shape[0], 1)), (1,reference_data_numpy.shape[-1]))
# 	if len(reference_data_numpy.shape) == 3:
# 		baseline = np.mean(reference_data_numpy[:,:,0:int(np.round(injection_start_time_seconds/time_interval_seconds))], axis=2)
# 		baseline = np.tile(np.reshape(baseline, (baseline.shape[0],baseline.shape[1], 1)), (1,1,reference_data_numpy.shape[-1]))
# 	if len(reference_data_numpy.shape) == 4:
# 		baseline = np.mean(reference_data_numpy[:,:,:,0:int(np.round(injection_start_time_seconds/time_interval_seconds))], axis=3)
# 		baseline = np.tile(np.reshape(baseline, (baseline.shape[0],baseline.shape[1],baseline.shape[2], 1)), (1,1,1,reference_data_numpy.shape[-1]))

# 	data_numpy = np.exp(data_numpy / (-1 / (relaxivity*TR)))
# 	data_numpy = (data_numpy * a -1) / (data_numpy * a * np.cos(flip_angle_radians) - 1)
# 	data_numpy = data_numpy / relative_term
# 	data_numpy = data_numpy * baseline
# 	###

# 	return data_numpy

# def estimate_concentration(params, contrast_AIF_numpy, time_interval):

#     # Notation is very inexact here. Clean it up later.

#     estimated_concentration = [0]
#     # if params[0] > 10 or params[1] > 10:
#     #   return estimated_concentration

#     append = estimated_concentration.append
#     e = math.e

#     ktrans = e**params[0]
#     ve = 1 / (1 + e**(-params[1]))
#     kep = ktrans / ve

#     log_e = -1 * kep * time_interval
#     capital_E = e**log_e
#     log_e_2 = log_e**2

#     block_A = (capital_E - log_e - 1)
#     block_B = (capital_E - (capital_E * log_e) - 1)
#     block_ktrans = ktrans * time_interval / log_e_2

#     for i in xrange(1, np.size(contrast_AIF_numpy)):
#         term_A = contrast_AIF_numpy[i] * block_A
#         term_B = contrast_AIF_numpy[i-1] * block_B
#         append(estimated_concentration[-1]*capital_E + block_ktrans * (term_A - term_B))

#     # Quick, error prone convolution method
#     # print estimated_concentration
#         # res = np.exp(-1*kep*time_series)
#         # estimated_concentration = ktrans * np.convolve(contrast_AIF_numpy, res) * time_series[1]
#         # estimated_concentration = estimated_concentration[0:np.size(res)]

#     return estimated_concentration

#     # # Gratuitous plotting snippet for sanity checks
#     # if True and (ve > 0.2):
#     # # if False and index[0] == 0 and index[1] > 11:

#     #     # optimization_path = np.zeros((len(allvecs), 2), dtype=float)
#     #     # for a_idx, allvec in enumerate(allvecs):
#     #     #     optimization_path[a_idx, :] = allvec
#     #     #     print allvec

#     #     # time_series = np.arange(0, contrast_AIF_numpy.size)
#     #     # estimated_concentration = estimate_concentration(result_params, contrast_AIF_numpy, time_interval)

#     #     # difference_term = observed_concentration - estimated_concentration
#     #     # # print sum(power(difference_term, 2))
#     #     # print [ktrans, ve]
#     #     # plt.plot(time_series, estimated_concentration, 'r--', time_series, observed_concentration, 'b--')
#     #     # plt.show()

#     #     # time_series = np.arange(0, contrast_AIF_numpy.size)
#     #     # estimated_concentration = estimate_concentration([.1, .01], contrast_AIF_numpy, time_interval)

#     #     # time_series = np.arange(0, contrast_AIF_numpy.size)
#     #     # estimated_concentration2 = estimate_concentration([.25, .01], contrast_AIF_numpy, time_interval)

#     #     # difference_term = observed_concentration - estimated_concentration
#     #     # # print sum(power(difference_term, 2))

#     #     # plt.plot(time_series, estimated_concentration, 'r--', time_series, estimated_concentration2, 'g--', time_series, observed_concentration, 'b--')
#     #     # plt.show()

#     #     delta = .01
#     #     x = np.arange(0, .35, delta)
#     #     delta = .01
#     #     y = np.arange(0, .5, delta)
#     #     X, Y = np.meshgrid(x, y)
#     #     Z = np.copy(X)

#     #     W = x
#     #     x1 = np.copy(x)
#     #     y1 = np.copy(x)

#     #     for k_idx, ktrans in enumerate(x):
#     #         for v_idx, ve in enumerate(y):
#     #             estimated_concentration = estimate_concentration([ktrans, ve], contrast_AIF_numpy, time_interval)
#     #             difference_term = observed_concentration - estimated_concentration
#     #             Z[v_idx, k_idx] = sum(power(difference_term, 2))

#     #         estimated_concentration = estimate_concentration([ktrans, .1], contrast_AIF_numpy, time_interval)
#     #         difference_term = observed_concentration - estimated_concentration
#     #         W[k_idx] = sum(power(difference_term, 2))

#     #     CS = plt.contourf(X,Y,Z, 30)
#     #     plt.clabel(CS, inline=1, fontsize=10)
#     #     plt.show()

#     #     # plt.plot(optimization_path)
#     #     # plt.show()

# def estimate_concentration(params, contrast_AIF_numpy, time_interval):

#     # Notation is very inexact here. Clean it up later.

#     estimated_concentration = [0]
#     # if params[0] > 10 or params[1] > 10:
#     #   return estimated_concentration

#     append = estimated_concentration.append
#     e = math.e

#     ktrans = params[0]
#     ve = params[1]
#     kep = ktrans / ve

#     log_e = -1 * kep * time_interval
#     capital_E = e**log_e
#     log_e_2 = log_e**2

#     block_A = (capital_E - log_e - 1)
#     block_B = (capital_E - (capital_E * log_e) - 1)
#     block_ktrans = ktrans * time_interval / log_e_2

#     for i in xrange(1, np.size(contrast_AIF_numpy)):
#         term_A = contrast_AIF_numpy[i] * block_A
#         term_B = contrast_AIF_numpy[i-1] * block_B
#         append(estimated_concentration[-1]*capital_E + block_ktrans * (term_A - term_B))

#     # Quick, error prone convolution method
#     # print estimated_concentration
#         # res = np.exp(-1*kep*time_series)
#         # estimated_concentration = ktrans * np.convolve(contrast_AIF_numpy, res) * time_series[1]
#         # estimated_concentration = estimated_concentration[0:np.size(res)]

#     return estimated_concentration


# def integration_test(contrast_sample_numpy, contrast_AIF_numpy, time_interval_seconds, bolus_time, mask_value):

#     observed_concentration = contrast_sample_numpy
#     time_series = np.arange(0, contrast_AIF_numpy.size) / (60 / time_interval_seconds)
#     time_interval = time_series[1]

#     power = np.power
#     sum = np.sum
#     e = math.e

#     def cost_function_bad(params):

#         # The estimate concentration function is repeated locally to eke out every last bit of efficiency
#         # from this massively looping program. As much as possible is calculated outside the loop for
#         # performance reasons. Appending is faster than pre-allocating space in this case - who knew.

#         estimated_concentration = [0]

#         append = estimated_concentration.append

#         ktrans = params[0]
#         ve = params[1]
#         kep = ktrans / ve

#         log_e = -1 * kep * time_interval
#         capital_E = e**log_e
#         log_e_2 = log_e**2

#         block_A = (capital_E - log_e - 1)
#         block_B = (capital_E - (capital_E * log_e) - 1)
#         block_ktrans = ktrans * time_interval / log_e_2

#         # for i in xrange(1, np.size(contrast_AIF_numpy)):
#         #     term_A = contrast_AIF_numpy[i] * block_A
#         #     term_B = contrast_AIF_numpy[i-1] * block_B
#         #     append(estimated_concentration[-1]*capital_E + block_ktrans * (term_A - term_B))

#         # This is a much faster, but less accurate curve generation method
#         res = np.exp(-1*kep*time_series)
#         estimated_concentration = ktrans * np.convolve(contrast_AIF_numpy, res) * time_series[1]
#         estimated_concentration = estimated_concentration[0:np.size(res)]        

#         difference_term = observed_concentration- estimated_concentration
#         difference_term = power(difference_term, 2)

#         return difference_term, observed_concentration, estimated_concentration

#     def cost_function_good(params):

#         # The estimate concentration function is repeated locally to eke out every last bit of efficiency
#         # from this massively looping program. As much as possible is calculated outside the loop for
#         # performance reasons. Appending is faster than pre-allocating space in this case - who knew.

#         estimated_concentration = [0]

#         append = estimated_concentration.append

#         ktrans = params[0]
#         ve = params[1]
#         kep = ktrans / ve

#         log_e = -1 * kep * time_interval
#         capital_E = e**log_e
#         log_e_2 = log_e**2

#         block_A = (capital_E - log_e - 1)
#         block_B = (capital_E - (capital_E * log_e) - 1)
#         block_ktrans = ktrans * time_interval / log_e_2

#         for i in xrange(1, np.size(contrast_AIF_numpy)):
#             term_A = contrast_AIF_numpy[i] * block_A
#             term_B = contrast_AIF_numpy[i-1] * block_B
#             append(estimated_concentration[-1]*capital_E + block_ktrans * (term_A - term_B))

#         # This is a much faster, but less accurate curve generation method
#         # res = np.exp(-1*kep*time_series)
#         # estimated_concentration = ktrans * np.convolve(contrast_AIF_numpy, res) * time_series[1]
#         # estimated_concentration = estimated_concentration[0:np.size(res)]        

#         difference_term = observed_concentration- estimated_concentration
#         difference_term = power(difference_term, 2)

#         return difference_term, observed_concentration, estimated_concentration

#     good_difference_term, good_observed_concentration, good_estimated_concentration = cost_function_good([.02,.01])
#     bad_difference_term, bad_observed_concentration, bad_estimated_concentration = cost_function_bad([.02, .01])

#     output_numpy = np.zeros((good_observed_concentration.size,3), dtype=float)
#     output_numpy = [good_observed_concentration, good_estimated_concentration, bad_estimated_concentration]
#     with open('C:/Users/azb22/Documents/Scripting/CED_NHX_DCE_Comparisons/Integration_Curves.csv', 'wb') as writefile:
#         csvfile = csv.writer(writefile, delimiter=',')
#         for row in output_numpy:
#             csvfile.writerow(row)


#     # plt.plot(time_series, good_difference_term, 'r--', time_series, bad_difference_term, 'g--')
#     # plt.show()

#     # plt.plot(time_series, good_estimated_concentration, 'r--', time_series, bad_estimated_concentration, 'g--', time_series, observed_concentration, 'b--')
#     # plt.show()

if __name__ == "__main__":
	pass