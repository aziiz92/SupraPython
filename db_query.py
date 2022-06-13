#import ctds
from datetime import datetime, timedelta
import pandas as pd

import shared.model as dm
from shared.import_utils import parse_timestamp


def delete_control_run(session, control_run_id):
    record = session.query(dm.ControlRun).filter_by(id=int(control_run_id)).one()
    session.delete(record)
    session.commit()
    return True


def get_operation_records(session, operation_uuid):
    return session.query(dm.Operation). \
        filter(dm.Operation.uuid == operation_uuid). \
        all()


def get_operations_by_lot_number(session, lot_number):
    return session.query(dm.Operation). \
        filter(dm.Operation.lot == lot_number).\
        all()


def get_operations_by_router_number(session, router_number):
    return session.query(dm.Operation). \
        filter(dm.Operation.routerNumber == router_number).\
        all()


def get_operations_by_router_number_and_date(session, router_number, timestamp):
    return session.query(dm.Operation). \
        filter(dm.Operation.routerNumber == router_number). \
        filter(dm.Operation.timeProdStop <= timestamp). \
        all()


def get_operations_by_router_number_list(session, router_numbers):
    return session.query(dm.Operation). \
        filter(dm.Operation.routerNumber.in_(tuple(router_numbers))). \
        all()


def get_lots_to_generate_report(session, part_numbers):

    part_numbers_query_string = ','.join(map("''{0}''".format, part_numbers))

    query = r"""
    SELECT DISTINCT A.LBARCL AS 'CustomerPartNumber',
                    A.LBINAC AS 'CustomerRevision',
                    A.LBNLOT as 'CustomerLotNumber',
                    C.FUMNUM as 'HandlingUnitNumber'
    FROM 
    (
        SELECT LBARCL,
               LBINAC,
               RIGHT('00000000'+CAST(LBNBIN AS VARCHAR(8)),8) + RIGHT('00000'+CAST(LBNUMI AS VARCHAR(5)),5) + RIGHT('000'+CAST(LBNLBL AS VARCHAR(3)),3) AS 'NBL',
               LBNLOT 
        FROM OpenQuery(IBMDASQL, 'SELECT LBARCL, LBINAC, LBNBIN, LBNUMI, LBNLBL, LBNLOT  FROM SUPGCOD.LIGBLVP WHERE LBCART IN ( """ + part_numbers_query_string + """ )') 
    ) A
    JOIN 
    (
        SELECT * FROM OpenQuery(IBMDASQL, 'SELECT ESONBL,ESOREF FROM SUPACCD.ENSOSTP WHERE ESONAR IN ( """ + part_numbers_query_string + """ )')
    ) B ON B.ESONBL = A.NBL
    JOIN
    (
        SELECT * FROM OpenQuery(IBMDASQL, 'SELECT FUMCLE,FUMNUM FROM SUPACCD.FSAUMP')
    ) C ON C.FUMCLE = B.ESOREF
    LEFT JOIN ReportGenerationStatusByCustomerLot D ON A.LBNLOT = D.CustomerLot
    
    WHERE A.LBNLOT != ''  AND D.CustomerLot IS NULL 
    ORDER BY LBNLOT
        
    """

    result_df = pd.read_sql(query, session.bind)
    if len(result_df) > 0:
        grouped_df =  result_df.groupby(['CustomerPartNumber',
                                         'CustomerRevision',
                                         'CustomerLotNumber'])['HandlingUnitNumber'].apply(list).reset_index(name='HandlingUnitNumberList')
        return grouped_df
    else:
        return None


def insert_report_status(session, reportUUID, customerLot, reportType, fileName, generationErrors):
    report_status_entry = dm.ReportGenerationStatusByCustomerLot(reportUUID=reportUUID,
                                                                 customerLot=customerLot,
                                                                 reportType=reportType,
                                                                 fileName=fileName,
                                                                 generationDateTime=datetime.now(),
                                                                 generationErrors=generationErrors)
    session.add(report_status_entry)
    session.flush()
    return None


