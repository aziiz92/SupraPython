#
#
#
# Lorsque le moteur d’import traite le dernier fichier d’un PC et qui a un "Time_Prod_Stop", alors on déclenche la génération des rapports pour ce numéro de lot.
#
#
#
# Interroger la base de données pour savoir s’il y a d’autres passage à prendre en compte
#
# Récupérer de la base de données la référence des pièces conformes du poste concerné (tous contrôles confondus).
# Parser le fichier de résultat de gamme
# Parser tous les fichiers JSON des contrôles sélectionnés
#
# Retirer les pièces qui ont au moins un contrôle non conforme sur ce poste
#
# Calculer le nombre de pièces par classe à l’aide de np.histogram avec 20 classes sur l'intervalle de tolérance
#
# Calculer les indicateurs statistiques (nombre de pièces, moyenne, écart type, variance, min, max)
#
#
#
# Envoyer une requête HTTP POST à Ignition avec les données nécessaires à la génération du rapport
#
# Ignition génère le rapport PDF, l’enregistre sur le réseau et ajoute un enregistrement dans une table de suivi.
#
import os
import json
import requests
import io
import operator
import logging
from datetime import datetime
from uuid import uuid4

from logging import handlers

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pyodbc  # added in order to force the dependency during the build phase
import numpy as np
import pandas as pd

from svglib.svglib import svg2rlg
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4

from histogram.configutils import config
from db_query import get_operations_by_router_number_and_date, get_lots_to_generate_report, insert_report_status, \
    get_customer_revision, get_operations_by_router_number_list
from shared.fileservice import get_measures
from shared.logger import init_logger, close_logger

logger = logging.getLogger(__name__)

report_root_path = os.getenv("VISITRI_IMPORT_REPORT_ROOT_PATH",
                             r"C:\Users\e.andre\Documents\temp\import-visitri\report\\")
report_log_path = os.getenv("VISITRI_IMPORT_REPORT_LOG_PATH",
                            r"C:\Users\e.andre\Documents\temp\import-visitri\report\\")

period = int(os.getenv("VISITRI_IMPORT_REPORT_PERIOD", 12))
db_host = os.getenv("VISITRI_IMPORT_DB_HOST", "192.168.0.77")
db_name = os.getenv("VISITRI_IMPORT_DB_NAME", "IMPORT_VISITRI_3")
db_user = os.getenv("VISITRI_IMPORT_DB_USER", "ignition")
db_pass = os.getenv("VISITRI_IMPORT_DB_PASS", "6j4RxkjPhLgqGiBe")
# db_host = os.getenv("VISITRI_IMPORT_DB_HOST", "10.242.115.78")
# db_host = os.getenv("VISITRI_IMPORT_DB_HOST", "10.0.0.2")
# db_name = os.getenv("VISITRI_IMPORT_DB_NAME", "IMPORT_VISITRI_3")
# db_user = os.getenv("VISITRI_IMPORT_DB_USER", "orm")
# db_pass = os.getenv("VISITRI_IMPORT_DB_PASS", "orm")
# Create the SQL data connection
connection_string = "mssql://" + db_user + \
                    ":" + db_pass + \
                    "@" + db_host + \
                    "/" + db_name + "?driver=ODBC+Driver+17+for+SQL+Server"

engine = create_engine(connection_string,
                       # echo=True
                       )
Session = sessionmaker(bind=engine)
session = Session()


class InspectionPlanData:
    def __init__(self, name):
        self.controls = {}
        self.name = name

    def add_data(self, control_name, feature_name, uuid, measure_df, specs_df, timeProdStart):

        if control_name not in self.controls:
            control = ControlData()
            self.controls[control_name] = control
        else:
            control = self.controls[control_name]
        control.add_data(self.name, control_name, feature_name, uuid, measure_df, specs_df, timeProdStart)

    def aggregate_data(self):
        for control in self.controls:
            self.controls[control].aggregate_data()

    def generate_story(self):
        story = []
        for control in self.controls:
            story.extend(self.controls[control].generate_story())
        return story


class ControlData:
    def __init__(self):
        self.features = {}

    def add_data(self, inspection_plan_name, control_name, feature_name, uuid, measure_df, specs_df, timeProdStart):
        if feature_name not in self.features:
            feature = FeatureData(inspection_plan_name, control_name, feature_name)
            self.features[feature_name] = feature
        else:
            feature = self.features[feature_name]
        feature.add_data(uuid, measure_df, specs_df, timeProdStart)

    def aggregate_data(self):
        for feature in self.features:
            self.features[feature].aggregate_data()

    def generate_story(self):
        story = []
        for feature in self.features:
            story.extend(self.features[feature].generate_story())
        return story


