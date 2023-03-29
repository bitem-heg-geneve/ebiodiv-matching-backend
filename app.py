from typing import Annotated
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from fastapi import FastAPI, Query, Body, Header

app = FastAPI(
    title="Backend mockup for ebiodiv",
    docs_url="/",
)

class BasisOfRecord(str, Enum):
    matcit = "matcit"
    specimen = "specimen"


class Ranking(str, Enum):
    date = "date"
    key = "key"
    scientificName = "scientificName"
    matching_number = Field("matching_number", description="rank by number of ")


class Occurrence(BaseModel):
    key: int
    basisOfRecord: str
    family: str
    genus: str
    specificEpithet: str
    decimalLatitude: str
    decimalLongitude: str
    elevation: int
    depth: int
    locality: str
    country: str
    day: int
    month: int
    year: int
    institutionCode: str
    collectionCode: str
    catalogNumber: str
    individualCount: int
    recordedBy: str
    typeStatus: str


class OccurrenceRelation(BaseModel):
    related_count: int = Field(description="Number of related occurrences")
    done_count: int = Field(description="Number of related occurrence already curated") 
    occurrence: Occurrence


class FacetValue(BaseModel):
    """Based on gbif.org API"""
    key: str
    title: str | None = Field(description="Name to display to the user, if null, the value is displayed")
    description: str | None = Field(default=None, description="Description for dataset for example")
    count: int


class Facet(BaseModel):
    name: str = Field(description="value for the /occurrences API")
    multi: bool = Field(description="can the user selects multiple value ?")
    complete: bool = Field(description="true is all the value are returned, false otherwise")
    values: list[FacetValue]


class OccurrenceResponse(BaseModel):
    occurrences: list[OccurrenceRelation]
    facets: list[Facet]


@app.get("/occurrences", summary="Simple list of occurrences with facet values", tags=['occurrences'])
def occurrences(
    q: Optional[str],
    basisOfRecord: BasisOfRecord,
    offset: int = 0,
    limit: int = 20,
    facet_limit: int = 20,
    ranking: Ranking = Ranking.date,
    year: int | None = None,
    datasetKey: str | None = None,
    curation_status: bool | None = Query(default=None, description="false to select occurrences that haven't been curated"),
    country: str | None = None,
    institutionCode: str | None = None,
    collectionCode: str | None = None,
    recordedBy: str | None = None,
    typeStatus: str | None = None,
    kingdom: str | None = None,
    phylum: str | None = None,
    clazz: str | None = Query(None, alias='class'),
    order: str | None = None,
    family: str | None = None,
    genus: str | None = None,
    species: str | None = None,
) -> OccurrenceResponse:
    return {
        "occurrences": [],
        "facets": []
    }


class OneRelatedOccurrence(BaseModel):
    occurrence: Occurrence
    decision: bool | None = Field(default=None, description="Can be null for undecided")


class RelatedOccurrenceResponse(BaseModel):
    subjectOccurrence: Occurrence
    related_occurrences: list[OneRelatedOccurrence]


@app.get("/occurrenceRelations", summary="Return one occurrence and its related occurrences with decisions", tags=['occurrences'])
def related_occurrence(
    occurrenceKeys: int
) -> RelatedOccurrenceResponse:
    return {

    }


@app.get("/nextOccurrenceRelations", 
    summary="Return the next occurrence",
    description="""same return type than /occurrenceRelations, 
                   same query parameter than /occurrences with the addition of occurrenceKey and without offset, limit and facet_limit.
                   Ranking is important to define the next occurrence""",
    tags=['occurrences']
)
def nextOccurrences(
    occurrenceKey: int,
    q: Optional[str],
    basisOfRecord: BasisOfRecord,
    ranking: Ranking = Ranking.date,
    year: int | None = None,
    datasetKey: str | None = None,
    curation_status: bool | None = Query(default=None, description="false to select occurrences that haven't been curated"),
    country: str | None = None,
    institutionCode: str | None = None,
    collectionCode: str | None = None,
    recordedBy: str | None = None,
    typeStatus: str | None = None,
    kingdom: str | None = None,
    phylum: str | None = None,
    clazz: str | None = Query(None, alias='class'),
    order: str | None = None,
    family: str | None = None,
    genus: str | None = None,
    species: str | None = None,
) -> RelatedOccurrenceResponse:
    return {
        "occurrences": [],
        "facets": []
    }


class OccurrenceRelation(BaseModel):
    occurrenceKey1: int
    occurrenceKey2: int
    decision: bool | None = Field(default=None, description="Can be null for undecided")


class OccurrenceRelations(BaseModel):
    occurrenceRelationList: list[OccurrenceRelation]


@app.post("/occurrenceRelations", tags=['occurrences'])
def post_new_occurrence_relations(
    # occurrence_relation: list[OccurrenceRelation],
    authorization: str = Header()
): 
    return {}


## Facets ##############################################################################

@app.get("/facets")
def facets(
    facetName: str | None = Query(default=None, description="Name of the field"),
    facetTitlePrefix: str | None = Query(default=None, description="Value typed by the user"),
    q: str | None = None,
    basisOfRecord: BasisOfRecord | None = None,
    facet_limit: int = 20,
    ranking: Ranking = Ranking.date,
    year: int | None = None,
    datasetKey: str | None = None,
    curation_status: bool | None = Query(default=None, description="false to select occurrences that haven't been curated"),
    country: str | None = None,
    institutionCode: str | None = None,
    collectionCode: str | None = None,
    recordedBy: str | None = None,
    typeStatus: str | None = None,
    kingdom: str | None = None,
    phylum: str | None = None,
    clazz: str | None = Query(None, alias='class'),
    order: str | None = None,
    family: str | None = None,
    genus: str | None = None,
    species: str | None = None,
):
    return {}

## Comments ############################################################################

class Comment(BaseModel):
    orcid: str
    timestamp: int
    text: str


@app.get("/comments", tags=["comments"])
def get_comments(
    occurrenceKeys: list[int] = Query()
) -> dict[str, list[Comment]]:
    return {}


@app.post("/comments", tags=["comments"])
def add_comment(
    occurrenceKey: int,
    comment: Comment = Body(),
    authorization: str = Header()
):
    return {}
