#!/usr/bin/env python3
# hyfu -- hybrid no-reference video quality model
import argparse
import sys
import os
import multiprocessing

from quat.log import *
from quat.utils.system import *
from quat.utils.fileutils import *
from quat.unsorted import *
from quat.parallel import *
from quat.ml.mlcore import *

from quat.unsorted import jdump_file
from pixelmodels.common import (
    extract_features_no_ref,
    get_repo_version,
    predict_video_score,
    MODEL_BASE_PATH
)

# this is the basepath, so for each type of model a separate file is stored
HYFU_MODEL_PATH = os.path.join(MODEL_BASE_PATH, "hyfu")


def hyfu_features():
    return {
        "contrast",
        "fft",
        "blur",
        "color_fulness",
        "saturation",
        "tone",
        "scene_cuts",
        "movement",
        "temporal",
        "si",
        "ti",
        "blkmotion",
        "cubrow.0",
        "cubcol.0",
        "cubrow.1.0",
        "cubcol.1.0",
        "cubrow.0.3",
        "cubcol.0.3",
        "cubrow.0.6",
        "cubcol.0.6",
        "cubrow.0.5",
        "cubcol.0.5",
        "staticness",
        "uhdhdsim",
        "blockiness",
        "noise",
        # not sure about the following features
        #"niqe",
        #"ceiq",
        #"brisque",
        #"strred"
    }



def hyfu_predict_video_score(video, temp_folder="./tmp", features_temp_folder="./tmp/features", clipping=True):
    features, full_report = extract_features_no_ref(
        video,
        temp_folder=temp_folder,
        features_temp_folder=features_temp_folder,
        featurenames=hyfu_features(),
        modelname="hyfu"
    )
    return predict_video_score(features, HYFU_MODEL_PATH)


def main(_=[]):
    # argument parsing
    parser = argparse.ArgumentParser(description='hyfu: a hybrid no-reference video quality model',
                                     epilog=f"stg7 2020 {get_repo_version()}",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("video", type=str, help="video to predict video quality")
    parser.add_argument("--feature_folder", type=str, default="./features/hyfu", help="store features in a file, e.g. for training an own model")
    parser.add_argument("--temp_folder", type=str, default="./tmp/hyfu", help="temp folder for intermediate results")
    parser.add_argument("--model", type=str, default=HYFU_MODEL_PATH, help="specified pre-trained model")
    parser.add_argument('--output_report', type=str, default=None, help="output report of calculated values, None uses the video name as basis")
    parser.add_argument('--cpu_count', type=int, default=multiprocessing.cpu_count() // 2, help='thread/cpu count')

    a = vars(parser.parse_args())
    if a["output_report"] is None:
        a["output_report"] = get_filename_without_extension(a["video"]) + ".json"

    prediction = hyfu_predict_video_score(
        a["video"],
        temp_folder=a["temp_folder"],
        features_temp_folder=a["feature_folder"],
        clipping=True
    )
    jprint(prediction)
    jdump_file(a["output_report"], prediction)



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))