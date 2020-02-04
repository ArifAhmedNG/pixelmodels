#!/usr/bin/env python3

from quat.ff.probe import ffprobe
from quat.ff.convert import (
    crop_video,
    convert_to_avpvs,
    convert_to_avpvs_and_crop
)
from quat.video import *
from quat.utils.assertions import *
from quat.visual.base_features import *
from quat.visual.image import *


def all_features():
    return {
        "contrast": ImageFeature(calc_contrast_features),
        "fft": ImageFeature(calc_fft_features),
        "blur": ImageFeature(calc_blur_features),
        "color_fulness": ImageFeature(color_fulness_features),
        "saturation": ImageFeature(calc_saturation_features),
        "tone": ImageFeature(calc_tone_features),
        "scene_cuts": CutDetectionFeatures(),
        "movement": MovementFeatures(),
        "temporal": TemporalFeatures(),
        "si": SiFeatures(),
        "ti": TiFeatures(),
        "blkmotion": BlockMotion(),
        "cubrow.0": CuboidRow(0),
        "cubcol.0": CuboidCol(0),
        "cubrow.1.0": CuboidRow(1.0),
        "cubcol.1.0": CuboidCol(1.0),
        "cubrow.0.3": CuboidRow(0.3),
        "cubcol.0.3": CuboidCol(0.3),
        "cubrow.0.6": CuboidRow(0.6),
        "cubcol.0.6": CuboidCol(0.6),
        "cubrow.0.5": CuboidRow(0.5),
        "cubcol.0.5": CuboidCol(0.5),
        "staticness": Staticness(),
        "uhdhdsim": UHDSIM2HD(),
        "blockiness": Blockiness(),
        # TODO: noise
    }


def unify_codec(x):
    if "h264" in x:
        return 0
    if "hevc" in x:
        return 1
    if "vp9" in x:
        return 2
    msg_assert(False, f"video codec{x} is not supported by this model")
    # this should never happen
    return 3


def extract_mode0_features(video):
    # use ffprobe to extract bitstream features
    meta = ffprobe(video)
    # mode0 base data
    mode0_features = {  # numbers are important here
        "framerate": float(meta["avg_frame_rate"]),
        "bitrate": float(meta["bitrate"]) / 1024,  # kbit/s
        "bitdepth": 8 if meta["bits_per_raw_sample"] == "unknown" else int(meta["bits_per_raw_sample"])
        "codec": unify_codec(meta["codec"]),
        "resolution": int(meta["height"]) * int(meta["width"]),
    }
    # mode0 extended features
    mode0_features["bpp"] = 1024 * mode0_features["bitrate"] / (mode0_features["framerate"] * mode0_features["resolution"])
    mode0_features["bitrate_log"] = np.log(mode0_features["bitrate"])
    mode0_features["framerate_norm"] = mode0_features["framerate"] / 60.0
    mode0_features["framerate_log"] = np.log(mode0_features["framerate"])
    mode0_features["resolution_log"] = np.log(mode0_features["resolution"])
    mode0_features["resolution_norm"] = mode0_features["resolution"] / (3840 * 2160)

    return mode0_features


def extract_features_no_ref(video, tmpfolder="./tmp", features_temp_folder="./tmp/features", featurenames=None, modelname="nofu", meta=False):
    msg_assert(features is not None, "features are required to be defined", f"feature set ok")
    lInfo(f"handle : {video} for {modelname}")

    all_feat = all_features()
    msg_assert(list(set(all_feat.keys()) & featurenames) > 0, "feature set empty")
    msg_assert(list(set(featurenames - all_feat.keys())) == 0, "feature set comtains features that are not defined")
    features = {}
    for featurename in featurenames:
        features[featurename] = all_feat[featurename]

    features_to_calculate = set([f for f in features.keys() if not features[f].load(features_temp_folder + "/" + modelname + "/" + f, video, f)])
    i = 0

    lInfo(f"calculate missing features {features_to_calculate} for {video}")
    if features_to_calculate != set():
        # convert to avpvs (rescale) and crop
        video_avpvs_crop = convert_to_avpvs_and_crop(video, tmpfolder + "/crop/")

        for frame in iterate_by_frame(video_avpvs_crop, convert=False):
            for f in features_to_calculate:
                x = features[f].calc(frame)
                lInfo(f"handle frame {i} of {video}: {f} -> {x}")
            i += 1
        os.remove(video_avpvs_crop)

    feature_files = []
    for f in features:
        feature_files.append(features[f].store(features_temp_folder + "/" + modelname + "/" + f, video, f))

    pooled_features = {}
    per_frame_features = {}
    for f in features:
        pooled_features = dict(advanced_pooling(features[f].get_values(), name=f), **pooled_features)
        per_frame_features = dict({f:features[f].get_values()}, **per_frame_features)

    full_features = {
        "video_name": video,
        "per_frame": per_frame_features,
    }

    # this is only used if it is a hybrid model
    if meta:
        metadata_features = extract_mode0_features(video)
        full_features["meta"] = metadata_features
        for m in metadata_features:
            pooled_features["meta_" + m] = metadata_features[m]

    return pooled_features, full_features



