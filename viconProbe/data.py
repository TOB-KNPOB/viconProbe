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

    Note
    ---
    `Class Attributes`
    
    self.path
        path of the exported :code:`.csv` Vicon analysis documents.
    self.doc
        :class:`pandas.DataFrame` loaded from :code:`.csv` Vicon analysis documents.
    self.attrs
        :class:`dict` of data batches. For example: ::

            self.attrs['Joints']
            self.attrs['Model Outputs']
    self.timestamps
        A list of gait timestamps stored in tuples: ::

            [(gait_1_start_time, gait_1_end_time), (gait_2_start_time, gait_2_end_time), ...]
    """
    def __init__(self, path: str, batches: list, **kwargs):
        self.path = path
        col_names = [n for n in range(500)]
        self.doc = pd.read_csv(path, header=None, names=col_names, low_memory=False)

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
        events_index = self.doc[self.doc[2] == 'Foot Strike'] \
            .index.tolist()

        self.timestamps = []
        for n in range(0, int(len(events_index)), 2):
            self.timestamps.append((float(self.doc.loc[events_index[n], 3]),
                                float(self.doc.loc[events_index[n + 1], 3])))

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
        row_start = int(self.doc[self.doc[0] == batch].index.tolist()[0]) + 5
        frame_start = int(self.doc.loc[row_start, 0])
        output_rate = int(self.doc.loc[row_start - 4, 0])

        def time2row(time: float) -> int:
            """Transform a time value to the row index in :attr:`self.doc`."""
            frame = time * output_rate
            row = int(row_start + frame - frame_start)
            if row < row_start:
                print("Invalid time value: {}".format(time))
            else:
                return row

        def gait_extract(start: int, end: int, col_name: str) -> list:
            """Extract the data of :code:`col_name` column from the :code:`start` row to the :code:`end` row."""
            data = self.doc.loc[time2row(start): time2row(end), col_name].tolist()
            return self.data_process(data)

        param_list = self.doc.loc[row_start - 3, :].tolist()
        sub_param_list = self.doc.loc[row_start - 2, :].tolist()

        try:
            gaits = [{} for n in range(len(self.timestamps))]

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
            print("Warning: unexpected error happens when parsing {}\nPlease check data completeness".format(self.path))

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
        super(ViconData_interp, self).__init__(**kwargs)

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
            print('{} has been loaded'.format(file))

    return subjects