from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy import Column, String, Text, Integer, Time, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(250))
    orcid = Column(String(250))

    def __repr__(self):
        return f"<User id={self.id!r}, name={self.name!r} orcid={self.orcid!r}>"


class Occurrence(Base):
    __tablename__ = "occurrences"
    id = Column(Integer, primary_key=True, index=True)
    gbifKey = Column(Integer, index=True)
    datasetKey = Column(String(36))
    institutionKey = Column(String(36))
    publishingOrgKey = Column(String(36))
    data = Column(JSON, index=True)
    dataHash = Column(String(64), index=True)
    timestamp = Column(Integer, server_default=func.now())

    def __repr__(self):
        return f"<Occurrence id={self.id!r}, gbifKey={self.gbifKey!r} datasetKey={self.datasetKey!r} institutionKey={self.institutionKey!r}>"


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    refOccurrenceId = Column(Integer, ForeignKey('occurrences.id'))
    refOccurrence = relationship("Occurrence")
    datasetKey = Column(String(36))
    institutionKey = Column(String(36))
    userId = Column(Integer, ForeignKey('users.id'))
    user = relationship("User")
    relations = relationship("OccurrenceRelation", cascade="all, delete-orphan")
    timestamp = Column(Integer, server_default=func.now())

    def __repr__(self):
        return f"<Event id={self.id!r}, refOccurrenceId={self.refOccurrenceId!r} user={self.userId!r} timestamp={self.timestamp!r} relations={self.relations!r}>"


class OccurrenceRelation(Base):
    __tablename__ = "occurrenceRelations"
    eventid = Column(Integer, ForeignKey('events.id'), primary_key=True, index=True)
    relatedOccurrenceId = Column(Integer, ForeignKey('occurrences.id'), primary_key=True)
    decision = Column(Boolean)
    isNewDecision = Column(Boolean)

    def __repr__(self):
        return f"<OccurrenceRelation eventid={self.eventid!r} relatedOccurrenceId={self.relatedOccurrenceId!r} decision={self.decision!r} isNewDecision={self.isNewDecision!r}>"


_SessionLocal = None


def getSession() -> Session:
    if _SessionLocal is None:
        raise Exception('Call storage.initialize before')
    return _SessionLocal()


def initialize(url):
    global _SessionLocal
    # check_same_thread only for sqlite :
    # https://fastapi.tiangolo.com/tutorial/sql-databases/?h=session#note
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def schema_graph_write():
    from sqlalchemy import MetaData
    from sqlalchemy_schemadisplay import create_schema_graph
    from . import server

    database_url = server.CONFIG['database']['url']
    initialize(server.CONFIG['database']['url'])

    # create the pydot graph object by autoloading all tables via a bound metadata object
    graph = create_schema_graph(metadata=MetaData(database_url),
        show_datatypes=True, # The image would get nasty big if we'd show the datatypes
        show_indexes=True, # ditto for indexes
        concentrate=False # Don't try to join the relation lines together
    )
    graph.write_png('dbschema.png')


if __name__ == '__main__':
    schema_graph_write()
