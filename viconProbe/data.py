from __future__ import annotations
from typing import Type, Union, Iterable

import os
import re
import math
import numpy as np
import pandas as pd
from scipy import interpolate

class ViconData(object):
    """The basic Vicon data class.
    
    Parameters
    ---
    path
        :class:`str` path of the exported :code:`.csv` Vicon analysis documents.
    batches
        :class:`list` a list of the data batches to be loaded. For example: ::

            batches = ['Joints', 'Model Outputs']
    max_col
        the number of columns to be loaded.

        Warning
        ---
        Since different data batches in the :code:`.csv` files exported from Vicon have different column numbers, the number of columns to be loaded needs to be manually set. :attr:`max_col` is set as :code:`500` in default and needs to be carefully revised if necessary.

    Note
    ---
    `Class Attributes`
    
    self.path
        path of the exported :code:`.csv` Vicon analysis documents.
    self.df
        :class:`pandas.DataFrame` loaded from :code:`.csv` Vicon analysis documents.
    self.attrs
        :class:`dict` of data batches. For example: ::

            self.attrs['Joints']
            self.attrs['Model Outputs']
    self.timestamps
        A list of gait timestamps stored in tuples: ::

            [(gait_1_start_time, gait_1_end_time), (gait_2_start_time, gait_2_end_time), ...]
    """
    def __init__(self, path: str, batches: list, max_col: int = 500, **kwargs):
        self.path = path

        # inactivate low_memory due to mixture data type
        try:
            self.df = pd.read_csv(
                self.path, 
                names=[n for n in range(max_col)],
                low_memory=False
            )
        
        # sometimes it raise issue, in this case activate low_memory
        except:
            self.df = pd.read_csv(
                self.path, 
                names=[n for n in range(max_col)],
                low_memory=True
            )

        self.gait_retrieve()
        self.attrs = {}

        for batch in batches:
            self.attrs[batch] = self.batch_retrieve(batch)

    def gait_retrieve(self):
        """Retrieve the gait timestamp to :attr:`self.gaites` in the format of :code:`[(gait_1_start_time, gait_1_end_time), (gait_2_start_time, gait_2_end_time), ...]`.
        
        Attention
        ---
        Every pair of :code:`Foot Strike` is deemed the start and end of a gait, regardless of what is before, after, and inserted between them.
        """
        events_indexes = df_match_indexes(self.df, 'Foot Strike')
        events_rows = events_indexes[0]
        events_cols = events_indexes[1]

        self.timestamps = []
        for n in range(0, int(len(events_rows)), 2):
            self.timestamps.append((
                float(self.df.loc[events_rows[n], events_cols[n] + 1]),
                float(self.df.loc[events_rows[n + 1], events_cols[n] + 1]),
            ))

    def batch_retrieve(self, batch: str) -> list:
        """Retrieve all parameters that belongs to different gaits from a batch of data.
        
        Parameters
        ---
        batch
            the name of the batch of data to be retrieved.
        
        Returns
        ---
        :class:`list`
            a list of dictionary, each stores the parameters that belongs to a gait, with the same order of :code:`self.timestamps`. In summary, to retrieve a piece of data: ::
            
                return_var[gait_idx][param_name][sub_param_name]
        """
        row_start = df_first_match_row(self.df, batch) + 5
        frame_start = int(self.df.loc[row_start, 0])
        output_rate = int(self.df.loc[row_start - 4, 0])

        def time2row(time: float) -> int:
            """Transform a time value to the row index in :attr:`self.df`."""
            frame = time * output_rate
            row = int(row_start + frame - frame_start)
            if row < row_start:
                print("Invalid time value: {}".format(time))
            else:
                return row

        def gait_extract(start: int, end: int, col_name: str) -> list:
            """Extract the data of :code:`col_name` column from the :code:`start` row to the :code:`end` row."""
            data = self.df.loc[time2row(start): time2row(end), col_name].tolist()
            return self.data_process(data)

        param_list = self.df.loc[row_start - 3, :].tolist()
        sub_param_list = self.df.loc[row_start - 2, :].tolist()

        gaits = [{} for n in range(len(self.timestamps))]

        try:
            for n in range(2, len(param_list)):
                if type(param_list[n]) == str:
                    param_name = param_list[n].split(':')[1]

                    for gait in gaits:
                        gait[param_name] = {}

                if type(sub_param_list[n]) == str:
                    sub_param_name = sub_param_list[n]

                    for m in range(len(gaits)):
                        event_data = gait_extract(self.timestamps[m][0], self.timestamps[m][1], n)
                        event_data = list(map(float, event_data))
                        gaits[m][param_name][sub_param_name] = event_data

            return gaits
        
        except:
            print("Warning: unexpected error happens when parsing {}".format(self.path))

    def data_process(self, data: list) -> list:
        """Post-processing of data.

        Parameters
        ---
        data
            Input gait's parameter data.
        
        Attention
        ---
        In the basic :class:`ViconData` class, this function doesn't do anything but return the :attr:`data`."""
        return data


