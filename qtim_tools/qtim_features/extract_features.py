""" This 'learner' program, perhaps wrongly named, is the my current
    general utility function. It takes in a folder full of images and
    labels, parses them into numpy arrays, extracts features from those
    arrays, and writes them into an easily accessible .csv. As of yet,
    it does not do any learning..
"""

# import 

import warnings

warnings.filterwarnings('ignore', '.*floating.*')
warnings.filterwarnings("ignore", message=".*dtype size changed.*")

import glob
import os
import numpy as np
import csv

from qtim_tools.qtim_features import morphology, statistics, GLCM
from qtim_tools.qtim_utilities import nifti_util
from qtim_tools.qtim_utilities.array_util import truncate_image, split_image, extract_maximal_slice
from qtim_tools.qtim_utilities.file_util import grab_files_recursive

feature_dictionary = {'GLCM': GLCM, 'morphology': morphology, 'statistics': statistics}


def generate_feature_list(input_file, label_file=None, features=['GLCM', 'morphology', 'statistics'], recursive=False, set_label='', levels=255, normalize_intensities=True, mask_value=0, use_labels=[-1], erode=[0, 0, 0], mode="whole_volume", filenames=True, featurenames=True, outfile='', overwrite=True, clear_file=True, write_empty=True, return_output=False, test=False):

    total_features, feature_indexes, label_output = generate_feature_indices(features, featurenames)

    # This needs to be restructured, probably with a new method to iterate through images. Currently, this will not work
    # wtihout an output file. The conflict is between retaining the ability to append to files in real-time (to prevent
    # catastrophic errors from wasting eons of processing time) and having a conditional "outfile" parameter.

    if label_file is None:
        labels = False
    else:
        labels = True

    if outfile != '':
        outfile = determine_outfile_name(outfile, overwrite)

        if clear_file:
            open(outfile, 'w').close()

        with open(outfile, 'ab') as writefile:
            csvfile = csv.writer(writefile, delimiter=',')
            csvfile.writerow(label_output[0, :])

            imagepaths, label_images = [input_file], label_file
            
            numerical_output = np.zeros((1, total_features), dtype=float)
            index_output = np.zeros((1, 1), dtype=object)

            for imagepath in imagepaths:

                print('\n')
                print('Pre-processing data...')

                image_list, unmodified_image_list, imagename_list, attributes_list = generate_numpy_images(imagepath, labels=labels, constant_label=label_images, levels=levels, mask_value=mask_value, use_labels=use_labels, erode=erode, mode=mode)
                
                if image_list == []:
                    if write_empty:
                        empty_output = np.zeros((1, total_features + 1), dtype=object)
                        empty_output[0,0] = imagepath
                        csvfile.writerow(empty_output[0,:])
                        continue

                print('Pre-processing complete!')

                # print image_list
                for image_idx, image in enumerate(image_list):

                    print('')
                    print('Working on image...')
                    print((imagename_list[image_idx]))
                    print('Voxel sum...')
                    print((np.sum(image)))
                    print('Image shape...')
                    print((image.shape))

                    if filenames:
                        index = imagename_list[image_idx]
                    else:
                        index = numerical_output.shape[0]

                    if numerical_output[0,0] == 0:
                        numerical_output[0, :] = generate_feature_list_method(image, unmodified_image_list[image_idx], attributes_list[image_idx], features, feature_indexes, total_features, levels, mask_value=mask_value, normalize_intensities=normalize_intensities)
                        index_output[0,:] = index
                    else:
                        numerical_output = np.vstack((numerical_output, generate_feature_list_method(image, unmodified_image_list[image_idx], attributes_list[image_idx], features, feature_indexes, total_features, levels, mask_value=mask_value, normalize_intensities=normalize_intensities)))
                        index_output = np.vstack((index_output, index))

                    csvfile.writerow(np.hstack((index_output[-1, :], numerical_output[-1, :])))

    final_output = np.hstack((index_output, numerical_output))

    print('Feature writing complete, writing output...')
    print('\n')

    print('Raw Output:')
    for col_id in range(final_output.shape[1]):
        print((label_output[0, col_id], final_output[:, col_id]))

    if return_output:
        return final_output


