"""Module for analysing tidal data"""
import datetime
import argparse
import os
import pytz
import pandas as pd
import numpy as np
import matplotlib.dates as mdates
from scipy import stats
import uptide

def read_tidal_data(filename):
    """reads the data and turns it into a useable format """
    #skip the stuff at the top combine date and time
    tide_data = pd.read_csv(filename, skiprows=11, sep=r'\s+', header=None)
    tide_data['Time'] = pd.to_datetime(tide_data[1] + ' ' + tide_data[2])

    #setup and clean sea level, T flags are still valid data
    sea_level_col = tide_data[3].astype(str)
    clean_sea_level = sea_level_col.str.replace('T', '', case = False)
    tide_data['Sea Level'] = pd.to_numeric(clean_sea_level, errors = 'coerce')
    tide_data.loc[tide_data['Sea Level'].abs() > 20, 'Sea Level'] = np.nan

    tide_data.set_index('Time', inplace=True)
    tide_data['Time'] = tide_data.index

    return tide_data[['Sea Level', 'Time']]

def extract_single_year_remove_mean(year, data):
    """groups data from single year to calculate a yearly average"""
    #defining the time range
    year_data = data.loc[str(year)].copy()
    year_data['Sea Level'] -= year_data['Sea Level'].mean()

    return year_data

def extract_section_remove_mean(start, end, data):
    """calculates the actual height of each wave without sea level """
    section = data.loc[start:end].copy()

    #subtract mean from every value in section
    mean_value = section['Sea Level'].mean(skipna=True)
    section['Sea Level'] = section['Sea Level'] - mean_value

    return section

def join_data(data1, data2):
    """combines data to allow for easier analysis"""
    combined = pd.concat([data1, data2])

    return combined.sort_index()

def sea_level_rise(data):
    """calculates the sea level rise from year to year"""
    #clean data of NaN
    daily_data = data.dropna(subset=['Sea Level'])

    #variables and regression
    datetime_of_sea_level = mdates.date2num(daily_data.index)
    sea_level = daily_data['Sea Level'].values
    slope_per_day, _, _, p_value, _ = stats.linregress(datetime_of_sea_level, sea_level)

    return slope_per_day, p_value

def tidal_analysis(data, constituents, start_datetime):
    """harmonic analysis on sea level data using specific consituents"""
    #activate uptide to allow for calculations
    tide = uptide.Tides(constituents)
    tide.set_initial_time(start_datetime)

    #clean data of NaN
    clean_data = data.dropna(subset=['Sea Level']).copy()

    levels = clean_data['Sea Level'].values
    levels = levels - np.mean(levels)

    #check that time is set to utc, not really needed
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

    # nodal corrections
    f_factors = np.array([1.0, 1.305])

    return amp * f_factors, pha

def get_longest_contiguous_data(data):
    """finds longest time with continous data"""
    #calculate difference between rows
    time_diffs = data.index.to_series().diff()

    #identify gaps and grouo them
    freq = time_diffs.mode()[0]
    gaps = time_diffs > freq
    gaps.iloc[0] = False
    group_ids = gaps.cumsum()

    longest_group_id = group_ids.value_counts().idxmax()

    return data[group_ids == longest_group_id]

def tidal_height_prediction(constituents, amp, pha, start_datetime, days_to_predict=7):
    """predicts future sea level based on current data"""
    tide = uptide.Tides(constituents)
    tide.set_initial_time(start_datetime)

    #hourly prediction points
    hours = np.arange(0, days_to_predict * 24)
    seconds = hours * 3600

    predicted_heights = np.zeros(len(seconds))
    for i, con_name in enumerate(constituents):
        con = tide.constituents[con_name] #pylint: disable=no-member
        phase_rad = np.radians(pha[i])
        predicted_heights += amp[i] * np.cos(con.speed * seconds +phase_rad)

    future_dates = [start_datetime + datetime.timedelta(hours=int(h)) for h in hours]

    return future_dates, predicted_heights

def run_prediction_mode(args, combined_data):
    """Helper to handle the prediction and reduce variables on main"""
    consts = ['M2', 'S2']
    raw_start = combined_data.index[-1]
    start_time = raw_start.to_pydatetime() if hasattr(raw_start, 'to_pydatetime') else raw_start

    print(f"\nGenerating {args.predict}-day prediction starting from {start_time}...")

    amp, pha = tidal_analysis(combined_data, consts, start_time)
    dates, heights = tidal_height_prediction(consts, amp, pha, start_time, args.predict)

    print(f"{'Time':<20} | {'Height (m)':<12}")
    print("-" * 35)
    for d, h in zip(dates[:10], heights[:10]):
        print(f"{d.strftime('%Y-%m-%d %H:%M'):<20} | {h:+.3f}")

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
    parser.add_argument('-p', '--predict',
                        type=int,
                        metavar='DAYS',
                        help="predict the tide for a set number of days")

    args = parser.parse_args(args_list)
    files = sorted([os.path.join(args.directory, f)
                    for f in os.listdir(args.directory) if f.endswith('.txt')])
    combined_data = None
    for file_path in files:
        data = read_tidal_data(file_path)
        combined_data = data if combined_data is None else join_data(combined_data, data)

    if combined_data is not None:
        slope, p_value = sea_level_rise(combined_data)
        rise_mm_year = slope * 365.25 * 1000
        now = datetime.datetime.now()

        if args.verbose:
            print(f"Analysis run at: {now}")
            print(f"The calculated sea level rise is: {rise_mm_year:.2f}mm per year.")
            print(f"The p-value is: {p_value:.2e}")

        if args.predict:
            run_prediction_mode(args, combined_data)

if __name__ == '__main__':
    main()