class FeatureData:

    def __init__(self, inspection_plan_name, control_name, feature_name):
        self.inspection_plan_name = inspection_plan_name
        self.control_name = control_name
        self.feature_name = feature_name
        self.measures = {}
        self.specs = {}
        self.timeProdStart = {}
        self.measures_aggregated = pd.DataFrame()
        self.specs_aggregated = None
        self.last_operation_uuid = None

    def add_data(self, uuid, measure_df, specs_df, timeProdStart):
        if uuid not in self.measures and uuid not in self.specs:
            self.measures[uuid] = measure_df
            self.specs[uuid] = specs_df
            self.timeProdStart[uuid] = timeProdStart
        else:
            logger.error("Measures already exist for this uuid")

    def aggregate_data(self):
        for uuid in self.measures:
            self.measures_aggregated = self.measures_aggregated.append(self.measures[uuid])
        self.find_last_operation()
        self.specs_aggregated = self.specs[self.last_operation_uuid]

    def generate_story(self):
        story = []
        nominal = self.specs_aggregated.loc[self.feature_name, 'Cote_Plan']
        usl = nominal + self.specs_aggregated.loc[self.feature_name, 'TolSup_Initial']
        lsl = nominal - self.specs_aggregated.loc[self.feature_name, 'TolInf_Initial']

        buf = io.BytesIO()

        fig, ax = plt.subplots(figsize=(8, 5))

        plt.hist(self.measures_aggregated["Feature_Value"], bins=20, range=[lsl, usl], ec='black')

        plt.axvline(x=lsl, color="r", linewidth=0.5)
        plt.axvline(x=usl, color="r", linewidth=0.5, label="Test")
        plt.axvline(x=nominal, color="black", linewidth=0.5)

        trans = ax.get_xaxis_transform()

        plt.text(usl,
                 0.99,
                 'Upper Spec Limit: ' + '{:.3f}'.format(usl),
                 fontsize="x-small",
                 transform=trans, rotation=90,
                 color="r",
                 bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 1},
                 ha='center', va='top')
        plt.text(nominal,
                 0.99,
                 'Nominal: ' + '{:.3f}'.format(nominal),
                 fontsize="x-small",
                 transform=trans,
                 rotation=90,
                 color="black",
                 bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 1},
                 ha='center', va='top')
        plt.text(lsl,
                 0.99,
                 'Lower Spec Limit: ' + '{:.3f}'.format(lsl),
                 fontsize="x-small",
                 transform=trans,
                 rotation=90,
                 color="r",
                 bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 1},
                 ha='center', va='top')

        plt.title("Distribution of measurements", fontsize=10)

        plt.xlabel('Value', fontsize=10)
        plt.ylabel('Frequency', fontsize=10)

        plt.savefig(buf, format="svg")
        plt.close()
        buf.seek(0)

        flowable_image = scale(svg2rlg(buf), scaling_factor=.8)

        std_dev = self.measures_aggregated["Feature_Value"].std()
        mean = self.measures_aggregated["Feature_Value"].mean()

        cpk = min((usl - mean) / (3. * std_dev), (mean - lsl) / (3. * std_dev))

        data = [['Sorting: 100%'],
                ['Inspection plan', str(self.inspection_plan_name)],
                ['Control', str(self.control_name)],
                ['Feature', str(self.feature_name)],
                ['Nominal', '{:.3f}'.format(nominal)],
                ['Lower spec limit', '{:.3f}'.format(lsl)],
                ['Upper spec limit', '{:.3f}'.format(usl)],
                [],
                ['Part count', self.measures_aggregated["Feature_Value"].count()],
                ['Mean', '{:.3f}'.format(mean)],
                ['Min', '{:.3f}'.format(self.measures_aggregated["Feature_Value"].min())],
                ['Max', '{:.3f}'.format(self.measures_aggregated["Feature_Value"].max())],
                ['Cpk', '{:.2f}'.format(cpk)],
                ]

        t = Table(data, hAlign='LEFT')

        story.append(t)
        story.append(flowable_image)
        story.append(PageBreak())
        return story

    def find_last_operation(self):
        self.last_operation_uuid = max(self.timeProdStart.items(), key=operator.itemgetter(1))[0]