def generate_feature_list_batch(folder, file_regex='*.nii*', features=['GLCM', 'morphology', 'statistics'], recursive=False, labels=False, label_suffix="-label", set_label='',  levels=255, normalize_intensities=True, mask_value=0, use_labels=[-1], erode=[0,0,0], mode="whole_volume", filenames=True, featurenames=True, outfile='', overwrite=True, clear_file=True, write_empty=True, return_output=False, test=False):

    total_features, feature_indexes, label_output = generate_feature_indices(features, featurenames)

    # This needs to be restructured, probably with a new method to iterate through images. Currently, this will not work
    # wtihout an output file. The conflict is between retaining the ability to append to files in real-time (to prevent
    # catastrophic errors from wasting eons of processing time) and having a conditional "outfile" parameter.

    if outfile != '':
        outfile = determine_outfile_name(outfile, overwrite)

        if clear_file:
            open(outfile, 'w').close()

        with open(outfile, 'ab') as writefile:
            csvfile = csv.writer(writefile, delimiter=',')
            csvfile.writerow(label_output[0,:])

            imagepaths, label_images = generate_filename_list(folder, file_regex, labels, label_suffix, set_label, recursive)
            
            numerical_output = np.zeros((1, total_features), dtype=float)
            index_output = np.zeros((1, 1), dtype=object)

            for imagepath in imagepaths:

                print('\n')
                print('Pre-processing data...')

                image_list, unmodified_image_list, imagename_list, attributes_list = generate_numpy_images(imagepath, labels=labels, label_suffix=label_suffix, set_label=set_label, label_images=label_images, levels=levels, mask_value=mask_value, use_labels=use_labels, erode=erode, mode=mode)
                
                if image_list == []:
                    if write_empty:
                        empty_output = np.zeros((1, total_features + 1), dtype=object)
                        empty_output[0,0] = imagepath
                        csvfile.writerow(empty_output[0,:])
                        continue

                print('Pre-processing complete!')

                for image_idx, image in enumerate(image_list):

                    print('')
                    print('Working on image...')
                    print((imagename_list[image_idx]))
                    print('Voxel sum...')
                    print((np.sum(image)))
                    print('Image shape...')
                    print((image.shape))

                    if filenames:
                        index = imagename_list[image_idx]
                    else:
                        index = numerical_output.shape[0]

                    if numerical_output[0,0] == 0:
                        numerical_output[0, :] = generate_feature_list_method(image, unmodified_image_list[image_idx], attributes_list[image_idx], features, feature_indexes, total_features, levels, mask_value=mask_value, normalize_intensities=normalize_intensities)
                        index_output[0,:] = index
                    else:
                        numerical_output = np.vstack((numerical_output, generate_feature_list_method(image, unmodified_image_list[image_idx], attributes_list[image_idx], features, feature_indexes, total_features, levels, mask_value=mask_value, normalize_intensities=normalize_intensities)))
                        index_output = np.vstack((index_output, index))

                    csvfile.writerow(np.hstack((index_output[-1,:], numerical_output[-1,:])))

    final_output = np.hstack((index_output, numerical_output))

    print('Feature writing complete, writing output...')
    print('\n')

    for row in final_output:
        print(row)

    if return_output:
        return final_output