def get_customer_revision(session, router_number):
    query = r"""
    SELECT UM.FUMNAR, C.ICICLA FROM OpenQuery(IBMDASQL, 'SELECT * FROM SUPACCD.FSAUMP') UM
    JOIN 
        (
        SELECT A.ICNCLI,A.ICCART,A.ICIART,A.ICICLA FROM OpenQuery(IBMDASQL, 'SELECT * FROM SUPGCOD.INDCLIP') A
            INNER JOIN
            (   
                SELECT ICNCLI,ICCART,ICIART,MAX(CAST(ICDDIC As int)) AS ICDDIC
                FROM OpenQuery(IBMDASQL, 'SELECT * FROM SUPGCOD.INDCLIP')
                GROUP BY ICNCLI,ICCART,ICIART
            ) B ON A.ICNCLI = B.ICNCLI
                AND A.ICCART = B.ICCART
                AND A.ICIART = B.ICIART
                AND A.ICDDIC = B.ICDDIC
        ) C ON UM.FUMCLI = C.ICNCLI
            AND UM.FUMNAR = C.ICCART
            AND UM.FUMNIN = C.ICIART
    
     WHERE UM.FUMNUM = '""" + str(router_number) + """'
        
    """

    result_df = pd.read_sql(query, session.bind)
    if len(result_df) > 0:
        return result_df['ICICLA'].iloc[0]
    else:
        return None




def get_inspection_plan_records(session, operation_uuid, inspection_plan_label):
    return session.query(dm.InspectionPlan).join(dm.Operation). \
        filter(dm.InspectionPlan.inspectionPlanLabel == inspection_plan_label). \
        filter(dm.Operation.uuid == operation_uuid). \
        all()


def get_control_records(session, operation_uuid, inspection_plan_label, control_label):
    return session.query(dm.Control).join(dm.InspectionPlan).join(dm.Operation). \
        filter(dm.Operation.uuid == operation_uuid). \
        filter(dm.InspectionPlan.inspectionPlanLabel == inspection_plan_label). \
        filter(dm.Control.controlLabel == control_label). \
        all()


def get_operation(session, operation_uuid):
    result = pd.read_sql(session.query(dm.Operation).
                         filter(dm.Operation.uuid == operation_uuid).
                         statement,
                         session.bind)
    return result


def insert_control_run_feature(session, control_run_id, feature_label, feature_flag):
    feature = dm.Feature(controlRunId=control_run_id,
                         featureLabel=feature_label,
                         feature_flag=feature_flag)
    session.add(feature)
    session.flush()
    return feature.id


def insert_control_run(session, control_id, start_time_string, end_time_string, use, control_type, version, count):
    control_run = dm.ControlRun(controlId=control_id,
                                timeCycleStart=parse_timestamp(start_time_string),
                                timeCycleStop=parse_timestamp(end_time_string),
                                importDateTime=datetime.now(),
                                use=use,
                                type=control_type,
                                version=version,
                                count=count)
    session.add(control_run)
    session.flush()
    return control_run.id


def insert_control_run_spec(session, run_header, run_id):
    for ix in range(len(run_header["CtrlSpc"])):
        for k in run_header["CtrlSpc"][ix]:
            spec_value = run_header["CtrlSpc"][ix][k]
            if isinstance(spec_value, str):
                control_metadata_ctrl_param = dm.ControlRunMetadata(runId=run_id,
                                                                    key=k,
                                                                    stringValue=spec_value)
            else:
                control_metadata_ctrl_param = dm.ControlRunMetadata(runId=run_id,
                                                                    key=k,
                                                                    decimalValue=float(spec_value))

            session.add(control_metadata_ctrl_param)


def insert_inspection_plan_run(session, inspection_plan_id, start_time_string, end_time_string, count):
    inspection_plan_run = dm.InspectionPlanRun(inspectionPlanId=inspection_plan_id,
                                               timeCycleStart=parse_timestamp(start_time_string),
                                               timeCycleStop=parse_timestamp(end_time_string),
                                               importDateTime=datetime.now(),
                                               count=count)
    session.add(inspection_plan_run)
    session.flush()
    return inspection_plan_run.id


