from covid_county_prediction.config.base_config import Config
import sys
import covid_county_prediction.config.global_config as global_config
import os
import logging


config = Config('Config for CovidCountyDataset')

config.labels_key = 'labels'
config.labels_class_boundaries = [2, 11, 80]  # 0.33, 0.67, 0.9 percentiles

config.num_classifiers = len(config.labels_class_boundaries)
config.num_classes = len(config.labels_class_boundaries) + 1

tensor_dir = os.path.join(global_config.data_save_dir, 'tensors/')
if not os.path.exists(tensor_dir):
    os.mkdir(tensor_dir)


def get_cached_tensors_path(s, e):
    base_file = f'tensors_{str(s)}_{str(e)}.pt'
    loc = os.path.join(tensor_dir, base_file)
    mem_loc = os.path.join('/dev/shm/', base_file)
    if os.path.exists(mem_loc):
        logging.info(f'Leading {base_file} from memory')
        return mem_loc
    return loc


config.get_cached_tensors_path = get_cached_tensors_path

config.num_features = 7

sys.modules[__name__] = config