def generate_numpy_images(imagepath, labels=False, label_suffix='-label', set_label='', label_images=[], mask_value=0, levels=255, use_labels=[-1], erode=0, mode="whole_volume", constant_label=None):

    image_list = []
    unmodified_image_list = []
    imagename_list = []
    attributes_list = []
    
    # nifti_util.save_alternate_nifti(imagepath, levels, mask_value=mask_value)
    image = nifti_util.nifti_2_numpy(imagepath)

    # This is likely redundant with the basic assert function in nifti_util
    if not nifti_util.assert_3D(image):
        print(('Warning: image at path ' + imagepath + ' has multiple time points or otherwise greater than 3 dimensions, and will be skipped.'))
        return [[],[],[],[]]

    if labels:

        if constant_label is not None:
            label_path = constant_label
        elif set_label != '':
            label_path = os.path.join(os.path.dirname(imagepath), os.path.basename(os.path.normpath(set_label)))
        else:
            head, tail = os.path.split(imagepath)
            split_path = str.split(tail, '.')
            label_path = split_path[0] + label_suffix + '.' + '.'.join(split_path[1:])
            label_path = os.path.join(head, label_path)

        if os.path.isfile(label_path):
            label_image = nifti_util.nifti_2_numpy(label_path)

            if label_image.shape != image.shape:
                print('Warning: image and label do not have the same dimensions. Imaging padding support has not yet been added. This image will be skipped.')
                return [[],[],[],[]]

            # In the future: create an option to analyze each frame separately.
            if not nifti_util.assert_3D(label_image):
                print(('Warning: image at path ' + imagepath + ' has multiple time points or otherwise greater than 3 dimensions, and will be skipped.'))
                return [[],[],[],[]]

            label_image = label_image.astype(int)
            label_indices = np.unique(label_image)

            if label_indices.size == 1:
                print(('Warning: image at path ' + imagepath + ' has an empty label-map, and will be skipped.'))
                return[[],[],[],[]]

            # Will break if someone puts in '0' as a label to use.
            if use_labels[0] != -1:
                label_indices = np.array([0] + [x for x in label_indices if x in use_labels])

            split_images = split_image(image, label_image, label_indices, mask_value=mask_value)
            masked_images = [truncate_image(x) for x in split_images]

            for masked_image in masked_images:

                unmodified_image_list += [np.copy(masked_image)]

                masked_image = nifti_util.coerce_levels(masked_image, levels=levels, reference_image=image, method="divide", mask_value=mask_value)

                # It would be nice in the future to check if an image is too small to erode. Maybe a minimum-size parameter?
                # Or maybe a "maximum volume reduction by erosion?" Hmm..
                masked_image = nifti_util.erode_label(masked_image, iterations=erode)

                # This is very ineffecient. TODO: Restructure this section.
                if mode == "maximal_slice":
                    image_list += [extract_maximal_slice(masked_image, mode='non_mask')[:, :, np.newaxis]]
                else:
                    image_list += [masked_image]

            if set_label == '':
                filename = str.split(label_path, '\\')[-1]
            else:
                filename = imagepath

            if label_indices.size == 2:
                imagename_list += [filename]
            else:
                split_filename = str.split(filename, '.')
                for labelval in label_indices[1:]:
                    filename = split_filename[0] + '_' + str(int(labelval)) + '.' + split_filename[1]
                    imagename_list += [filename]

            attributes_list += [nifti_util.return_nifti_attributes(imagepath)] * (label_indices.size - 1)
            print(('Finished... ' + str.split(imagepath, '\\')[-1]))

        else:
            print(('Warning: image at path ' + imagepath + ' has no label-map, and will be skipped.'))
            return[[],[],[],[]]

    else:
        image = nifti_util.coerce_levels(image, levels=levels, reference_image=image, method="divide", mask_value=mask_value)
        image_list += [image]
        unmodified_image_list += [image]
        imagename_list += [imagepath]
        attributes_list += [nifti_util.return_nifti_attributes(imagepath)]

    return [image_list, unmodified_image_list, imagename_list, attributes_list]

def generate_feature_list_method(image, unmodified_image, attributes, features, feature_indexes='', total_features='', levels=-1, mask_value=0, normalize_intensities=False):

    if feature_indexes == '' or total_features == '':
        total_features = 0
        feature_indexes = [0]

        for feature in features:
            total_features += feature_dictionary[feature].feature_count()
            if feature_indexes == [0]:
                feature_indexes = [0, feature_dictionary[feature].feature_count()]
            else:
                feature_indexes += [feature_indexes[-1] + feature_dictionary[feature].feature_count()]

    numerical_output = np.zeros((1, total_features), dtype=float)

    if (image != mask_value).sum() == 0:
        print('Warning: image is empty, either because it could not survive erosion or because of another error. It will be skipped.')
        return numerical_output

    glcm_image = np.copy(image)
    glcm_image = glcm_image.astype(int)

    for feature_idx, feature in enumerate(features):

        if feature == 'GLCM':

            levels += 1
            print('Calculating GLCM...')
            numerical_output[0, feature_indexes[feature_idx]:feature_indexes[feature_idx+1]] = GLCM.glcm_features(glcm_image, levels=levels)

        if feature == 'morphology':

            print('Calculating morphology features...')
            numerical_output[0, feature_indexes[feature_idx]:feature_indexes[feature_idx+1]] = morphology.morphology_features(unmodified_image, attributes)

        if feature == 'statistics':

            # Should intensity statistics be eroded? Currently, they are not, as indicated by the "unmodified image" parameter.

            print('Calculating statistical features...')
            if normalize_intensities:
                numerical_output[0, feature_indexes[feature_idx]:feature_indexes[feature_idx+1]] = statistics.statistics_features(glcm_image)
            else:
                numerical_output[0, feature_indexes[feature_idx]:feature_indexes[feature_idx+1]] = statistics.statistics_features(unmodified_image)

    print('\n')

    return numerical_output