def calculate_station_data(engine, operation_uuid):
    query1 = r"""
    DELETE FROM [StationOperationResult]
    WHERE [OperationUUID] = '""" + str(operation_uuid) + """'"""
    query2 = r"""
    INSERT INTO [StationOperationResult] 
    SELECT [OperationUUID], [Station],
    SUM(CASE WHEN [StationStatus]=0 THEN 1 ELSE 0 END) AS [Conforming],
    SUM(CASE WHEN [StationStatus]=1 THEN 1 ELSE 0 END) AS [NonConforming],
    COUNT([StationStatus]) AS [Count]
    FROM
    (
        SELECT C.[OperationUUID], C.Station AS 'Station', M.[Rank], MAX(M.Value) AS [StationStatus]
        FROM  [InspectionPlan] C 

        JOIN [InspectionPlanRun] CR ON C.InspectionPlanId = CR.InspectionPlanId
        JOIN [InspectionPlanMeasure] M ON CR.[InspectionPlanRunId] = M.[InspectionPlanRunId]

        WHERE C.OperationUUID = '""" + str(operation_uuid) + """'
        AND M.Value IN (0, 1)
        GROUP BY C.[OperationUUID], C.Station, [M].[Rank]
    ) T
    GROUP BY [OperationUUID], [Station]
    """
    engine.execute(query1)
    engine.execute(query2)

'''
class CtdsHandler:
    def __init__(self, db_host, db_user, db_pass, db_name):
        self.db_host = db_host
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_name = db_name

    def insert_bulk_run(self, run_id, run_header):
        with ctds.connect(self.db_host, user=self.db_user, password=self.db_pass, database=self.db_name) as connection:
            connection.bulk_insert('InspectionPlanRunControl',
                                   [(ctds.SqlBigInt(run_id),
                                     ctds.SqlVarChar(x.encode('latin-1'))) for x in
                                    run_header["Ctrl_List"]],
                                   batch_size=500,
                                   )

    def insert_measure(self, measure):
        with ctds.connect(self.db_host, user=self.db_user, password=self.db_pass, database=self.db_name) as connection:
            connection.bulk_insert('InspectionPlanMeasure', measure, batch_size=5000)

    def insert_histogram(self, histogram_data):
        with ctds.connect(self.db_host, user=self.db_user, password=self.db_pass, database=self.db_name, timeout=20) \
                as connection:
            connection.bulk_insert('ControlOperationDistribution', histogram_data, batch_size=500)

    def insert_metadata(self, metadata):
        with ctds.connect(self.db_host, user=self.db_user, password=self.db_pass, database=self.db_name, timeout=20) \
                as connection:
            connection.bulk_insert('FeatureMetadata', metadata, batch_size=500)


def convert_integer_measure(sql_data):
    """
    Converts a list of list to list of tuple with new types
    [0] : int -> ctds.SqlBigInt
    [1] : int -> ctds.SqlInt
    [2] : int -> ctds.SqlBigInt
    """

    output = [(ctds.SqlBigInt(x[0]),
               ctds.SqlInt(x[1]),
               ctds.SqlBigInt(x[2])
               ) for x in sql_data]

    return output


def format_for_bulk_import(sql_data):
    """
    Converts a list of list to list of tuple with new types
    [0] : unchanged
    [1] : float -> ctds.SqlDecimal with precision 13 and scale 6
    [2] : float -> ctds.SqlDecimal with precision 13 and scale 6
    [3:] : unchanged
    """
    output = [(x[0],
               ctds.SqlDecimal("%.6f" % x[1], 13, 6),
               ctds.SqlDecimal("%.6f" % x[2], 13, 6)
               ) + x[3:] for x in sql_data]

    return output


def convert_feature_metadata_to_varchar(sql_data):
    """
    Converts a list of list to list of tuple with new types
    [0] : unchanged
    [1] : string -> ctds.SqlVarChar with latin-1 encoding
    [2] : string -> ctds.SqlVarChar with latin-1 encoding
    [3] : string -> ctds.SqlVarChar with latin-1 encoding
    """
    output = [(x[0],
               ctds.SqlVarChar(str(x[1]).encode('latin-1')),
               ctds.SqlVarChar(str(x[2]).encode('latin-1') if x[2] is not None else None)) for x in sql_data]

    return output
'''