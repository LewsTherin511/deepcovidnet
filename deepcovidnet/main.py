import sys
sys.path.append("/home/lews/PycharmProjects/covid_deepcovidnet")

import deepcovidnet.config.global_config as global_config

from deepcovidnet.CovidRunner import CovidRunner
from deepcovidnet.OrdinalCovidRunner import OrdinalCovidRunner
from deepcovidnet.CoralRunner import CoralRunner

from deepcovidnet.CovidCountyDataset import CovidCountyDataset
from deepcovidnet.DataSaver import DataSaver
import deepcovidnet.config.model_hyperparam_config as hyperparams
import deepcovidnet.config.CovidCountyDatasetConfig as dataset_config
from deepcovidnet.CovidExperiment import CovidExperiment
from deepcovidnet.FeatureAnalyzer import FeatureAnalyzer, AnalysisType

import argparse
from torch.utils.data import DataLoader
import logging
from datetime import datetime
import pickle
import numpy as np


def get_train_val_test_datasets(mode, use_cache=True, load_features=False):
    assert mode in ['all', 'train', 'train_no_val', 'test']

    train_start = global_config.data_start_date
    val_start   = global_config.train_end_date
    test_start  = global_config.val_end_date
    end_date    = global_config.data_end_date

    train_dataset = None
    val_dataset   = None
    test_dataset  = None

    if mode in ['all', 'train', 'train_no_val']:
        train_dataset = CovidCountyDataset(
            train_start,
            val_start,
            means_stds=None,
            use_cache=use_cache,
            load_features=load_features
        )

        if mode != 'train_no_val':
            val_dataset = CovidCountyDataset(
                val_start,
                test_start,
                means_stds=train_dataset.means_stds,
                use_cache=use_cache,
                load_features=load_features
            )

    if mode in ['all', 'test']:
        means_stds = None

        if not use_cache:
            assert mode == 'all', 'mode can\'t be test when use_cache=False'
            means_stds = train_dataset.means_stds

        test_dataset = CovidCountyDataset(
            test_start,
            end_date,
            means_stds=means_stds,
            use_cache=use_cache,
            load_features=load_features
        )

    return train_dataset, val_dataset, test_dataset


def get_train_val_test_loaders(mode, load_features=False):
    assert mode in ['all', 'train', 'train_no_val', 'test']

    train_dataset, val_dataset, test_dataset = get_train_val_test_datasets(mode, load_features=load_features)
    train_loader = None
    val_loader = None
    test_loader = None

    if mode in ['all', 'train', 'train_no_val']:
        train_loader = DataLoader(
                            train_dataset,
                            batch_size=hyperparams.batch_size,
                            shuffle=True
                        )

        if mode != 'train_no_val':
            val_loader = DataLoader(
                        val_dataset,
                        batch_size=hyperparams.batch_size,
                        shuffle=False
                    )

    if mode in ['all', 'test']:
        test_loader = DataLoader(
                        test_dataset,
                        batch_size=hyperparams.batch_size,
                        shuffle=False
                    )

    return train_loader, val_loader, test_loader


def get_runner(runner_type):
    if runner_type == 'regular':
        return CovidRunner
    elif runner_type == 'ordinal':
        return OrdinalCovidRunner
    elif runner_type == 'coral':
        return CoralRunner


def get_analysis_type(analysis_type):
    if analysis_type == 'feature':
        return AnalysisType.FEATURE
    elif analysis_type == 'group':
        return AnalysisType.GROUP
    elif analysis_type == 'time':
        return AnalysisType.TIME
    elif analysis_type == 'soi':
        return AnalysisType.SOI


