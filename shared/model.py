from sqlalchemy import Column, ForeignKey, String, Integer, DateTime, BigInteger, Numeric, UniqueConstraint, Boolean
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Operation(Base):
    __tablename__ = 'Operation'
    uuid = Column("OperationUUID", String(36), primary_key=True)
    inspectionPlan = relationship("InspectionPlan", back_populates="operation", cascade="")
    machine = Column("Machine", String(255))
    partNumber = Column("PartNumber", String(255))
    lot = Column("Lot", String(255))
    routerNumber = Column("RouterNumber", String(255))
    sequenceNumber = Column("Sequence", Integer())
    timeProdStart = Column("TimeProdStart", DateTime())
    timeProdStop = Column("TimeProdStop", DateTime())


class InspectionPlan(Base):
    __tablename__ = "InspectionPlan"
    id = Column("InspectionPlanId", BigInteger(), primary_key=True)
    operationUUID = Column("OperationUUID",
                           String(36),
                           ForeignKey('Operation.OperationUUID', onupdate="CASCADE", ondelete="CASCADE"),
                           nullable=False)
    inspectionPlanLabel = Column("InspectionPlanLabel", String(255), nullable=False)
    computer = Column("Computer", Integer)
    partIndex = Column("PartIndex", String(255))
    station = Column("Station", String(255))
    device = Column("Device", String(255))
    operation = relationship("Operation", back_populates="inspectionPlan", foreign_keys=[operationUUID])
    control = relationship("Control", back_populates="inspectionPlan", )
    run = relationship("InspectionPlanRun", back_populates="inspectionPlan")
    __table_args__ = (UniqueConstraint("OperationUUID", "InspectionPlanLabel"),)


class Control(Base):
    __tablename__ = 'Control'
    id = Column("ControlId", BigInteger(), primary_key=True)
    inspectionPlanId = Column("InspectionPlanId",
                              BigInteger(),
                              ForeignKey('InspectionPlan.InspectionPlanId', onupdate="CASCADE", ondelete="CASCADE"),
                              nullable=False)
    controlLabel = Column("ControlLabel", String(255), nullable=False)
    type = Column("Type", String(255), nullable=False)
    inspectionPlan = relationship("InspectionPlan", back_populates="control", foreign_keys=[inspectionPlanId])
    run = relationship("ControlRun", back_populates="control")
    __table_args__ = (UniqueConstraint("ControlLabel", "InspectionPlanId"),)


class ControlOperationResult(Base):
    __tablename__ = "ControlOperationResult"
    id = Column("ControlOperationFeatureId", BigInteger(), primary_key=True)
    controlId = Column("ControlId",
                       BigInteger(),
                       ForeignKey('Control.ControlId', onupdate="CASCADE", ondelete="CASCADE"))
    featureLabel = Column("FeatureLabel", String(255))
    conforming = Column("Conforming", BigInteger())
    nonConforming = Column("NonConforming", BigInteger())
    count = Column("Count", BigInteger())
    undefined = Column("Undefined", BigInteger())
    unevaluated = Column("Unevaluated", BigInteger())

    __table_args__ = (UniqueConstraint("ControlId", "FeatureLabel"),)


class ControlOperationResultValue(Base):
    __tablename__ = 'ControlOperationResultValue'
    controlOperationFeatureId = Column("ControlOperationFeatureId", BigInteger(),
                                       ForeignKey('ControlOperationResult.ControlOperationFeatureId',
                                                  onupdate="CASCADE", ondelete="CASCADE"),
                                       primary_key=True)
    average = Column("Average", Numeric(13, 6))
    maximum = Column("Maximum", Numeric(13, 6))
    median = Column("Median", Numeric(13, 6))
    minimum = Column("Minimum", Numeric(13, 6))
    outlierCount = Column("OutlierCount", BigInteger())
    q1 = Column("Q1", Numeric(13, 6))
    q3 = Column("Q3", Numeric(13, 6))
    standardDeviation = Column("StandardDeviation", Numeric(13, 6))


