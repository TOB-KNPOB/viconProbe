# include parent folder to python path
from inspect import getsourcefile
import os.path
import sys

current_path = os.path.abspath(getsourcefile(lambda:0))
current_dir = os.path.dirname(current_path)
parent_dir = current_dir[:current_dir.rfind(os.path.sep)]
sys.path.insert(0, parent_dir)

# import the module
from viconProbe import data, export

# parameters of interest
params_model_outputs = [
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

# load subjects data and export the assembled parameters
subjects = data.load(
    folder='viconProbe/subjects', 
    batches=['Model Outputs'], 
    vicon_data_class=data.ViconData_interp, 
    point_num=100,
    threshold_num=50
)

export.export_gait_attrs(
    subjects=subjects,
    batch='Model Outputs', 
    params=params_model_outputs,
    export_folder='viconProbe/outputs',
)