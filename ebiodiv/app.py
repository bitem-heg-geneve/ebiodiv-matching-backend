import logging
import hashlib
import orjson
from typing import Dict, List, Optional, Any

from fastapi import Body, FastAPI, Request, Query, Depends
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from . import server, storage

logger = logging.getLogger(__name__)

CONFIG = server.CONFIG


app = FastAPI(
    title="eBioDiv - SIB server",
    version="3.0.0",
    docs_url="/",
    redoc_url=None,
    default_response_class=ORJSONResponse,
    swagger_ui_parameters={"syntaxHighlight": False},
    description="""
<p>Store occurrence relations of ebiodiv.org</p>

<p><a href='https://github.com/bitem-heg-geneve/ebiodiv-matching-backend'>Source code</a></p>
""",
)


# Dependency
def get_db() -> storage.Session:
    db = storage.getSession()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    storage.initialize(CONFIG['database']['url'])


async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Exception")
        return ORJSONResponse(
            status_code=500,
            content={
                "error": exc.__class__.__module__ + "." + exc.__class__.__name__,
                "url": str(request.url),
                "args": exc.args,
            },
        )


app.middleware("http")(catch_exceptions_middleware)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

server.configure_app(app)


class OcurrenceRelation(BaseModel):
    occurrence: Dict[str, Any]
    decision: Optional[bool]
    is_new_decision: bool


class User(BaseModel):
    name: str
    orcid: Optional[str]


class OccurrenceRelationsModel(BaseModel):
    institutionKey: str 
    datasetKey:str
    user: User
    refOccurrence: Dict[str, Any]
    relations: List[OcurrenceRelation]


def get_user(session: storage.Session, user: User) -> storage.User:
    userObj = session.query(storage.User).where(storage.User.name==user.name and storage.User.orcid==user.orcid).scalar()
    if userObj is None:
        userObj = storage.User(name=user.name, orcid=user.orcid)
        session.add(userObj)
        session.commit()
    return userObj


def get_hash(b: bytes):
    m = hashlib.sha256()
    m.update(b)
    return m.hexdigest()


def get_occurrence(session: storage.Session, occurrence: Dict[str, Any]) -> storage.Occurrence:
    key = occurrence['key']
    data = orjson.dumps(occurrence)
    dataHash = get_hash(data)
    occurrenceObj = session.query(storage.Occurrence).where(storage.Occurrence.dataHash==dataHash).scalar()
    if occurrenceObj is None:
        occurrenceObj = storage.Occurrence(
            gbifKey=key,
            datasetKey=occurrence.get('datasetKey'),
            institutionKey=occurrence.get('institutionKey'),
            publishingOrgKey=occurrence.get('publishingOrgKey'),
            data=data.decode(),
            dataHash=dataHash,
        )
        session.add(occurrenceObj)
        session.commit()
    return occurrenceObj


@app.post("/newOcurrenceRelations")
async def occurrenceRelations(data: OccurrenceRelationsModel, session: storage.Session = Depends(get_db)):
    user = get_user(session, data.user)
    relationsObj = [
        storage.OccurrenceRelation(
            relatedOccurrenceId=get_occurrence(session, relation.occurrence).id,
            decision=relation.decision,
            isNewDecision=relation.is_new_decision,
        )
        for relation in data.relations
    ]

    # commit the event
    session.add(storage.Event(
        userId=user.id,
        institutionKey=data.institutionKey,
        datasetKey=data.datasetKey,
        refOccurrenceId=get_occurrence(session, data.refOccurrence).id,
        relations=relationsObj,
    ))
    session.commit()
    return {'ok': True}


@app.post('/occurrences')
async def occurrences(
    occurrenceIds: Optional[List[int]],
    session: storage.Session = Depends(get_db)
):
    occurrences = {}
    r = session.query(storage.Occurrence).where(storage.Occurrence.id.in_(occurrenceIds)).all()
    for occ in r:
        occ: storage.Occurrence = occ
        occurrences[occ.id] = orjson.loads(occ.data)
    return occurrences


@app.get("/occurrenceRelations")
async def events(
    institutionKey: Optional[str] = None,
    datasetKey: Optional[str] = None,
    occurrenceKey: Optional[int] = None,
    eventId: Optional[int] = None,
    withOccurrence: bool = False,
    session: storage.Session = Depends(get_db)
):
    q = session.query(storage.Event).join(storage.User, storage.User.id==storage.Event.userId).join(storage.Occurrence, storage.Occurrence.id==storage.Event.refOccurrenceId)
    if institutionKey:
        q = q.where(storage.Occurrence.institutionKey == institutionKey)
    if datasetKey:
        q = q.where(storage.Occurrence.datasetKey == datasetKey)
    if occurrenceKey:
        q = q.where(storage.Occurrence.gbifKey == occurrenceKey)
    if eventId:
        q = q.where(storage.Event.id == eventId)
    events = []

    occurrenceIdSet = set()
    def addToOccurrenceIdSet(occId):
        nonlocal occurrenceIdSet
        if withOccurrence:
            occurrenceIdSet.add(occId)
        return occId

    events = [
        {
            'id': event.id,
            'timestamp': event.timestamp,
            'user': {
                'name': event.user.name,
                'orcid': event.user.orcid, 
            },
            'refOccurrenceId': addToOccurrenceIdSet(event.refOccurrenceId),
            'refOccurrenceKey': event.refOccurrence.gbifKey,
            'datasetKey': event.refOccurrence.datasetKey,
            'institutionKey': event.refOccurrence.institutionKey,
            'publishingOrgKey': event.refOccurrence.publishingOrgKey,
            'relations': [
                {
                    'relatedOccurrenceId': addToOccurrenceIdSet(r.relatedOccurrenceId),
                    'decision': r.decision,
                    'is_new_decision': r.isNewDecision,
                }
                for r in event.relations
            ]
        }
        for event in q.all()
    ]
    results = {
        'events': events
    }

    if withOccurrence:
        occurrences = {}
        r = session.query(storage.Occurrence).where(storage.Occurrence.id.in_(occurrenceIdSet)).all()
        for occ in r:
            occ: storage.Occurrence = occ
            occurrences[occ.id] = orjson.loads(occ.data)
        results['occurrences'] = occurrences

    return results