class StationOperationResult(Base):
    __tablename__ = 'StationOperationResult'
    operationUUID = Column("OperationUUID", String(36), ForeignKey('Operation.OperationUUID',
                                                                   onupdate="CASCADE", ondelete="CASCADE"),
                           )
    station = Column("Station", String(255))
    conforming = Column("Conforming", Integer())
    nonConforming = Column("NonConforming", Integer())
    count = Column("Count", Integer())
    __table_args__ = (
        PrimaryKeyConstraint(operationUUID, station),
    )


class ControlOperationDistribution(Base):
    __tablename__ = 'ControlOperationDistribution'
    controlOperationFeatureId = Column("ControlOperationFeatureId", BigInteger(),
                                       ForeignKey('ControlOperationResult.ControlOperationFeatureId',
                                                  onupdate="CASCADE", ondelete="CASCADE"),
                                       )
    lowerLimit = Column("ControlOperationDistributionLowerLimit", Numeric(13, 6))
    upperLimit = Column("ControlOperationDistributionUpperLimit", Numeric(13, 6))
    count = Column("ControlOperationDistributionCount", BigInteger())
    __table_args__ = (
        PrimaryKeyConstraint(controlOperationFeatureId, lowerLimit, upperLimit),
    )


class InspectionPlanRun(Base):
    __tablename__ = 'InspectionPlanRun'
    id = Column("InspectionPlanRunId", BigInteger(), primary_key=True)
    inspectionPlanId = Column("InspectionPlanId", BigInteger(), ForeignKey('InspectionPlan.InspectionPlanId',
                                                                           onupdate="CASCADE", ondelete="CASCADE"),
                              nullable=False)
    timeCycleStart = Column("TimeCycleStart", DateTime())
    timeCycleStop = Column("TimeCycleStop", DateTime())
    importDateTime = Column("ImportDateTime", DateTime())
    count = Column("Count", BigInteger())
    inspectionPlan = relationship("InspectionPlan", back_populates="run", foreign_keys=[inspectionPlanId])
    runControl = relationship("InspectionPlanRunControl", back_populates="run")
    measure = relationship("InspectionPlanMeasure", back_populates="run")


class InspectionPlanRunControl(Base):
    __tablename__ = 'InspectionPlanRunControl'
    runId = Column("InspectionPlanRunId", BigInteger(),
                   ForeignKey('InspectionPlanRun.InspectionPlanRunId',
                              onupdate="CASCADE", ondelete="CASCADE")
                   )
    run = relationship("InspectionPlanRun",
                       back_populates="runControl",
                       foreign_keys=[runId])
    label = Column("ControlLabel", String(255))
    __table_args__ = (
        PrimaryKeyConstraint(runId, label),
    )


class InspectionPlanOperationResult(Base):
    __tablename__ = 'InspectionPlanOperationResult'
    inspectionPlanId = Column("InspectionPlanId", BigInteger(), ForeignKey('InspectionPlan.InspectionPlanId',
                                                                           onupdate="CASCADE", ondelete="CASCADE"),
                              primary_key=True)
    conforming = Column("Conforming", BigInteger())
    nonConforming = Column("NonConforming", BigInteger())
    count = Column("Count", BigInteger())
    undefined = Column("Undefined", BigInteger())
    unevaluated = Column("Unevaluated", BigInteger())


