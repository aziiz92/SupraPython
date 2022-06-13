from collections import Counter
import pandas as pd

def organize_run_data(run_list):
    # take the run data from the json and reshape it
    new_run_list = []
    this_run_dict = {}
    this_run_data = []

    for item in run_list:

        if "Time_Cycle_Start" in item:
            # we copy the data to the run dictionary
            if len(this_run_data) > 0:
                this_run_dict["Data"] = this_run_data
            if this_run_dict:
                new_run_list.append(this_run_dict)
            this_run_data = []
            this_run_dict = item

        if "CtrlHeader" in item:
            this_run_dict["CtrlHeader"] = item["CtrlHeader"]

        if "Data" in item:
            this_run_data.extend(item["Data"])

        if "Time_Cycle_Stop" in item:
            this_run_dict["Time_Cycle_Stop"] = item["Time_Cycle_Stop"]

    if len(this_run_data) > 0:
        this_run_dict["Data"] = this_run_data
    if this_run_dict:
        new_run_list.append(this_run_dict)

    new_run_list = compress_run_headers(new_run_list)

    return new_run_list


def compress_run_headers(run_list):
    # we take a run list and we remove from the headers the data that doesn't change from run to run
    # For controls, we compress the CtrlSpc and FeatureSpc arrays
    # "CtrlSpc":
    # [
    #     {"PixelSize_Type": 1},
    #     {"PixelSize": 0.011000}
    # ],
    # "FeatureSpc":
    # [
    #     {"Name": "Disp_Global", "Property": "Max Value", "Value": 1.000000},
    #     {"Name": "Disp_Global", "Property": "Min Value", "Value": 0.000000},
    #     {"Name": "Disp_Global", "Property": "Max Value CtrlEtln", "Value": 1.000000},
    #     {"Name": "Disp_Global", "Property": "Min Value CtrlEtln", "Value": 0.000000},
    #     {"Name": "Disp_Id", "Property": "Max Value", "Value": 0.060000},
    #     {"Name": "Disp_Id", "Property": "Min Value", "Value": 0.000000},
    #     {"Name": "Disp_Id", "Property": "Max Value CtrlEtln", "Value": 0.060000},
    #     {"Name": "Disp_Id", "Property": "Min Value CtrlEtln", "Value": 0.000000},
    #     {"Name": "Disp_OppId", "Property": "Max Value", "Value": 0.200000},
    #     {"Name": "Disp_OppId", "Property": "Min Value", "Value": 0.000000},
    #     {"Name": "Disp_OppId", "Property": "Max Value CtrlEtln", "Value": 0.200000},
    #     {"Name": "Disp_OppId", "Property": "Min Value CtrlEtln", "Value": 0.000000}
    # ],

    # For inspection plans, we compress Ctrl_List arrays
    # "Ctrl_List": ["D1C1-S1 r_pce", "D1C1-S1 m_pce", "D1C1-S1 Stat_Endroit", "D1C1-S1 abs Pce D", "D1C1-S1 abs Pce G"],

    current_ctrl_spc = pd.DataFrame()
    current_feature_spc = pd.DataFrame()
    current_ctrl_list = []

    new_run_list = []

    for run in run_list:

        if "GamHeader" in run:
            if "Ctrl_List" in run["GamHeader"]:
                if len(current_ctrl_list)>0:
                    new_Ctrl_List = run["GamHeader"]["Ctrl_List"]
                    if Counter(run["GamHeader"]["Ctrl_List"]) == Counter(current_ctrl_list):
                        run["GamHeader"].pop("Ctrl_List")
                    current_ctrl_list = new_Ctrl_List
                else:
                    current_ctrl_list = run["GamHeader"]["Ctrl_List"]

        if "CtrlHeader" in run:

            if "CtrlSpc" in run["CtrlHeader"]:
                if len(current_ctrl_spc) > 0:
                    new_compressed_list, new_df = keep_different_records(run["CtrlHeader"]["CtrlSpc"],
                                                                         current_ctrl_spc)
                    if len(new_compressed_list) > 0:
                        run["CtrlHeader"]["CtrlSpc"] = new_compressed_list
                    else:
                        run["CtrlHeader"].pop("CtrlSpc")
                    current_ctrl_spc = new_df
                else:
                    current_ctrl_spc = pd.DataFrame(run["CtrlHeader"]["CtrlSpc"])
            if "FeatureSpc" in run["CtrlHeader"]:
                if len(current_feature_spc) > 0:
                    new_compressed_list, new_df = keep_different_records(run["CtrlHeader"]["FeatureSpc"],
                                                                         current_feature_spc)
                    if len(new_compressed_list) > 0:
                        run["CtrlHeader"]["FeatureSpc"] = new_compressed_list
                    else:
                        run["CtrlHeader"].pop("FeatureSpc")
                    current_feature_spc = new_df
                else:
                    current_feature_spc = pd.DataFrame(run["CtrlHeader"]["FeatureSpc"])

        new_run_list.append(run)

    return new_run_list


def keep_different_records(new_list, old_df):
    new_df = pd.DataFrame(new_list)

    merged_df = old_df.merge(new_df, indicator = True, how="outer").loc[lambda x : x['_merge']=='right_only']
    merged_df = merged_df.drop(columns=['_merge'])
    new_compressed_list = merged_df.to_dict('records')
    return new_compressed_list, new_df