#!/usr/bin/env python3
# hyfr -- hybrid full-reference video quality model
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

from pixelmodels.train_common import (
    read_database
)
from pixelmodels.common import (
    extract_features_full_ref,
    get_repo_version,
    predict_video_score,
    MODEL_BASE_PATH
)

# this is the basepath, so for each type of model a separate file is stored
HYFR_MODEL_PATH = os.path.join(MODEL_BASE_PATH, "hyfr")


def hyfr_features():
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
        # FR features
        "ssim",
        "psnr",
        "vifp",
        "fps",
    }



def hyfr_predict_video_score(dis_video, ref_video, temp_folder="./tmp", features_temp_folder="./tmp/features", model_path=HYFR_MODEL_PATH, clipping=True):
    features, full_report = extract_features_full_ref(
        dis_video,
        ref_video,
        temp_folder=temp_folder,
        features_temp_folder=features_temp_folder,
        featurenames=hyfr_features(),
        modelname="hyfr",
        meta=True
    )
    return predict_video_score(features, model_path)


def main(_=[]):
    # argument parsing
    parser = argparse.ArgumentParser(
        description='hyfr: a hybrid full-reference video quality model',
        epilog=f"stg7 2020 {get_repo_version()}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--feature_folder", type=str, default="./features/hyfr", help="store features in a file, e.g. for training an own model")
    parser.add_argument("--temp_folder", type=str, default="./tmp/hyfr", help="temp folder for intermediate results")
    parser.add_argument("--model", type=str, default=HYFR_MODEL_PATH, help="specified pre-trained model")

    subparsers = parser.add_subparsers(
        help='sub commands',
        dest="command"
    )

    predict = subparsers.add_parser(
        'predict',
        help='predict video quality of single video',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    predict.add_argument(
        "dis_video",
        type=str,
        help="distorted video to predict video quality"
    )
    predict.add_argument(
        "ref_video",
        type=str,
        help="source video"
    )
    predict.add_argument(
        '--output_report',
        type=str,
        default=None,
        help="output report of calculated values, None uses the video name as basis"
    )

    batch = subparsers.add_parser(
        'batch',
        help='perform batch prediction of a full database',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    batch.add_argument(
        'database',
        type=str,
        help='csv file of database, e.g. per_user.csv'
    )
    batch.add_argument(
        '--cpu_count',
        type=int,
        default=multiprocessing.cpu_count() // 2,
        help='thread/cpu count'
    )
    batch.add_argument(
        '--output_report_folder',
        type=str,
        default="reports/hyfr",
        help="folder for output reports of calculated values, video name is used as basis"
    )

    a = vars(parser.parse_args())

    if a["command"] == "predict":
        if a["output_report"] is None:
            a["output_report"] = get_filename_without_extension(a["dis_video"]) + ".json"

        prediction = hyfr_predict_video_score(
            a["dis_video"],
            a["ref_video"],
            temp_folder=a["temp_folder"],
            features_temp_folder=a["feature_folder"],
            model_path=a["model"],
            clipping=True
        )
        jprint(prediction)
        jdump_file(a["output_report"], prediction)

    if a["command"] == "batch":
        lInfo("batch prediction")
        videos = [[x["video"], x["src_video"]] for x in read_database(a["database"], full_ref=True)]
        results = run_parallel(
            items=videos,
            function=hyfr_predict_video_score,
            arguments=[a["temp_folder"], a["feature_folder"], a["model"], True],
            num_cpus=a["cpu_count"],
            multi_item=True
        )
        os.makedirs(a["output_report_folder"], exist_ok=True)
        for i, result in enumerate(results):
            dn = os.path.normpath(os.path.dirname(videos[i][0])).replace(os.sep, "_")
            report_filename = dn + get_filename_without_extension(videos[i][0]) + ".json"
            jdump_file(
                os.path.join(a["output_report_folder"], report_filename),
                result
            )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
