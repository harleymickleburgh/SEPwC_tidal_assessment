"""Module for analysing tidal data"""
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
    """reads the data and turns it into a useable format """
    #skip the stuff at the top of the file
    tide_data = pd.read_csv(filename, skiprows=11, sep=r'\s+', header=None)

    #Combine the date and time strings
    datetime_str = tide_data[1] + ' ' + tide_data[2]
    tide_data['Time'] = pd.to_datetime(datetime_str)

    #convert sea level and remove letters and stuff from numbers so the maths works
    tide_data['Sea Level'] = tide_data[3].replace(r'[^0-9.-]', '', regex=True)
    tide_data['Sea Level'] = pd.to_numeric(tide_data['Sea Level'], errors= 'coerce')

    #set outliers to NaN to be removed later
    tide_data['Sea Level'] = tide_data['Sea Level'].mask(tide_data['Sea Level'] < -10)

    #set index but keep time and sea level column for test
    tide_data.set_index('Time', inplace=True)
    
    resampled_data = tide_data[['Sea Level']].resample('h').mean()
    
    resampled_data['Time'] = resampled_data.index

    return resampled_data[['Sea Level', 'Time']]

def extract_single_year_remove_mean(year, data):
    """groups data from single year to calculate a yearly average"""
    #defining the time range
    year_string_start = str(year)+"0101"
    year_string_end = str(year)+"1231"
    year_data = data.loc[year_string_start:year_string_end, ['Sea Level']]

    #averaging out the sea level
    mmm = np.mean(year_data['Sea Level'])
    year_data['Sea Level'] -= mmm

    return year_data


def extract_section_remove_mean(start, end, data):
    """calculates the actual height of each wave without sea level """
    #take only rows between start and end dates
    section_data = data.loc[start:end, ['Sea Level']].copy()

    #calculate the mean sea level for this section
    section_mean = section_data['Sea Level'].mean()

    #subtract mean from every value in section
    section_data['Sea Level'] = section_data['Sea Level'] - section_mean

    return section_data

def join_data(data1, data2):
    """combines data to allow for easier analysis"""
    combined = pd.concat([data1, data2])
    combined.sort_index(inplace=True)

    return combined

def sea_level_rise(data):
    """calculates the sea level rise from year to year"""
    #remove rows where sea level data is missing
    clean_data = data.dropna(subset=['Sea Level'])

    #calculate days since first data point
    x_data = (clean_data.index - clean_data.index[0]).total_seconds().values / 86400.0
    y_data = clean_data['Sea Level'].values

    #regression for slope and intercept
    slope, _, _, p, _ = stats.linregress(x_data, y_data)

    return slope, p

def tidal_analysis(data, constituents, start_datetime):
    """harmonic analysis on sea level data using specific consituents""" 
    tide = uptide.Tides(constituents) #this allows for analysis of all types of wave M2 S2 etc
    tide.set_initial_time(start_datetime)
    
    #remove missing data 
    clean_data = data.dropna(subset=['Sea Level'])
    sea_level = clean_data['Sea Level'].values

    if clean_data.index.tz is None:
        localized_index = clean_data.index.tz_localize('UTC')
    else:
        localized_index = clean_data.index

    #convert daetimes to seconds
    times = (localized_index - start_datetime).total_seconds().values

    #harmonic analysis
    amp, pha = uptide.analysis.harmonic_analysis(tide, sea_level, times)

    return amp, pha

def get_longest_contiguous_data(data):
    """finds longest time with continous data"""

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