class ViconData_interp(ViconData):
    """Based on :class:`ViconData`, resampling all gait's parameter data to the same length via data interpretation.

    Parameters
    ---
    point_num
        resampled data length.
    threshold_num
        only resample the parameter data with valid data point number that is larger than :attr:`self.threshold_num`.
    **kwargs
    
    Note
    ---
    `Class Attributes`

    self.point_num
        `int` resampled data length.
    self.threshold_num
        `int` only resample the parameter data with valid data point number that is larger than :attr:`self.threshold_num`.
    """
    def __init__(self, point_num: int = 100, threshold_num: int = 50, **kwargs):
        self.point_num = point_num
        self.threshold_num = threshold_num
        ViconData.__init__(self, **kwargs)

    def data_process(self, data: list) -> list:
        """resample the input data to the same length.

        - Remove all :code:`NaN` in the original data.
        - If the remaining valid data points is larger than :attr:`self.threshold_num`, resample the input data to :attr:`self.threshold_num` points, via data interpretation.
        
        Parameters
        ---
        data
            Input gait's parameter data.
        """
        try:
            data_remove_nan = [d for d in data if math.isnan(float(d)) == False]
        except:
            print(data)

        if len(data_remove_nan) < self.threshold_num or len(data_remove_nan) < 2:
            return data_remove_nan
        else:
            interpolate_kind = 'slinear'

        func_interp = interpolate.interp1d(range(len(data_remove_nan)),
                                           data_remove_nan,
                                           kind=interpolate_kind)

        x_new = np.linspace(0, len(data_remove_nan) - 1, self.point_num)
        data_new = func_interp(x_new)

        return data_new


def df_match_indexes(df: pd.DataFrame, symbol: str) -> tuple:
    """Get the indexes of matched cells of a :mod:`pandas` data frame.
    
    Parameters
    ---
    df
        :mod:`pandas` data frame.
    symbol
        the string to be matched.

    Returns
    ---
    :class:`tuple`
        a tuple with lists of matched cells' row indexes and column indexes as its two elements.
    """
    indexes = np.where(df == symbol)
    return indexes

def df_first_match_index(df: pd.DataFrame, symbol: str) -> tuple:
    """Get the first matched cell's index from a :mod:`pandas` data frame.
    
    Parameters
    ---
    df
        :mod:`pandas` data frame.
    symbol
        the string to be matched.

    Returns
    ---
    :class:`tuple`
        a tuple with the first matched cell's row and column indexes.
    """
    indexes = df_match_indexes(df, symbol)
    return (indexes[0][0], indexes[1][0])


def df_first_match_row(df: pd.DataFrame, symbol: str) -> int:
    """Get the first matched cell's row index from a :mod:`pandas` data frame.
    
    Parameters
    ---
    df
        :mod:`pandas` data frame.
    symbol
        the string to be matched.

    Returns
    ---
    :class:`tuple`
        the first matched cell's row indexes.
    """
    index = df_first_match_index(df, symbol)
    return index[0]


def df_first_match_col(df: pd.DataFrame, symbol: str) -> int:
    """Get the first matched cell's column index from a :mod:`pandas` data frame.
    
    Parameters
    ---
    df
        :mod:`pandas` data frame.
    symbol
        the string to be matched.

    Returns
    ---
    :class:`tuple`
        the first matched cell's column indexes.
    """
    index = df_first_match_index(df, symbol)
    return index[1]


def load(folder: str, batches: str, vicon_data_class: Type[ViconData], **kwargs) -> list:
    """Load all :code:`.csv` Vicon analysis documents under a folder.

    Parameters
    ---
    folder
        the folder storing all :code:`.csv` Vicon analysis documents.
    batches
        :class:`list` a list of the data batches to be loaded. For example: ::

            batches = ['Joints', 'Model Outputs']
    
    vicon_data_class
        the Vicon data class to load and analysis the Vicon data.
    **kwargs
        other parameters passed in for Vicon data class initialisation.

    Returns
    ---
    :class:`dict`
        dictionary of all subjects data arranged in the form of: :code:`return_val[subject_name][condition]`.

    Attention
    ---
    At current stage, conditions like :code:`fast walking 1` and :code:`fast walking 2` are identified as two different conditions. In the future, a 'trail' level may be added to the dictionary structure, with extended node tree mechanism developed in :mod:`pedarProbe`.
    """
    folders = os.listdir(folder)
    folders.sort()
    subjects = {}

    for name in folders:  
        if '.DS_Store' in name:
                continue
        
        if name not in subjects:
                subjects[name] = {}

        files = os.listdir(os.path.join(folder, name))
        files.sort()

        for file in files:
            if '.DS_Store' in file:
                continue

            condition = re.search('[^.]*', file).group()
            filepath = os.path.join(folder, name, file)
            subjects[name][condition] = vicon_data_class(path=filepath, batches=batches, **kwargs)
            print('{}/{} has been loaded'.format(name, file))

    return subjects