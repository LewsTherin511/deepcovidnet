import pandas as pd
import os

def main():

	raw_features_file = "/home/lews/PycharmProjects/covid_deepcovidnet/deepcovidnet/data/OxCGRT_latest.csv"
	df = pd.read_csv(raw_features_file,
				 usecols=[
					 'CountryName',
					 'CountryCode',
					 'RegionName',
					 'RegionCode',
					 'Date',
					 'C1_School closing',
					 'C2_Workplace closing',
					 'C3_Cancel public events',
					 'C4_Restrictions on gatherings',
					 'C5_Close public transport',
					 'C6_Stay at home requirements',
					 'C7_Restrictions on internal movement',
					 'C8_International travel controls',
					 'E1_Income support',
					 'E2_Debt/contract relief',
					 'E3_Fiscal measures',
					 'E4_International support',
					 'H1_Public information campaigns',
					 'H2_Testing policy',
					 'H3_Contact tracing',
					 'H4_Emergency investment in healthcare',
					 'H5_Investment in vaccines',
					 'H6_Facial Coverings'],
					 	parse_dates=['Date'],
					  index_col='CountryName')

	df_grouped_by_country = df.groupby('Date')

	for group_date in df_grouped_by_country.groups:
		current_time = group_date.to_pydatetime()
		year = current_time.year
		month = current_time.month
		day = current_time.day
		out_folder = f"data/jsi-OxCGRT/{year:02d}/{month:02d}/{day:02d}"
		if not os.path.exists(out_folder):
			os.makedirs(out_folder)
		with open(f"{out_folder}/{year:02d}-{month:02d}-{day:02d}-OxCGRT.csv", "w+") as out_file:
			df_temp = df.loc[df['Date'] == group_date]
			df_temp.to_csv(out_file)


if __name__ == "__main__":
	main()
