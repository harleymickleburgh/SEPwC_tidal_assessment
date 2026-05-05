#import the modules we need
import pandas as pd
import datetime
import os
import numpy as np
import uptide
import pytz
import math
from scipy import stats
import matplotlib.dates as mdates
import argparse


def read_tidal_data(filename):
    #skip the stuff at the top of the file
    tide_data = pd.read_csv(filename, skiprows=11, sep=r'\s+', header=None)

    #Combine the date and time strings
    datetime_str = tide_data[1] + ' ' + tide_data[2]
    tide_data['Date'] = pd.to_datetime(datetime_str)

    #rename column 3 to Sea Level
    tide_data = tide_data.rename(columns={3: "Sea Level"})

    #converting stuff to numbers
    tide_data['Sea Level'] = pd.to_numeric(tide_data['Sea Level'], errors= 'coerce')

    #set index and keep Sea Level column
    tide_data = tide_data.set_index('Date')
    tide_data = tide_data[['Sea Level']]

    #hide sensor errors
    tide_data = tide_data.mask(tide_data['Sea Level'] < -300)

    return tide_data

def extract_single_year_remove_mean(year, data):
    #defining the time range
    year_string_start = str(year)+"0101"
    year_string_end = str(year)+"1231"
    year_data = data.loc[year_string_start:year_string_end, ['Sea Level']]

    #averaging out the sea level
    mmm = np.mean(year_data['Sea Level'])
    year_data['Sea Level'] -= mmm

    return year_data


def extract_section_remove_mean(start, end, data):
    #take only rows between start and end dates
    section_data = data.loc[start:end, ['Sea Level']]

    #calculate the mean sea level for this section
    section_mean = section_data['Sea Level'].mean()

    #subtract mean from every value in section
    section_data['Sea Level'] = section_data['Sea Level'] - section_mean

    return section_data

def join_data(data1, data2):
    combined = pd.concat([data1, data2])
    combined = combined.sort_index()

    return combined

def sea_level_rise(data):
    #convert the index to numbers
    x_data = (data.index - data.index[0]).total_seconds() / (24 *3600)
    
    #regression on time(x) and sea level (y)
    result = stats.linregress(x_data, data['Sea Level'])

    return result.slope, result.pvalue

def tidal_analysis(data, constituents, start_datetime):

    return

def get_longest_contiguous_data(data):

    return


def main(args_list=None):

    parser = argparse.ArgumentParser(
                     prog="UK Tidal analysis",
                     description="Calculate tidal constiuents and RSL from tide gauge data",
                     )

    parser.add_argument("directory",
                    help="the directory containing txt files with data")
    parser.add_argument('-v', '--verbose',
                    action='store_true',
                    default=False,
                    help="Print progress")

    args = parser.parse_args(args_list)
    dirname = args.directory
    verbose = args.verbose

    print("Add your code here to do things!")

if __name__ == '__main__':
    main()