class ReportCanvas(canvas.Canvas):

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_canvas(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_canvas(self, page_count):
        page = "Page %s of %s" % (self._pageNumber, page_count)
        x = 128
        self.saveState()
        self.drawImage("images/supra_logo.png", x=50, y=A4[1] - 65, width=150, preserveAspectRatio=True, anchor="sw")
        # self.setStrokeColorRGB(0, 0, 0)
        # self.setLineWidth(0.5)
        # self.line(66, 78, A4[0] - 66, 78)
        self.setFont('Helvetica', 10)
        self.drawString(A4[0] / 2, 25, page)
        self.restoreState()


class HistogramReport:
    def __init__(self, *args, **kwargs):
        self.filename = 'test.pdf'

        self.doc = None

        self.report_title = None
        self.lot_number = ""
        self.Story = []
        self.report_uuid = None
        self.report_datetime = None
        # dict with {"name":InspectionPlanData}
        self.inspection_plans = {}

    def add_inspection_plan(self, inspection_plan_name):
        if inspection_plan_name not in self.inspection_plans:
            inspection_plan = InspectionPlanData(inspection_plan_name)
            self.inspection_plans[inspection_plan_name] = inspection_plan
            return inspection_plan
        else:
            return self.inspection_plans[inspection_plan_name]

    def aggregate_measures(self):
        for inspection_plan in self.inspection_plans:
            self.inspection_plans[inspection_plan].aggregate_data()

    def generate_story(self):
        for inspection_plan in self.inspection_plans:
            self.Story.extend(self.inspection_plans[inspection_plan].generate_story())

    def add_title(self, canvas, doc):
        # If the left_footer attribute is not None, then add it to the page
        canvas.saveState()
        if self.report_title is not None:
            canvas.setFont('Helvetica', 12)
            canvas.drawCentredString(14 * cm, A4[1] - 1.5 * cm, "Measurement report")
            canvas.drawCentredString(14 * cm, A4[1] - 2.2 * cm, self.report_title)
            canvas.drawCentredString(14 * cm, A4[1] - 2.9 * cm, "Lot #: " + str(self.lot_number))
            canvas.setTitle(self.report_title)

        if self.report_uuid is not None:
            footer = "Report " + self.report_uuid + \
                     " generated on " + \
                     self.report_datetime.strftime("%Y-%m-%dT%H:%M:%S")
            canvas.setFont('Helvetica', 6)
            canvas.drawString(0.2 * cm, 0.2 * cm, footer)

        canvas.restoreState()

    def generate_report(self):
        self.doc = SimpleDocTemplate(self.filename,
                                     topMargin=3 * cm, bottomMargin=1 * cm,
                                     leftMargin=2 * cm, rightMargin=1 * cm)
        self.doc.build(self.Story, canvasmaker=ReportCanvas,
                       onFirstPage=self.add_title,
                       onLaterPages=self.add_title)


# def generate_report_for_lot(lot_number):
#     return None


def get_operations_from_router_number(router_number, timestamp):
    operations = get_operations_by_router_number_and_date(session, router_number, timestamp)

    if len(operations) > 0:
        return operations
    return None


def get_operations_from_router_number_list(router_numbers):
    operations = get_operations_by_router_number_list(session, router_numbers)

    if len(operations) > 0:
        return operations
    return None


def scale(drawing, scaling_factor):
    """
    Scale a reportlab.graphics.shapes.Drawing()
    object while maintaining the aspect ratio
    """
    scaling_x = scaling_factor
    scaling_y = scaling_factor

    drawing.width = drawing.minWidth() * scaling_x
    drawing.height = drawing.height * scaling_y
    drawing.scale(scaling_x, scaling_y)
    drawing.hAlign = "CENTER"
    return drawing


def generate_report_for_lot(report_path, customer_lot_number, router_numbers, part_number, customer_revision):
    report_uuid = str(uuid4())
    report_datetime = datetime.now()
    error_count = 0
    logger.info("Customer lot number: " + str(customer_lot_number))
    logger.info("Router numbers: " + str(router_numbers))
    logger.info("Report UUID: " + str(report_uuid))

    report_filename = str(part_number) + " - " + str(customer_lot_number) + ".pdf"

    try:

        operations = get_operations_from_router_number_list(router_numbers)
        # we loop through the list of uuids

        report = HistogramReport()
        if operations is None:
            logger.error("No operation found for " + str(customer_lot_number) + " in database")
            insert_report_status(session=session,
                                 reportUUID=report_uuid,
                                 customerLot=customer_lot_number,
                                 reportType="histogram",
                                 fileName=report_filename,
                                 generationErrors=None)
            session.commit()
            return None

        logger.info(str(len(operations)) + " operation(s) will be aggregated")

        for operation in operations:
            try:
                error_count = 0
                uuid = operation.uuid
                machine = operation.machine
                router_number = operation.routerNumber
                operation_timeProdStart = operation.timeProdStart

                logger.info("Operation UUID: " + uuid)
                logger.info("Router number: " + router_number)
                logger.info("Sequence : " + str(operation.sequenceNumber))

                for item in config["histogram_config"]:

                    story = []
                    if str(item["part_number"]) == str(part_number):

                        for inspection_plans in item["inspection_plans"]:
                            for inspection_plan in inspection_plans:
                                logger.info("Inspection plan: " + str(inspection_plan))
                                inspection_plan_data = get_measures(uuid, machine, inspection_plan)

                                if inspection_plan_data[0] is None:
                                    logger.error("Inspection plan: " + str(inspection_plan))
                                    logger.error("Inspection plan file not found or empty")
                                    error_count += 1
                                    continue

                                inspection_plan_status_df = inspection_plan_data[0]["Status"]

                                inspection_plan_report_object = report.add_inspection_plan(inspection_plan)

                                if inspection_plan_data[2] != uuid:
                                    logger.error("UUID error!!")
                                    error_count += 1
                                for control_dict in inspection_plans[inspection_plan]:
                                    for control in control_dict:
                                        logger.info("Control: " + str(control))
                                        features = control_dict[control]
                                        control_data = get_measures(uuid, machine, control)

                                        if control_data[0] is None:
                                            error_count += 1
                                            continue

                                        for feature in features:
                                            logger.info("Feature: " + str(feature))
                                            if control_data[2] != uuid:
                                                logger.error("UUID error!!")
                                            if feature not in control_data[0]:
                                                logger.error(feature + " not found in control " + control)
                                                error_count += 1
                                                continue
                                            feature_df = control_data[0][feature]

                                            feature_df = feature_df.merge(inspection_plan_status_df, how="right",
                                                                          left_index=True, right_index=True)

                                            feature_df = feature_df[feature_df["Status"] == 0]
                                            feature_df = feature_df[feature_df["Feature_Value"].notnull()]
                                            logger.info("Adding " + str(len(feature_df)) + " parts")
                                            feature_spec = control_data[1][0]["Specs"]

                                            inspection_plan_report_object.add_data(control,
                                                                                   feature,
                                                                                   uuid,
                                                                                   feature_df,
                                                                                   feature_spec,
                                                                                   operation_timeProdStart)
            except Exception as e:
                error_count += 1
                logger.error(e, exc_info=True)
                continue

        report.aggregate_measures()
        report.generate_story()

        report.report_title = str(part_number) + " Rev " + customer_revision + " - " + customer_lot_number
        report.lot_number = customer_lot_number
        report.report_uuid = report_uuid
        report.report_datetime = report_datetime
        report.filename = report_path + report_filename

        report.generate_report()

        insert_report_status(session=session,
                             reportUUID=report_uuid,
                             customerLot=customer_lot_number,
                             reportType="histogram",
                             fileName=report_filename,
                             generationErrors=error_count)
        session.commit()

    except Exception as e:
        error_count += 1
        logger.error(e, exc_info=True)
        insert_report_status(session=session,
                             reportUUID=report_uuid,
                             customerLot=customer_lot_number,
                             reportType="histogram",
                             fileName=report_filename,
                             generationErrors=error_count)
        session.commit()
        return False

    return True


def get_lots_to_process():
    part_numbers = []
    for item in config["histogram_config"]:
        part_numbers.append(str(item["part_number"]))

    records = get_lots_to_generate_report(session, part_numbers)

    for index, row in records.iterrows():

        lot_number = row['CustomerLotNumber']
        router_numbers = row['HandlingUnitNumberList']
        part_number = row['CustomerPartNumber']
        customer_revision = row['CustomerRevision']
        report_path = report_root_path + part_number + "\\"
        if not os.path.exists(report_path):
            os.makedirs(report_path)
        log_path = report_log_path + part_number + "\\"
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        init_logger(__name__, log_path, part_number + " - " + lot_number)

        generate_report_for_lot(report_path, lot_number, router_numbers, part_number, customer_revision)

        close_logger(__name__)
    return None


get_lots_to_process()

# logger_histograms = init_logger(__name__, report_log_path, "12689.0308.6.41.381.log")
# generate_report_for_lot("12689.0308.6.41.381")
# close_logger(__name__)
#
# def get_raw_data_one_operation():
#     # we loop through the inspection plans that are in the configuration for this partnumber
#     for inspection plan in inspections_plans:
#
#         inspection_plan_results = get_inspection_plan_results_from_db
#             # we loop through the controls that are in the configuration for this inspection_plan
#             for control in controls:
#                 control_results = get_control_results
#                 filtered_control_results = filter non conforming parts using inspection_plan_results
#                 concatenate filtered_control_results in a big dataframe with inspection_plan, control and uuid columns and tolerances
