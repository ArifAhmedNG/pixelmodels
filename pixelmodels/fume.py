#!/usr/bin/env python3
# fume -- full-reference video quality model
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
FUME_MODEL_PATH = os.path.join(MODEL_BASE_PATH, "fume")


def fume_features():
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
        #"compressibility", --> no improvements
    }


def fume_predict_video_score(dis_video, ref_video, temp_folder="./tmp", features_temp_folder="./tmp/features", model_path=FUME_MODEL_PATH, clipping=True):
    features, full_report = extract_features_full_ref(
        dis_video,
        ref_video,
        temp_folder=temp_folder,
        features_temp_folder=features_temp_folder,
        featurenames=fume_features(),
        modelname="train_fume"
    )
    return predict_video_score(features, model_path)


def main(_=[]):
    # argument parsing
    parser = argparse.ArgumentParser(
        description='fume: a full-reference video quality model',
        epilog=f"stg7 2020 {get_repo_version()}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--feature_folder", type=str, default="./features/fume", help="store features in a file, e.g. for training an own model")
    parser.add_argument("--temp_folder", type=str, default="./tmp/fume", help="temp folder for intermediate results")
    parser.add_argument("--model", type=str, default=FUME_MODEL_PATH, help="specified pre-trained model")

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
        default="reports/fume",
        help="folder for output reports of calculated values, video name is used as basis"
    )

    a = vars(parser.parse_args())

    if a["command"] == "predict":
        if a["output_report"] is None:
            a["output_report"] = get_filename_without_extension(a["dis_video"]) + ".json"

        prediction = fume_predict_video_score(
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
            function=fume_predict_video_score,
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


'''
from math import ceil
import csv
import pandas as pd

from sklearn.ensemble import RandomForestClassifier

if __name__ == "__main__":
    features_1000 = pd.read_csv("/home/arif7/VisualDub_Evaluation/pixelmodels/pixelmodels/models/fume_1000/features.csv")

    mos_data = 2*features_1000['mos']
    filtered_feature_data = features_1000.drop(columns=['src_video', 'mos', 'mos_class', 'rating_dist'])

    print(mos_data.shape)
    print(mos_data)
    print(filtered_feature_data.shape)

    X = filtered_feature_data.to_numpy().tolist()
    Y = mos_data.to_numpy().tolist()

    clf = RandomForestClassifier(max_depth=10, random_state=0, n_estimators=300)

    clf.fit(X, Y)

    print("F1 score: ", f1_score(Y, clf.predict(X), average='macro'))
    joblib.dump(clf, 'random_forest_fume_may31.joblib')

    #print(filtered_feature_data[filtered_feature_data['src_video'] == '/home/arif7/VisualDub_Evaluation/pixelmodels/data/1000_videos/src_videos/IA_H_17.mp4'])
    #print(filtered_feature_data.to_numpy().tolist()[:5])
    
    #dis_video = "/home/arif7/VisualDub_Evaluation/pixelmodels/data/1000_videos/segments/Bob_H_1_stage2_lower_half_fume.mp4"
    #ref_video = "/home/arif7/VisualDub_Evaluation/pixelmodels/data/1000_videos/src_videos/Bob_H_1.mp4"
    csv_path = "/home/arif7/VisualDub_Evaluation/NAS_videos_metrics.csv"
    orig = []

    with open(csv_path) as f:
        reader = csv.reader(f)
        orig = list(reader)

    features_temp_folder = "/home/arif7/VisualDub_Evaluation/pixelmodels/features/train_fume"
    model_path = "/home/arif7/VisualDub_Evaluation/pixelmodels/pixelmodels/models/fume_1000"

    count = 0
    for i, metrics_data in enumerate(orig):
        if i <= 1:
            continue

        try:
            video_name = metrics_data[0]

            stage1_video = "/home/arif7/VisualDub_Evaluation/pixelmodels/data/NAS_videos/segments/{}_stage1_lower_half_fume.mp4".format(video_name)
            stage2_video = "/home/arif7/VisualDub_Evaluation/pixelmodels/data/NAS_videos/segments/{}_stage2_lower_half_fume.mp4".format(video_name)
            ref_video = "/home/arif7/VisualDub_Evaluation/pixelmodels/data/NAS_videos/src_videos/{}.mp4".format(video_name)

            s1_fume_score = fume_predict_video_score(stage1_video, ref_video, temp_folder="./train_fume", features_temp_folder=features_temp_folder, model_path=model_path, clipping=True)
            s2_fume_score = fume_predict_video_score(stage2_video, ref_video, temp_folder="./train_fume", features_temp_folder=features_temp_folder, model_path=model_path, clipping=True)

            orig[i][13] = str(int(s1_fume_score['mos']))
            orig[i][33] = str(int(s2_fume_score['mos']))

            print("===================================================================================")
            print("===================================================================================")
            print("===================================================================================")
            print("----------------------------<<<", video_name, s1_fume_score['mos'], s2_fume_score['mos'], ">>>---------------------------------")
            print("===================================================================================")
            print("===================================================================================")
            print("===================================================================================")
            count += 1
            #if count == 2:
            #    break
        except:
            pass
        with open("NAS_videos_metrics_trained_fume.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(orig)

    #print(fume_predict_video_score(dis_video, ref_video, temp_folder="./train_fume", features_temp_folder=features_temp_folder, model_path=model_path, clipping=True))
    #sys.exit(main(sys.argv[1:]))
'''