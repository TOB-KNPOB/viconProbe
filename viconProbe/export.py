from __future__ import annotations
from typing import Type, Union, Iterable

import xlwt

from viconProbe import data

class XlsBlock(object):
    """Advance block container for :code:`.xls` file writing. It allows a block to contain other blocks as its contents, and the layer of containing relationship is unlimited. In :meth:`render`, the exact writing position of each block is determined.
    
    Parameters
    ---
    worksheet
        the :mod:`xlwt` worksheet to be write.
    head
        the head title of the block.
    mode
        the direction of content layout: :code:`right` / :code:`down`.

    Note
    ---
    `Class Attributes`

    self.worksheet
        :class:`xlwt.Worksheet.Worksheet` the :mod:`xlwt` worksheet to be write.
    self.head
        :class:`str` the head title of the block.
    self.contents
        :class:`list` a list of :class:`XlsBlock` as the block's content, or a list of data.
    self.mode
        :class:`str` the direction of content layout: :code:`right` / :code:`down`.
    self.row
        :class:`int` current writing row.
    self.row_start
        :class:`int` starting row of the block. Updated during :meth:`render`.
    self.row_end
        :class:`int` ending row of the block. Updated during :meth:`render`.
    self.col
        :class:`int` current writing column.
    self.col_start
        :class:`int` starting column of the block. Updated during :meth:`render`.
    self.col_end
        :class:`int` ending column of the block. Updated during :meth:`render`.
    """
    def __init__(self, worksheet: xlwt.Worksheet.Worksheet, head: str, mode: str = 'right'):
        self.worksheet = worksheet
        self.head = head
        self.contents = []
        self.mode = mode

    def move(self, row_add: int, col_add: int):
        """Move current writing location by :code:`row_add` and :code:`col_add`."""
        self.row += row_add
        self.col += col_add
        self.update(self.row, self.col)

    def move_to(self, row_new: int, col_new: int):
        """Move current writing location to :code:`row_add` and :code:`col_add`."""
        self.row = row_new
        self.col = col_new
        self.update(self.row, self.col)

    def update(self, row_new: int, col_new: int):
        """When current writing location is changed, update the :attr:`row_start`, :attr:`row_end`, :attr:`col_start`, and :attr:`col_end`.

        Parameters
        ---
        row_new
            current writing row.
        col_new
            current writing column.
        
        Attention
        ---
        After rendering a content `(children)` block, its ending row and column is deem the current writing location of the father block. Therefore :meth:`update` is also necessary."""
        if row_new > self.row_end:
            self.row_end = row_new

        if col_new > self.col_end:
            self.col_end = col_new

        if row_new < self.row_start:
            self.row_start = row_new

        if col_new < self.col_start:
            self.col_start = col_new

    def render(self, row: int, col: int):
        """Recursively render the block and its content to the :code:`.xls` file.
        
        Parameters
        ---
        row
            starting row of the block.
        col
            beginning column of the block.
        """
        self.row, self.row_start, self.row_end = row, row, row
        self.col, self.col_start, self.col_end = col, col, col

        self.worksheet.write(self.row_start, self.col_start, self.head)
        self.move(1, 0)

        for content in self.contents:
            if type(content) == XlsBlock:
                content.render(self.row, self.col)

                self.update(content.row_start, content.col_start)
                self.update(content.row_end, content.col_end)

                if self.mode == 'right':
                    self.move_to(self.row_start + 1, self.col_end + 1)

                elif self.mode == 'down':
                    self.move_to(self.row_end, self.col_start)

            else:
                for data in content:
                    self.worksheet.write(self.row, self.col, data)
                    self.move(1, 0)


