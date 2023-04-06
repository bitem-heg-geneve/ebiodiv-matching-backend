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
    matching_number = "matching_number" # rank by number of related occurrences


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
    done_count: int = Field(description="Number of related curated occurrence") 
    pndg_count: int = Field(description="Number of related uncurated occurrence") 
    occurrence: Occurrence


class FacetValue(BaseModel):
    """Based on gbif.org API"""
    key: str
    title: str | None = Field(description="Name to display to the user, if null, the value is displayed")
    description: str | None = Field(default=None, description="Description for dataset for example")
    count: int


class MultiFacetOneValue(BaseModel):
    facet: str
    key: str
    title: str | None = Field(description="Name to display to the user, if null, the value is displayed")


class MultiFacetValues(BaseModel):
    """Define the values of multiple facets.
    Use case : the user search for a scientific name, then each results define kingdom, phylum, order, family, genus
    Similar to what gbif.org has done, see for example https://www.gbif.org/occurrence/search?q=apis
    """
    values: list[MultiFacetOneValue]
    count: int


class Facet(BaseModel):
    name: str = Field(description="value for the /occurrences API")
    multi: bool = Field(description="can the user selects multiple value ?")
    complete: bool = Field(description="true is all the value are returned, false otherwise")
    values: list[FacetValue]


class OccurrenceResponse(BaseModel):
    occurrences: list[OccurrenceRelation]
    facets: list[Facet]


class OccurrenceFormat(str, Enum):
    subject = "subject"
    related = "related"


class RankOrder(str, Enum):
    asc = "asc"
    desc = "desc"


@app.get("/occurrences", summary="Simple list of occurrences with facet values", tags=['occurrences'])
def occurrences(
    # q, parameter for the initial search
    # see https://docs.google.com/presentation/d/19Qyi8Je1RCjTuX2iFBC4ljUNCV0bV361/edit#slide=id.p1
    q: Optional[str] = Query(description="search an unique value in all the fields"),
    format: OccurrenceFormat = Query(description="related to get the related occurrences of the selected occurrences"),
    offset: int = 0,
    limit: int = 20,
    ranking: Ranking = Ranking.date,
    rankOrder: RankOrder = Query(default=RankOrder.asc, description="ranking order, ascending (True) or descending (False)"),
    curation_status: bool | None = Query(default=None, description="false to select occurrences that haven't been curated"),

    ## occurrences
    basisOfRecord: BasisOfRecord = Query(),
    year: int | None = Query(default=None, description="year of the occurrence"),

    # based on https://tb.plazi.org/GbifOccLink/data/occurrences/search
    ## occurrences
    scientificName: str | None = Query(default=None, description="see respective DarwinCore term"),
    acceptedScientificName: str | None = Query(default=None, description="see respective DarwinCore term"),
    kingdom: str | None = Query(default=None, description="see respective DarwinCore term"),
    phylum: str | None = Query(default=None, description="see respective DarwinCore term"),
    clazz: str | None = Query(None, description="see respective DarwinCore term", alias='class'),
    order: str | None = Query(default=None, description="see respective DarwinCore term"),
    family: str | None = Query(default=None, description="see respective DarwinCore term"),
    genus: str | None = Query(default=None, description="see respective DarwinCore term"),
    specificEpithet: str | None = Query(default=None, description="see respective DarwinCore term"),
    infraspecificEpithet: str | None = Query(default=None, description="see respective DarwinCore term"),
    taxonRank: str | None = Query(default=None, description="see respective DarwinCore term"),
    country: str | None = Query(default=None, description="see respective DarwinCore term"),
    stateProvince: str | None = Query(default=None, description="see respective DarwinCore term"),
    typeStatus: str | None = Query(default=None, description="see respective DarwinCore term"),
    recordedBy: str | None = Query(default=None, description="see respective DarwinCore term"),
    institutionCode: str | None = Query(default=None, description="see respective DarwinCore term"),
    collectionCode: str | None = Query(default=None, description="see respective DarwinCore term"),

    # based on https://tb.plazi.org/GbifOccLink/data/datasets/search
    # however, this API returns occurrences NOT datasetKeys

    ## datasets
    datasetKey: str | None = Query(default=None, description="is it relevant?"),
    datasetTitle: str | None = Query(default=None, description="the title of the dataset proper, or the title of the source publication (the latter for materials citation datasets only"),
    datasetGbifDoi: str | None = Query(default=None, description="the gbifDoi of the dataset proper"),
    datasetSourceDoi: str | None = Query(default=None, description="the sourceDoi of the dataset proper"),
    datasetIdentifier: str | None = Query(default=None, description="the identifier of the dataset proper"),
    datasetCreator: str | None = Query(default=None, description="the creator of the dataset proper"),
    datasetCitation: str | None = Query(default=None, description="the citation of the dataset proper"),

    ## publications
    pubAuthor: str | None = Query(default=None, description="the author of the source publication (for materials citation datasets only"),
    pubDate: str | None = Query(default=None, description="the date the source publication was published (for materials citation datasets only"),
    pubYear: str | None = Query(default=None, description="the year the source publication was published (for materials citation datasets only"),
    pubJournal: str | None = Query(default = None, description="the journal of the source publication (for materials citation datasets only"),
    pubPublisher: str | None = Query(default=None, description="the publisher of the source publication (for materials citation datasets only"),
    pubVolume: str | None = Query(default=None, description="the volume number of the source publication (for materials citation datasets only"),
    pubIssue: str | None = Query(default=None, description="the issue number of the source publication (for materials citation datasets only"),
    pubNumero: str | None = Query(default=None, description="the numero of the source publication (for materials citation datasets only"),
    pubFirstPage: int | None = Query(default=None, description="the first page of the source publication (for materials citation datasets only"),
    pubLastPage: int | None = Query(default=None, description="the last page of the source publication (for materials citation datasets only"),
    pubDoi: str | None = Query(default=None, description="the DOI of the source publication (for materials citation datasets only"),
    pubZooBankId: str | None = Query(default=None, description="the ZooBank issued UUID of the source publication (for materials citation datasets only"),
    pubPlaziUuid: str | None = Query(default=None, description="the Plazi issued UUID of the source publication metadata (for materials citation datasets only")
) -> OccurrenceResponse:
    return {
        "occurrences": [],
        "facets": []
    }