class ControlRun(Base):
    __tablename__ = 'ControlRun'
    id = Column("ControlRunId", BigInteger(), primary_key=True)
    controlId = Column("ControlId", BigInteger(), ForeignKey('Control.ControlId',
                                                             onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type = Column("Type", String(255), nullable=False)
    version = Column("Version", String(255))
    timeCycleStart = Column("TimeCycleStart", DateTime())
    timeCycleStop = Column("TimeCycleStop", DateTime())
    importDateTime = Column("ImportDateTime", DateTime())
    use = Column("Use", String(255))
    count = Column("Count", BigInteger())
    control = relationship("Control", back_populates="run", foreign_keys=[controlId])
    controlRunMetadata = relationship("ControlRunMetadata", back_populates="run")
    feature = relationship("Feature", back_populates="run", cascade="all, delete-orphan")


class ControlRunMetadata(Base):
    __tablename__ = 'ControlRunMetadata'
    runId = Column("ControlRunId",
                   BigInteger(),
                   ForeignKey('ControlRun.ControlRunId', onupdate="CASCADE", ondelete="CASCADE")
                   )
    key = Column("ControlRunMetadataKey", String(255))
    stringValue = Column("ControlRunMetadataStringValue", String(255))
    decimalValue = Column("ControlRunMetadataDecimalValue", Numeric(13, 6))
    run = relationship("ControlRun", back_populates="controlRunMetadata")
    __table_args__ = (
        PrimaryKeyConstraint(runId, key),
    )


class Feature(Base):
    __tablename__ = 'Feature'
    id = Column("FeatureId", BigInteger(), primary_key=True)
    controlRunId = Column("ControlRunId", BigInteger(),
                          ForeignKey('ControlRun.ControlRunId', onupdate="CASCADE", ondelete="CASCADE"),
                          nullable=False)
    featureLabel = Column("FeatureLabel", String(255))
    feature_flag = Column("MeasureFlag", Boolean())
    run = relationship("ControlRun", back_populates="feature")
    featureMetadata = relationship("FeatureMetadata", back_populates="feature")
    measure = relationship("Measure", back_populates="feature")

    __table_args__ = (UniqueConstraint("ControlRunId", "FeatureLabel"),)


class FeatureMetadata(Base):
    __tablename__ = 'FeatureMetadata'
    featureId = Column("FeatureId", BigInteger(), ForeignKey('Feature.FeatureId',
                                                             onupdate="CASCADE", ondelete="CASCADE")
                       )
    key = Column("FeatureMetadataKey", String(255))
    value = Column("FeatureMetadataValue", String(255))
    feature = relationship("Feature", back_populates="featureMetadata")
    __table_args__ = (
        PrimaryKeyConstraint(featureId, key),
    )


class Measure(Base):
    __tablename__ = 'Measure'
    featureId = Column("FeatureId", BigInteger(), ForeignKey('Feature.FeatureId',
                                                             onupdate="CASCADE", ondelete="CASCADE"))
    rank = Column("Rank", BigInteger())
    integerValue = Column("IntegerValue", Integer())
    decimalValue = Column("DecimalValue", Numeric(13, 6))
    feature = relationship("Feature", back_populates="measure")
    __table_args__ = (
        PrimaryKeyConstraint(featureId, rank),
    )


class InspectionPlanMeasure(Base):
    __tablename__ = 'InspectionPlanMeasure'
    rank = Column("Rank", BigInteger())
    value = Column("Value", Integer())
    runId = Column("InspectionPlanRunId", BigInteger(),
                   ForeignKey('InspectionPlanRun.InspectionPlanRunId',
                              onupdate="CASCADE", ondelete="CASCADE")
                   )
    run = relationship("InspectionPlanRun", back_populates="measure")
    __table_args__ = (
        PrimaryKeyConstraint(runId, rank),
    )


class ReportGenerationStatus(Base):
    __tablename__ = 'ReportGenerationStatus'
    reportUUID = Column("ReportUUID", String(36))
    operationUUID = Column("OperationUUID", String(36),
                           ForeignKey('Operation.OperationUUID', onupdate="CASCADE", ondelete="CASCADE"))
    reportType = Column("ReportType", String(255))
    fileName = Column("FileName", String(255))
    generationDateTime = Column("GenerationDateTime", DateTime())
    generationErrors = Column("GenerationErrors", Integer())
    __table_args__ = (
        PrimaryKeyConstraint(reportUUID, operationUUID),
    )


class ReportGenerationStatusByCustomerLot(Base):
    __tablename__ = 'ReportGenerationStatusByCustomerLot'
    reportUUID = Column("ReportUUID", String(36))
    customerLot = Column("CustomerLot", String(36))
    reportType = Column("ReportType", String(255))
    fileName = Column("FileName", String(255))
    generationDateTime = Column("GenerationDateTime", DateTime())
    generationErrors = Column("GenerationErrors", Integer())
    __table_args__ = (
        PrimaryKeyConstraint(reportUUID, customerLot),
    )