def export_gait_attrs(subjects: dict, batch: str, params: list, export_folder: str = 'outputs'):
    """Export the gait parameters data to :code:`.xls` files.

    - Every subject export a :code:`.xls` file.
    - Every parameter stores in a sheet of the :code:`.xls` file.
    - In every sheet, data is arranged in the form of:

    .. list-table:: Data Sheet Format
       :header-rows: 1
    
       * - Subject A
         - 
         - 
         - 
       * - Parameter 1
         - 
         - 
         - 
       * - Gait 1 data
         - Gait 2 data
         - Gait 3 data
         - \.\.\.
       * - Parameter 2
         - 
         - 
         - 
       * - Gait 1 data
         - Gait 2 data
         - Gait 3 data
         - \.\.\.
       * - \.\.\.
         - \.\.\.
         - \.\.\.
         - \.\.\.

    Parameters
    ---
    subjects
        dictionary of all subjects data arranged in the form of: :code:`return_val[subject_name][condition]`. Provided by :func:`viconProbe.data.load`.
    batch
        name of the data batch to be exported, e.g. :code:`'Joints'`, :code:`'Module Outputs'`, etc.
    params
        a list of selected parameter list. For example: ::

            # selected parameters of Joints batch
            params = [
                'Head_Head_End',
                'L_Collar_L_Humerus',
                'L_Elbow_L_Wrist',
                'L_Femur_L_Tibia',
                'L_Foot_L_Toe',
                'L_Humerus_L_Elbow',
                'L_Tibia_L_Foot',
                'L_Wrist_L_Wrist_End',
                'LowerBack_Head',
                'LowerBack_L_Collar',
                'LowerBack_R_Collar',
                'R_Collar_R_Humerus',
                'R_Elbow_R_Wrist',
                'R_Femur_R_Tibia',
                'R_Foot_R_Toe',
                'R_Humerus_R_Elbow',
                'R_Tibia_R_Foot',
                'R_Wrist_R_Wrist_End',
                'Root_L_Femur',
                'Root_LowerBack',
                'Root_R_Femur',
                'World_Root',
            ]

        ::

            # selected parameters of Module Outputs batch
            params = [
                'CentreOfMass',
                'LAnkleAngles',
                'LAnkleForce',
                'LAnkleMoment',
                'LAnklePower',
                'LFootProgressAngles',
                'LGroundReactionForce',
                'LGroundReactionMoment',
                'LHipAngles',
                'LHipForce',
                'LHipMoment',
                'LHipPower',
                'LKneeAngles',
                'LKneeForce',
                'LKneeMoment',
                'LKneePower',
                'LNormalisedGRF',
                'LPelvisAngles',
                'RAnkleAngles',
                'RAnkleForce',
                'RAnkleMoment',
                'RAnklePower',
                'RFootProgressAngles',
                'RGroundReactionForce',
                'RGroundReactionMoment',
                'RHipAngles',
                'RHipForce',
                'RHipMoment',
                'RHipPower',
                'RKneeAngles',
                'RKneeForce',
                'RKneeMoment',
                'RKneePower',
                'RNormalisedGRF',
                'RPelvisAngles',
            ]

    export_folder
        the export folder.

        Note
        ---
        The exported file is named and stored as :code:`<export_folder>/<batch_name>.xls`.
    """
    for name in subjects:
        workbook = xlwt.Workbook(encoding='ascii')

        for param in params:
            worksheet = workbook.add_sheet(param, cell_overwrite_ok=True)

            param_batch = XlsBlock(worksheet, param)
            subject_batch = XlsBlock(worksheet, name)
            subject_batch.mode = 'down'
            param_batch.contents.append(subject_batch)

            for condition in subjects[name]:
                condition_batch = XlsBlock(worksheet, condition)
                subject_batch.contents.append(condition_batch)
                data = subjects[name][condition].attrs[batch]

                for gait_num in range(len(data)):
                    gait_batch = XlsBlock(worksheet, 'Gait ' + str(gait_num))
                    condition_batch.contents.append(gait_batch)

                    if param not in data[gait_num].keys():
                        print("Warning: {} - {} - {} not found".format(name, condition, param))

                    else:
                        for sub_param in data[gait_num][param]:
                            sub_param_batch = XlsBlock(worksheet, sub_param)
                            gait_batch.contents.append(sub_param_batch)
                            sub_param_batch.contents.append(data[gait_num][param][sub_param])

            param_batch.render(0, 0)

        save_file = "{}/{} - {}.xls".format(export_folder, name, batch)
        workbook.save(save_file)
        print('/{} has been outputed'.format(save_file))