def generate_feature_indices(features=['GLCM', 'morphology', 'statistics'], featurenames=True):

    total_features = 0
    feature_indexes = [0]

    for feature in features:
        total_features += feature_dictionary[feature].feature_count()
        if feature_indexes == [0]:
            feature_indexes = [0, feature_dictionary[feature].feature_count()]
        else:
            feature_indexes += [feature_indexes[-1] + feature_dictionary[feature].feature_count()]
    
    if featurenames:
        label_output = np.zeros((1, total_features+1), dtype=object)
        for feature_idx, feature in enumerate(features):
            label_output[0, (1+feature_indexes[feature_idx]):(1+feature_indexes[feature_idx+1])] = feature_dictionary[feature].featurename_strings()
        label_output[0,0] = 'index'

    return [total_features, feature_indexes, label_output]

def generate_filename_list(folder, file_regex='*.nii*', labels=False, label_suffix='-label', set_label='', recursive=False):

    if recursive:
        imagepaths = grab_files_recursive(folder, file_regex)
    else:
        imagepaths = glob.glob(os.path.join(folder, file_regex))

    if labels:
        if set_label == '':
            label_images = [x for x in imagepaths if label_suffix in x]
            imagepaths = [x for x in imagepaths if label_suffix not in x]
        else:
            label_images = [os.path.join(os.path.dirname(x), os.path.basename(set_label)) if os.path.exists(x) else '' for x in imagepaths]
            imagepaths = [x for x in imagepaths if os.path.join(os.path.dirname(x), os.path.basename(set_label)) not in x]
    else:
        label_images = []

    if imagepaths == []:
        raise ValueError("There are no .nii or .nii.gz images in the provided folder.")
    if labels and label_images == []:
        raise ValueError("There are no labels with the provided suffix in this folder. If you do not want to use labels, set the \'labels\' flag to \'False\'. If you want to change the label file suffix (default: \'-label\'), then change the \'label_suffix\' flag.")

    return [imagepaths, label_images]


def determine_outfile_name(outfile, overwrite=True):
    
    write_flag = False
    while not write_flag:
        if not os.path.isfile(outfile):
            write_flag = True
            continue
        if overwrite:
            write_flag = True
        else:
            split_outfile = str.split(outfile, '.')
            print(split_outfile)
            outfile = '.'.join(split_outfile[0:-1]) + '_new.' + split_outfile[-1]
            if not os.path.isfile(outfile):
                write_flag = True

    return outfile


def test_method():
    test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','test_data','test_data_features','MR_Tumor_Shape'))
    generate_feature_list_batch(folder=test_folder, features=['morphology'], labels=True, levels=100, outfile='test_feature_results_shape.csv',test=False, mask_value=0, erode=[0,0,0], overwrite=True)
    return


def extract_features(folder, outfile, labels=True, features=['GLCM','morphology', 'statistics'], levels=100, mask_value=0, erode=[0,0,0], overwrite=True, label_suffix='-label', set_label='', file_regex='*.nii*', recursive=False, normalize_intensities=False):
    generate_feature_list_batch(folder=folder, outfile=outfile, labels=labels, features=features, levels=levels, mask_value=mask_value, erode=erode, overwrite=overwrite, label_suffix=label_suffix, set_label=set_label, file_regex=file_regex, recursive=recursive, normalize_intensities=normalize_intensities)


if __name__ == "__main__":

    np.set_printoptions(suppress=True, precision=2)
    test_method()
    # test_parallel()