import argparse
import sys

import qtim_tools

class qtim_commands(object):

    def __init__(self):
        parser = argparse.ArgumentParser(
            description='A number of pre-packaged command used by the Quantiative Tumor Imaging Lab at the Martinos Center',
            usage='''qtim <command> [<args>]

The following commands are available:
   coregistration      Coregister data to one volume, or through a series of steps.
   deep_learning       Preprocess coregistered volumes for deep learning analysis.
   dti_conversion      Generate DTI volumes from RAWDATA.
   label_statistics    Generate label statistics from the COREGISTRATION folder.
''')

        parser.add_argument('command', help='Subcommand to run')
        args = parser.parse_args(sys.argv[1:2])

        if not hasattr(self, args.command):
            print 'Sorry, that\'s not one of the commands.'
            parser.print_help()
            exit(1)

        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def coregistration(self):
        parser = argparse.ArgumentParser(
            description='Coregister QTIM volumes to one volume, or according to a series of steps in a configuration file.')

        parser.add_argument('study_name', type=str)
        parser.add_argument('base_directory', type=str)
        parser.add_argument('-destination_volume', type=str)
        parser.add_argument('-config', type=str)   

        args = parser.parse_args(sys.argv[2:])
        print 'Coregistering volumes for study directory... %s' % args.study_name

        qtim_tools.qtim_pipelines.coregistration.coregistration(args.study_name, args.base_directory, args.destination_volume, args.config)

    def deep_learning(self):
        parser = argparse.ArgumentParser(
            description='Prepare a study for a deep learning experiment. Performs N4 bias correction, skull-stripping, isotropic resampling, and zero-mean normalization.')

        parser.add_argument('study_name', type=str)
        parser.add_argument('base_directory', type=str)
        parser.add_argument('-skull_strip_label', type=str)
        parser.add_argument('-config', type=str)   

        args = parser.parse_args(sys.argv[2:])
        print 'Preprocessing for deep learning in study directory... %s' % args.study_name

        qtim_tools.qtim_pipelines.deep_learning.deep_learning_preprocess(args.study_name, args.label_name, args.base_directory)

    def dti_conversion(self):
        parser = argparse.ArgumentParser(
            description='Generate DTI modalities from QTIM study raw data.')

        parser.add_argument('study_name', type=str)
        parser.add_argument('base_directory', type=str)       
        parser.add_argument('-output_modalities', type=str)
        parser.add_argument('-overwrite', type=bool)         
        parser.add_argument('-config', type=str)   

        args = parser.parse_args(sys.argv[2:])
        print 'Running DTI conversion on study directory... %s' % args.study_name

        qtim_tools.qtim_pipelines.dti_conversion.qtim_dti_conversion(args.study_name, args.base_directory, args.output_modalities, args.overwrite)

    def label_statistics(self):
        parser = argparse.ArgumentParser(
            description='Generate label statistics from a QTIM study and a given ROI.')

        parser.add_argument('study_name', type=str)
        parser.add_argument('label_name', type=str)
        parser.add_argument('base_directory', type=str)
        parser.add_argument('-output_csv', type=str)
        parser.add_argument('-label_mode', type=str)
        parser.add_argument('-config', type=str)   

        args = parser.parse_args(sys.argv[2:])
        print 'Running label statistics on study directory... %s' % args.study_name

        qtim_tools.qtim_pipelines.label_statistics.qtim_study_statistics(args.study_name, args.label_name, args.base_directory, args.output_csv, args.label_mode)


def main():
    qtim_commands()