class Decision(str, Enum):
    undecided = "undecided"
    no = "no"
    yes = "yes"


class StatusCode(str, Enum):
    DONE = "DONE" # Curated
    PNDG = "PNDG" # Uncurated
    UDCB = "UDCB" # Undecidable


class OneRelatedOccurrence(BaseModel):
    occurrence: Occurrence
    decision: Decision | None = None
    statusCode: StatusCode = StatusCode.PNDG


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


class NewOccurrenceRelation(BaseModel):
    occurrenceKey1: int
    occurrenceKey2: int
    decision: Decision
    userName: str
    orcid: str


class NewOccurrenceRelations(BaseModel):
    occurrenceRelationList: list[NewOccurrenceRelation]


@app.post("/occurrenceRelations", tags=['occurrences'])
def post_new_occurrence_relations(
    occurrence_relation: list[NewOccurrenceRelation] = Body(),
    # authorization: str = Header()
): 
    return {}


## Facets ##############################################################################

class FacetsResult(BaseModel):
    values: list[FacetValue]


@app.get("/facets", tags=["facets"])
def facets(
    facetName: str | None = Query(default=None, description="Name of the field"),
    facetTitlePrefix: str | None = Query(default=None, description="Value typed by the user"),
    q: str | None = None,
    basisOfRecord: BasisOfRecord | None = None,
    facet_limit: int = 20,
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
) -> FacetsResult:
    """https://tb.plazi.org/GbifOccLink/data/occurrences/searchFieldValues?field=phylum&phylum=A*&kingdom=Animalia"""
    return {}

## Comments ############################################################################

class Comment(BaseModel):
    orcid: str
    userName: str
    timestamp: int
    text: str


@app.get("/comments", tags=["comments"])
def get_comments(
    subjectOccurrenceKey: int = Query(),
    relatedOccurrenceKeys: list[int] = Query()
) -> dict[str, list[Comment]]:
    return {}


@app.post("/comments", tags=["comments"])
def add_comment(
    subjectOccurrenceKey: int,
    relatedOccurrenceKey: int,
    comment: Comment = Body(),
    authorization: str = Header()
):
    return {}
