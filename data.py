import math
import numpy as np
import pandas as pd
from scipy import interpolate


class ViconData(object):

    def __init__(self, path):
        self.path = path
        col_names = [n for n in range(500)]
        self.doc = pd.read_csv(path, header=None, names=col_names, low_memory=False)

        self.analyse_event()
        self.joints = self.analyse_param('Joints')
        self.model_outputs = self.analyse_param('Model Outputs')

    def analyse_event(self):
        events_index = self.doc[self.doc[2] == 'Foot Strike'] \
            .index.tolist()

        self.events = []
        for n in range(0, int(len(events_index)), 2):
            self.events.append((float(self.doc.loc[events_index[n], 3]),
                                float(self.doc.loc[events_index[n + 1], 3])))

    def analyse_param(self, symbol):
        row_start = int(self.doc[self.doc[0] == symbol].index.tolist()[0]) + 5
        frame_start = int(self.doc.loc[row_start, 0])
        output_rate = int(self.doc.loc[row_start - 4, 0])

        def time2row(time):
            frame = time * output_rate
            return row_start + frame - frame_start

        def event_extract(start, end, col_name):
            data = self.doc.loc[time2row(start): time2row(end), col_name].tolist()
            return self.data_process(data)

        param_list = self.doc.loc[row_start - 3, :].tolist()
        sub_param_list = self.doc.loc[row_start - 2, :].tolist()

        try:
            gaits = [{} for n in range(len(self.events))]

            for n in range(2, len(param_list)):
                if type(param_list[n]) == str:
                    param_name = param_list[n].split(':')[1]

                    for gait in gaits:
                        gait[param_name] = {}

                if type(sub_param_list[n]) == str:
                    sub_param_name = sub_param_list[n]

                    for m in range(len(gaits)):
                        event_data = event_extract(self.events[m][0], self.events[m][1], n)
                        event_data = list(map(float, event_data))
                        gaits[m][param_name][sub_param_name] = event_data

            return gaits
        
        except:
            print("Warning: unexpected error happens when parsing {}\nPlease check data completeness".format(self.path))

    def data_process(self, data):
        return data


class ViconData_interp(ViconData):
    def __init__(self, path, point_num=100, threshold_num=500):
        self.point_num = point_num
        self.threshold_num = threshold_num
        super(ViconData_interp, self).__init__(path)

    def data_process(self, data):
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


if __name__ == "__main__":
    path = 'subjects/zhaoloon/fast speed 1.csv'
    data = ViconData_interp(path, 100, 50)
    print(data.model_outputs[0]['LAnkleAngles']['X'])
