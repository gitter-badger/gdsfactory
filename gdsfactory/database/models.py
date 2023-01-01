from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Process(SQLModel, table=True):
    """Foundry Process."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str]
    version: Optional[str]


class Unit(SQLModel, table=True):
    """A unit is a definite magnitude of a quantity."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    quantity: str
    symbol: str
    description: Optional[str]


class Wafer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    serial_number: str
    name: str
    description: Optional[str]


class ComputedResult(SQLModel, table=True):
    """Results obtained after computation/analysis of the raw results contained in the table result."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str
    unit_id: Unit = Relationship(back_populates="id")
    value: str
    description: str
    domain: str
    domain_unit: Unit = Relationship(back_populates="id")
    unit: Unit = Relationship(back_populates="id")


# class Result(SQLModel, table=True):
#     __tablename__ = "result"
#     __table_args__ = {"comment": "This table holds all results."}

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     name = Column(String(200), nullable=False)
#     type = Column(String(50), nullable=False)
#     unit_id = Column(ForeignKey("unit.id"), index=True)
#     domain_unit_id = Column(ForeignKey("unit.id"), index=True)
#     value = Column(TEXT, nullable=False)
#     domain = Column(TEXT)
#     description = Column(String(200))

#     domain_unit = relationship("Unit", primaryjoin="Result.domain_unit_id == Unit.id")
#     unit = relationship("Unit", primaryjoin="Result.unit_id == Unit.id")


# class Reticle(SQLModel, table=True):
#     __tablename__ = "reticle"
#     __table_args__ = {"comment": "This table holds the definition of a reticle."}

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     name = Column(String(200), nullable=False)
#     position = Column(
#         String(50), comment="Position of the reticle on the wafer. (ROW, COLUMN)"
#     )
#     size = Column(
#         String(50),
#         comment="The size of the reticle (X,Y) having the convention that -Å· points towards the notch/flat of the wafer.",
#     )
#     wafer_id = Column(ForeignKey("wafer.id"), nullable=False, index=True)
#     description = Column(String(200))

#     wafer = relationship("Wafer")


# class ComputedResultSelfRelation(SQLModel, table=True):
#     __tablename__ = "computed_result_self_relation"
#     __table_args__ = {
#         "comment": "This table holds all computed results self relation. This is used to link computed results together"
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     computed_result1_id = Column(
#         ForeignKey("computed_result.id"), nullable=False, index=True
#     )
#     computed_result2_id = Column(
#         ForeignKey("computed_result.id"), nullable=False, index=True
#     )

#     computed_result1 = relationship(
#         "ComputedResult",
#         primaryjoin="ComputedResultSelfRelation.computed_result1_id == ComputedResult.id",
#     )
#     computed_result2 = relationship(
#         "ComputedResult",
#         primaryjoin="ComputedResultSelfRelation.computed_result2_id == ComputedResult.id",
#     )


# class Die(SQLModel, table=True):
#     __tablename__ = "die"
#     __table_args__ = {"comment": "This table holds die definition."}

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     reticle_id = Column(ForeignKey("reticle.id"), nullable=False, index=True)
#     name = Column(String(200), nullable=False)
#     position = Column(String(50))
#     size = Column(String(50))
#     description = Column(String(200))

#     reticle = relationship("Reticle")


# class ResultComputedResultRelation(SQLModel, table=True):
#     __tablename__ = "result_computed_result_relation"
#     __table_args__ = {
#         "comment": "This table holds the relations in between the results and the computed results."
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     result_id = Column(ForeignKey("result.id"), nullable=False, index=True)
#     computed_result_id = Column(
#         ForeignKey("computed_result.id"), nullable=False, index=True
#     )

#     computed_result = relationship("ComputedResult")
#     result = relationship("Result")


# class ResultInfo(SQLModel, table=True):
#     __tablename__ = "result_info"
#     __table_args__ = {
#         "comment": "This table holds extra information about specific results."
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     name = Column(String(200), nullable=False)
#     value = Column(String(200), nullable=False)
#     result_id = Column(ForeignKey("result.id"), nullable=False, index=True)
#     computed_result_id = Column(
#         ForeignKey("computed_result.id"), nullable=False, index=True
#     )
#     unit_id = Column(ForeignKey("unit.id"), index=True)
#     description = Column(String(200))

#     computed_result = relationship("ComputedResult")
#     result = relationship("Result")
#     unit = relationship("Unit")


# class ResultProcessRelation(SQLModel, table=True):
#     __tablename__ = "result_process_relation"
#     __table_args__ = {
#         "comment": "This table holds all results and simulation result relation."
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     result_id = Column(ForeignKey("result.id"), nullable=False, index=True)
#     process_id = Column(ForeignKey("process.id"), nullable=False, index=True)

#     process = relationship("Process")
#     result = relationship("Result")


# class ResultSelfRelation(SQLModel, table=True):
#     __tablename__ = "result_self_relation"
#     __table_args__ = {
#         "comment": "This table holds all results self relation. This is used to link results together"
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     result1_id = Column(ForeignKey("result.id"), nullable=False, index=True)
#     result2_id = Column(ForeignKey("result.id"), nullable=False, index=True)

#     result1 = relationship(
#         "Result", primaryjoin="ResultSelfRelation.result1_id == Result.id"
#     )
#     result2 = relationship(
#         "Result", primaryjoin="ResultSelfRelation.result2_id == Result.id"
#     )


# class Component(SQLModel, table=True):
#     __tablename__ = "component"
#     __table_args__ = {"comment": "This table holds the definition of components."}

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     die_id = Column(ForeignKey("die.id"), nullable=False, index=True)
#     name = Column(String(250), nullable=False)
#     description = Column(String(200))

#     die = relationship("Die")


# class Port(SQLModel, table=True):
#     __tablename__ = "port"
#     __table_args__ = {"comment": "This table holds all ports definition."}

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     component_id = Column(ForeignKey("component.id"), nullable=False, index=True)
#     name = Column(String(200), server_default=text("''"))
#     port_type = Column(String(200))
#     position = Column(String(50), nullable=False)
#     orientation = Column(Float(asdecimal=True), nullable=False)
#     description = Column(String(200))

#     component = relationship("Component")


# class ComponentInfo(SQLModel, table=True):
#     __tablename__ = "component_info"
#     __table_args__ = {
#         "comment": "This table holds information for the component using name/value pairs with optional description."
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     component_id = Column(ForeignKey("component.id"), index=True)
#     die_id = Column(ForeignKey("die.id"), index=True)
#     port_id = Column(ForeignKey("port.id"), index=True)
#     reticle_id = Column(ForeignKey("reticle.id"), index=True)
#     wafer_id = Column(ForeignKey("wafer.id"), index=True)
#     name = Column(String(200), nullable=False)
#     value = Column(String(200), nullable=False)
#     description = Column(String(200))

#     component = relationship("Component")
#     die = relationship("Die")
#     port = relationship("Port")
#     reticle = relationship("Reticle")
#     wafer = relationship("Wafer")


# class ResultComponentRelation(SQLModel, table=True):
#     __tablename__ = "result_component_relation"
#     __table_args__ = {
#         "comment": "This table holds the relations in between results and components."
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     result_id = Column(ForeignKey("result.id"), nullable=False, index=True)
#     component_id = Column(ForeignKey("component.id"), index=True)
#     die_id = Column(ForeignKey("die.id"), index=True)
#     port_id = Column(ForeignKey("port.id"), index=True)
#     reticle_id = Column(ForeignKey("reticle.id"), index=True)
#     wafer_id = Column(ForeignKey("wafer.id"), index=True)

#     component = relationship("Component")
#     die = relationship("Die")
#     port = relationship("Port")
#     result = relationship("Result")
#     reticle = relationship("Reticle")
#     wafer = relationship("Wafer")


# class RelationInfo(SQLModel, table=True):
#     __tablename__ = "relation_info"
#     __table_args__ = {
#         "comment": "This table holds extra information about specific relation."
#     }

#     id = Column(Integer, primary_key=True)
#     created = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     updated = Column(
#         TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
#     )
#     computed_result_self_relation_id = Column(
#         ForeignKey("computed_result_self_relation.id"), index=True
#     )
#     result_self_relation_id = Column(ForeignKey("result_self_relation.id"), index=True)
#     result_process_relation_id = Column(
#         ForeignKey("result_process_relation.id"), index=True
#     )
#     result_component_relation_id = Column(
#         ForeignKey("result_component_relation.id"), index=True
#     )
#     result_computed_result_relation_id = Column(
#         ForeignKey("result_computed_result_relation.id"), index=True
#     )
#     name = Column(String(200), nullable=False)
#     value = Column(String(200), nullable=False)
#     description = Column(String(200))

#     computed_result_self_relation = relationship("ComputedResultSelfRelation")
#     result_component_relation = relationship("ResultComponentRelation")
#     result_computed_result_relation = relationship("ResultComputedResultRelation")
#     result_process_relation = relationship("ResultProcessRelation")
#     result_self_relation = relationship("ResultSelfRelation")


if __name__ == "__main__":
    from sqlmodel import Session, SQLModel, create_engine

    import gdsfactory as gf

    sqlite_file_name = "database.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"

    engine = create_engine(sqlite_url)

    def create_db_and_tables():
        SQLModel.metadata.create_all(engine)

    c = gf.c.ring_single(radius=10)

    with Session(engine) as session:

        w1 = Wafer(name="12", serial_number="ABC")
        # r1 = Reticle(name="sky1", wafer_id=w1.id, wafer=w1)
        # d1 = Die(name="d00", reticle_id=r1.id, reticle=r1)
        # c1 = Component(name=c.name, die_id=d1.id, die=d1)

        # component_settings = []

        # for key, value in c.settings.changed.items():
        #     s = ComponentInfo(component=c1, component_id=c1.id, name=key, value=value)
        #     component_settings.append(s)

        # for port in c.ports.values():
        #     s = Port(
        #         component=c1,
        #         component_id=c1.id,
        #         port_type=port.port_type,
        #         name=port.name,
        #         orientation=port.orientation,
        #         position=port.center,
        #     )
        #     component_settings.append(s)

        # session.add_all([w1, r1, d1, c1])
        # session.add_all(component_settings)
        session.add_all([w1])
        session.commit()
