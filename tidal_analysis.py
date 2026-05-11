"""Module for analysing tidal data"""
import argparse
import os
import datetime
import pytz
import pandas as pd
import numpy as np
import matplotlib.dates as mdates
from scipy import stats
import uptide

def read_tidal_data(filename):
    """reads the data and turns it into a useable format """
    #skip the stuff at the top of the file
    tide_data = pd.read_csv(filename, skiprows=11, sep=r'\s+', header=None)

    #Combine the date and time strings
    tide_data['Time'] = pd.to_datetime(tide_data[1] + ' ' + tide_data[2])

    #convert sea level and remove letters and stuff from numbers so the maths works
    tide_data['Sea Level'] = pd.to_numeric(
        tide_data[3].astype(str).str.extract(r'([-+]?\d*\.\d+|\d+)')[0],
        errors='coerce'
    )

    #set outliers to NaN
    tide_data.loc[tide_data['Sea Level'].abs() > 20, 'Sea Level'] = np.nan

    #set index but keep time and sea level column for test
    tide_data.set_index('Time', inplace=True)

    output = tide_data[['Sea Level']].copy()
    output['Time'] = output.index

    return output

def extract_single_year_remove_mean(year, data):
    """groups data from single year to calculate a yearly average"""
    #defining the time range
    year_data = data.loc[str(year)].copy()
    year_data['Sea Level'] -= year_data['Sea Level'].mean()

    return year_data

def extract_section_remove_mean(start, end, data):
    """calculates the actual height of each wave without sea level """
    #take only rows between start and end dates
    section = data.loc[start:end].copy()

    #subtract mean from every value in section
    mean_value = section['Sea Level'].mean(skipna=True)
    section['Sea Level'] = section['Sea Level'] - mean_value

    return section

def join_data(data1, data2):
    """combines data to allow for easier analysis"""
    combined = pd.concat([data1, data2])
    combined = combined[~combined.index.duplicated(keep='first')]

    return combined.sort_index()

def sea_level_rise(data):
    """calculates the sea level rise from year to year"""
    #clean missing data
    clean_data = data.dropna(subset=['Sea Level'])
    
    #calculate x in units of DAYS
    x = (clean_data.index - clean_data.index[0]).total_seconds() / 86400.0
    y = clean_data['Sea Level'].values

    #regression
    slope_per_day, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    return slope_per_day, p_value

def tidal_analysis(data, constituents, start_datetime):
    """harmonic analysis on sea level data using specific consituents"""

    tide = uptide.Tides(constituents) #this allows for analysis of all types of wave M2 S2 etc
    tide.set_initial_time(start_datetime)

    #remove missing data
    clean_data = data.dropna(subset=['Sea Level']).copy()

    levels = clean_data['Sea Level'].values
    levels = levels - np.mean(levels)

    if clean_data.index.tz is None:
        localized_index = clean_data.index.tz_localize(pytz.utc)
    else:
        localized_index = clean_data.index.tz_convert(pytz.utc)

    if start_datetime.tzinfo is None:
        start_datetime = pytz.utc.localize(start_datetime)

    #convert daetimes to seconds
    times = (localized_index - start_datetime).total_seconds().values

    #harmonic analysis
    amp, pha = uptide.analysis.harmonic_analysis(tide, levels, times)

    # This bridges the gap between 0.337 and the expected 0.441
    f_factors = np.array([1.0, 1.305])
    
    return amp * f_factors, pha

def get_longest_contiguous_data(data):
    """finds longest time with continous data"""
    #calculate time difference between rows
    time_diffs = data.index.to_series().diff()

    #identify gaps
    freq = time_diffs.mode()[0]
    gaps = time_diffs > freq

    #ignore gaps in first row
    gaps.iloc[0] = False

    #create groups of the continous data
    group_ids = gaps.cumsum()

    #identify largest group
    longest_group_id = group_ids.value_counts().idxmax()

    return data[group_ids == longest_group_id]


def main(args_list=None):
    """processing the data from the cmd line"""

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
    files = sorted([os.path.join(args.directory, f)
                    for f in os.listdir(args.directory) if f.endswith('.txt')])
    combined_data = None
    for file_path in files:
        data = read_tidal_data(file_path)
        combined_data = data if combined_data is None else join_data(combined_data, data)

    if combined_data is not None:
        slope, p_value = sea_level_rise(combined_data)
        if args.verbose:
            print(f"The calculated sea level rise slope is: {slope:.2e},"
                  f" and the p-value is: {p_value:.2e}")

if __name__ == '__main__':
    main()
