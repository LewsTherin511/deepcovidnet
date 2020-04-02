from torch.utils.data import Dataset
from abc import ABC, abstractmethod
import glob
import pandas as pd
import covid_county_prediction.constants as constants
import numpy as np
import re

class BaseCountyDataset(Dataset, ABC):
    def __init__(self):
        # load all required data here
        self.poi_info = self.get_poi_info()
        self.census = self.make_census_dict()
    
    def get_poi_info(self):
        # get county code for each poi
        county_df = pd.read_csv(constants.PLACE_COUNTY_CBG_FILE, 
                            usecols=['safegraph_place_id', 'countyFIPS'], 
                            dtype={'countyFIPS': str}
            )
        county_df = df.dropna().set_index('safegraph_place_id')

        # get top level category for each poi 
        cat_df = pd.DataFrame()
        for f in os.listdir(constants.CORE_POI_PATH):
            if f.starts_with(constants.CORE_POI_CSV_PREFIX):
                f = os.path.join(constants.CORE_POI_PATH, f)
                temp_df = pd.read_csv(f, usecols=['safegraph_place_id', 'top_category'])
                temp_df = temp_df.dropna().set_index('safegraph_place_id')

                assert len(cat_df.index.intersection(temp_df.index)) == 0
                cat_df = pd.concat([cat_df, temp_df], axis='index')

        final_df = pd.concat([county_df, cat_df], axis='columns')

        return final_df.to_dict(orient='index')

    def make_census_dict(self):
        if __name__ == '__main__':
            main_df = pd.DataFrame()
            for file in glob.glob(constants.PATH_TO_SAFEGRAPH_OPEN_CENSUS_DATA + "cbg_*.csv"):
                df = pd.read_csv(file, converters={
                    'census_block_group': lambda x: str(x)})  # The converter is used to retain leading zeros

                # Convert census block groups to FIPS codes and use as index named FIPS
                df.index = df['census_block_group'].apply(lambda x: x[:5]).astype(
                    int)  # Save only first five chars of index
                df.drop('census_block_group', axis=1, inplace=True)
                df.index.name = "FIPS"

                # Aggregate data by FIPS codes
                df = df.groupby("FIPS").sum()
                main_df = main_df.join(df, how="outer")
            return main_df.to_dict()
    
    def read_sg_patterns(self, csv_file):
        df = pd.read_csv(csv_file, 
                usecols=[
                        'safegraph_place_id', 
                        'date_range_start', 
                        'date_range_end', 
                        'raw_visit_counts',
                        'visits_by_day'
                        # bucketed_dwell_times may be useful to see
                        # how long people stayed
                    ],
                converters={'visits_by_day': (lambda x: np.array([int(s) for s in re.split(r'[,\s]\s*', x.strip('[]'))]))}
            ).set_index('safegraph_place_id')

        if (df['date_range_start'] == df.iloc[0]['date_range_start']).all() and \
            (df['date_range_end'] == df.iloc[0]['date_range_end']).all():  
            
            start_time = df.iloc[0]['date_range_start']
            end_time   = df.iloc[0]['date_range_end']

            df.drop(labels=['date_range_start', 'date_range_end'], axis='columns', inplace=True)

        #start_time and end_time can be processed based on model here

        grouped = df.groupby(
            lambda sg_id : 
                self.poi_info[sg_id]['countyFIPS']
                    if sg_id in self.poi_info and self.poi_info[sg_id]['countyFIPS']
                    else '00000'
        )

        return pd.concat([grouped.raw_visit_counts.sum(), grouped.visits_by_day.apply(np.sum)], axis=1)

    @abstractmethod
    def __len__(self):
        raise NotImplementedError()

    @abstractmethod
    def __getitem__(self, idx):
        raise NotImplementedError()