def add_args(parser):
    modes = np.array([
        ['train', 'train the model and validate after every epoch'],
        ['train_no_val', 'train the model without validating'],
        ['val', 'evaluate the model on the validation set. Use --load-path to specify model path'],
        ['test', 'evaluate the model on the test set. Use --load-path to specify model path'],
        ['cache', 'cache all normalized feature groups in the train, val and test set so loading them is efficient'],
        ['save', 'save individual feature groups. Specify a relevant save function as defined in DataSaver.py by using --save-func argument'],
        ['tune', 'tune hyperparameters (of medium level and above as defined in model_hyperparam_config.py) by using Bayesian Optimization with Expected Improvement'],
        ['rank', 'rank input features on their importance. Use --analysis-type to decide what exactly to rank']
    ])

    parser.add_argument('--exp', required=True, help='a string to name the current experiment (used for tensorboard and other logs)')
    parser.add_argument('--runner', default='ordinal', choices=['regular', 'ordinal'])
    nl = '\n'
    parser.add_argument(
        '--mode', default='train', choices=list(modes[:, 0]),
        help=f'{"".join([modes[i][0] + ": " + modes[i][1] + nl for i in range(len(modes))])}'
    )
    parser.add_argument('--data-dir', default=global_config.data_base_dir)
    parser.add_argument('--data-save-dir', default=global_config.data_save_dir)
    parser.add_argument('--start-date', default=str(global_config.data_start_date))
    parser.add_argument('--end-date', default=str(global_config.data_end_date))
    parser.add_argument('--save-func', default='save_weather_data')
    parser.add_argument('--load-path', default='')
    parser.add_argument('--analysis-type', default='feature', choices=['feature', 'group', 'time', 'soi'])
    parser.add_argument('--load-hps', default='')


def main():
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    global_config.set_static_val('data_base_dir', args.data_dir, overwrite=True)
    global_config.set_static_val('data_save_dir', args.data_save_dir, overwrite=True)

    if args.load_hps:
        hyperparams.load(args.load_hps)

    if args.mode == 'train' or args.mode == 'train_no_val':
        train_loader, val_loader, _ = get_train_val_test_loaders(args.mode)

        for b in train_loader:
            b.pop(dataset_config.labels_key)
            break  # just init b with a batch

        runner = get_runner(args.runner)(args.exp, load_path=args.load_path, sample_batch=b)

        runner.train(train_loader, val_loader=val_loader)

    elif args.mode == 'test' or args.mode == 'val':
        assert args.load_path, 'model path not specified'

        if args.mode == 'val':
            data_loader = get_train_val_test_loaders('train')[1]
        else:
            data_loader = get_train_val_test_loaders(args.mode)[2]

        for b in data_loader:
            b.pop(dataset_config.labels_key)
            break  # just init b with a batch

        runner = get_runner(args.runner)(args.exp, load_path=args.load_path, sample_batch=b)

        runner.test(data_loader)

    elif args.mode == 'cache':
        train_dataset, val_dataset, test_dataset = \
            get_train_val_test_datasets(mode='all', use_cache=False)

        train_dataset.save_cache_on_disk()
        val_dataset.save_cache_on_disk()
        test_dataset.save_cache_on_disk()

    elif args.mode == 'save':
        start_date  = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date    = datetime.strptime(args.end_date, '%Y-%m-%d').date()

        d = DataSaver()
        try:
            getattr(d, args.save_func)(start_date, end_date)
        except TypeError:
            getattr(d, args.save_func)()

    elif args.mode == 'tune':
        train_dataset, val_dataset, _ = get_train_val_test_datasets('train')
        exp = CovidExperiment(
                args.exp,
                get_runner(args.runner),
                train_dataset=train_dataset,
                val_dataset=val_dataset,
                exp_name=args.exp
            )

        best_params, best_vals, _, _ = hyperparams.tune(exp)

        pickle.dump(
            (best_params, best_vals),
            open(global_config.get_best_tune_file(args.exp), 'wb')
        )

    elif args.mode == 'rank':
        assert args.load_path, 'model path not specified'

        val_loader = get_train_val_test_loaders('train', load_features=True)[1]

        for b in val_loader:
            b.pop(dataset_config.labels_key)
            break

        analyzer = FeatureAnalyzer(
            runner=get_runner(args.runner)(args.exp, load_path=args.load_path, sample_batch=b),
            val_loader=val_loader
        )

        results = analyzer.get_ranked_features(
                    get_analysis_type(args.analysis_type)
                )

        print('Feature Analysis Results')
        print('=' * 80)
        print('=' * 80)
        print('=' * 80)
        print('\n' * 3)
        print(results)
        print('\n' * 3)
        print('=' * 80)
        print('=' * 80)
        print('=' * 80)
        print('\n' * 3)


if __name__ == '__main__':
    main()
