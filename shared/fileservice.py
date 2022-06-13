import os
import sys
import time
import logging

import orjson as oj
import pandas as pd
import numpy as np

from .file_utils import open_file
from .run_utils import organize_run_data

archive_path = os.getenv("VISITRI_IMPORT_ARCHIVE_PATH", r"C:\applications\Visitri\\")


def load_data_file(operation_uuid, machine, control_label):
    logger = logging.getLogger("__main__")
    relative_path = str(machine) + "\\" + operation_uuid + "\\" + control_label + ".json"
    source_absolute_path = os.path.join(archive_path, relative_path)
    logger.info("Opening file for:" + str(machine) + "\\" + operation_uuid + "\\" + control_label)
    try:
        if os.path.isfile(source_absolute_path + ".zip"):
            data = open_file(source_absolute_path + ".zip", ".zip")
        elif os.path.isfile(source_absolute_path + ".xz"):
            data = open_file(source_absolute_path + ".xz", ".xz")
        else:
            data = None
            logger.error("File not found")
    except Exception:
        datadict = {}
        logger.error("Not able to open file")
    else:
        if data is not None:
            datadict = oj.loads(data)
        else:
            datadict = {}

    return datadict


def get_measures(operation_uuid, machine, control_label):
    datadict = load_data_file(operation_uuid, machine, control_label)
    measure_df = None
    runs = []

    if len(datadict) == 0 or "Run" not in datadict:
        return measure_df, runs, None

    run_list = datadict["Run"]
    run_data = organize_run_data(run_list)

    if len(run_data) == 0:
        return measure_df, runs, None

    for index, current_run in enumerate(run_data):
        spec_df = None
        time_cycle_stop = None
        time_cycle_start = None

        if "Time_Cycle_Start" in current_run:
            time_cycle_start = current_run["Time_Cycle_Start"]

        if "Time_Cycle_Stop" in current_run:
            time_cycle_stop = current_run["Time_Cycle_Stop"]

        if "CtrlHeader" in current_run:

            if "FeatureSpc" in current_run["CtrlHeader"]:
                spec_df = pd.DataFrame(current_run["CtrlHeader"]["FeatureSpc"]).pivot(index="Name",
                                                                                      columns="Property",
                                                                                      values="Value")
        column_multiindex = get_column_index(current_run)

        if "Data" in current_run:
            run_measure_df = pd.DataFrame(current_run["Data"], columns=column_multiindex)
            run = {"TimeCycleStart": time_cycle_start,
                   "TimeCycleStop": time_cycle_stop,
                   "FirstIndex": current_run["Data"][0][0],
                   "Specs": spec_df}
        else:
            run_measure_df = pd.DataFrame(columns=column_multiindex)
            run = {"TimeCycleStart": time_cycle_start,
                   "TimeCycleStop": time_cycle_stop,
                   "Specs": spec_df}

        runs.append(run)
        if measure_df is None:
            measure_df = run_measure_df
        else:
            measure_df = measure_df.append(run_measure_df, ignore_index=True)

    for column in measure_df.columns.levels[0]:
        if column == 'Rank' or column == 'Status':
            continue

        measure_df.loc[(measure_df[(column, "Feature_Status")] == 2) |
                       (measure_df[(column, "Feature_Status")] == 3),
                       (column, "Feature_Value")] = np.nan

    return measure_df, runs, datadict["UUID"]


def get_column_index(run):
    if "CtrlHeader" in run:
        header = run["CtrlHeader"]
    elif "GamHeader" in run:
        header = run["GamHeader"]
    else:
        header = None
    feature_labels = header['Data_Labels'][1:]
    types = header['Data_Types'][1:]
    column_tuples = [("Rank", "Rank")]

    for index, label in enumerate(feature_labels):
        column_tuples.append((label, types[index]))

    column_multiindex = pd.MultiIndex.from_tuples(column_tuples)
    return column_multiindex
