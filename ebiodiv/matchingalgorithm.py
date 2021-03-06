"""
Matching algorithm between two occurrences.

For reference:
* description of GBIF fields: https://www.gbif.org/data-quality-requirements-occurrences
* descritpion of GBIF issues: https://gbif.github.io/parsers/apidocs/org/gbif/api/vocabulary/OccurrenceIssue.html
"""
import decimal
import math
import datetime
import re
from typing import Optional, Tuple, List, Dict, FrozenSet
from collections import namedtuple

import jaro
import numpy as np
import numpy.ma as ma


"""Normalization of the occurrences"""

RE_NOT_ALPHANUM = re.compile(r"[^A-Z0-9]+")


def normalize_str(value: Optional[str]) -> str:
    return value.strip() if value else ""


def normalize_str_alphanum(value: Optional[str]) -> str:
    """
    * "I.42891-001" and "I 42891 - 001" becomes "I42891001" (without spaces).
    * "KS.43690" and "KS46553" becomes "KS46553" (occurrences 1100114000 and 3066982498)

    Drawback: "KS13" and "40.KS,13.KS" are going to match in get_score_string_exact_or_include
    """
    value = normalize_str(value).upper()
    return RE_NOT_ALPHANUM.sub("", value)


def normalize_str_or_none(value: Optional[str]) -> Optional[str]:
    return value.strip() if value else value


def normalize_int(value) -> Optional[int]:
    return int(value) if value else None


def normalize_elevationdepth(elevation, depth) -> Tuple[Optional[float], Optional[float]]:
    """
    Normalize elevation and depth.
    Also (see the comments below for the details):
    elevation = -depth if elevation is None else elevation

    elevationAccuracy and depthAccuracy are ignored.
    """
    # elevation
    if isinstance(elevation, str):
        # it seems the elevation is never a string
        elevation = elevation.replace("ca.", "")
    if elevation is not None:
        elevation = float(elevation)
        if elevation < -6000000:
            elevation = None
    # depth
    if depth is not None:
        depth = float(depth)

    """
    Basically: elevation = -depth if elevation is None else elevation
    But that elevation and depth can be both defined
    """
    if depth == elevation:
        """
        see occurrences:
        * 1418672649 ( elevation = depth = elevationAccuracy = depthAccuracy = 0.5 )
        * 3059210941 ( elevation = depth = 354 )

        Should be declared as invalid ?
        """
        return elevation, depth

    if (depth is not None) and ((elevation is None) or (depth != 0 and elevation == 0)):
        """elevation is either None or zero (while depth is not)"""
        elevation = -depth
    return elevation, depth


def normalize_yearmonthday(year, month, day) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    year = int(year) if year else None
    month = int(month) if year and month else None
    day = int(day) if year and month and day else None
    return year, month, day


def normalize_latlon(lat, long) -> Tuple[Optional[float], Optional[float]]:
    if not long or not lat:
        return None, None
    long = float(long)
    lat = float(lat)
    if (long == 0 and lat == 0) or (long == 360 and lat == 360):
        return None, None
    return long, lat


def normalize_recordedbyids(recordedbyids: Optional[List[Dict[str, str]]]) -> FrozenSet[str]:
    """Dict[str, str] : there are two keys: "type" and "value".
    """
    if recordedbyids is None:
        return frozenset()

    return frozenset({
        v["value"]  # ignore "type"
        for v in recordedbyids
    })


def normalize_occurrence(occurrence):
    for field_name, field_desc in FIELDS.items():
        occurrence[field_name] = field_desc.normalize(occurrence.get(field_name))

    for field_names, field_desc in MULTI_FIELDS.items():
        result = field_desc.normalize(*[occurrence.get(field_name) for field_name in field_names])
        for i, field_name in enumerate(field_names):
            occurrence[field_name] = result[i]


"""Scoring of the occurrences"""


def get_score_string_jw(subject_value, related_value):
    if subject_value is None or related_value is None or subject_value == "" or related_value == "":
        return np.nan
    return jaro.jaro_winkler_metric(subject_value, related_value)


def get_score_string_exact(subject_value, related_value):
    if subject_value == "" or related_value == "":
        return np.nan
    return 1 if related_value.upper() == subject_value.upper() else 0


def get_score_string_exact_or_include(subject_value, related_value):
    """
    occurrence 1804360418: catalog number = "CMNA 2015-0001"
    occurrence 2871638302: catalog number = "CMNA 2015-0001, CMNA 2015-0004, CMNA 2015-0011, CMNA 2015-0015, CMNA 2015-0017"

    the values are normalized as (by normalize_str_alphanum):
    "CMNA 2015 0001"
    and "CMNA 2015 0001 CMNA 2015 0004 CMNA 2015 0011 CMNA 2015 0015 CMNA 2015 0017"

    this scoring function returns 0.8 for these two occurrences.

    Note: in case of "RUSI 6139 (previously ORI 1482 (erroneously listed as ORI 1485 in the RUSI database ))"
    and "ORI 1485" the score is going to be 0.8 too.
    """
    if subject_value == "" or related_value == "":
        return np.nan
    subject_value = subject_value.upper()
    related_value = related_value.upper()
    if subject_value == related_value:
        return 1
    if subject_value in related_value or related_value in subject_value:
        return 0.8
    return 0


def get_score_numeric(subject_value, related_value):
    candidates = [related_value]
    value_for_max = [c for c in candidates if c is not None]
    if subject_value:
        value_for_max.append(subject_value)

    if len(value_for_max) == 0 or subject_value is None:
        result = [np.nan] * len(candidates)
    else:
        max_value = abs(max(value_for_max))

        if max_value == 0:
            # all values are either 0 or None
            return [1 if candidate is not None else None for candidate in candidates]

        result = [1 - (abs(candidate - subject_value) / max_value) if candidate is not None else np.nan for candidate in candidates]
    return result[0]


def get_score_recordedbyids(subject_value: FrozenSet[str], related_value: FrozenSet[str]) -> float:
    """If at least one identifier match, then the score is 1
    otherwise the score 0
    """
    return 1 if len(subject_value.intersection(related_value)) > 0 else 0


def get_occurrence_date(occ):
    """Return the number of day since 1/1/0.
    * If the month is not defined then it is replaced by 6
    * If the day is not defnied then it is replaced by 15

    Return None if year is not defined
    """
    if occ["year"]:
        dt = datetime.date(occ["year"], occ["month"] or 6, occ["day"] or 15)
        return dt.toordinal()
    return None


def get_score_yearmonthday(subject_occ, related_occ):
    subject_date = get_occurrence_date(subject_occ)
    related_date = get_occurrence_date(related_occ)
    if subject_date and related_date:
        """
        The current scoring takes into account the date difference, nothing more.
        350 in math.exp(...) is adjusted to have:
        * a 1 day distance returns a score of 0.90
        * a 7 days distance returns a score of 0.49
        * a 15 days distance returns a score of 0.22

        It may require some adjustments after a review of confirmed matched occurrences.

        Possible errors (ignored in this implementation):
        * A typo about "22/5/2022" can transform in "2/5/2022" or "22/8/2022" or "22/5/2012".
        * A date format misunderstanding can transform in "2/5/2022" to "5/2/2022".
        * If the day is missing "22/5/2022" becomes "5/2022". The current scoring seen "5/2022" as "1/5/2022".
        """
        return math.exp(-abs(subject_date - related_date) / 10)
    return np.nan


def get_score_latlon(subject_occ, related_occ):
    """
    use the Haversine formula
    https://en.wikipedia.org/wiki/Haversine_formula
    """
    lat_1, lng_1 = subject_occ["decimalLatitude"], subject_occ["decimalLongitude"]
    lat_2, lng_2 = related_occ["decimalLatitude"], related_occ["decimalLongitude"]

    if not (lat_1 and lng_1 and lat_2 and lng_2):
        return np.nan

    # use decimal.Decimal to avoid rounding problem
    lng_1, lat_1, lng_2, lat_2 = map(decimal.Decimal, [lng_1, lat_1, lng_2, lat_2])

    # decimal to radians
    # note: may be not required if math.sin are in replaced by math.cos in h = .... below
    lng_1, lat_1, lng_2, lat_2 = map(math.radians, [lng_1, lat_1, lng_2, lat_2])

    try:
        d_lat = lat_2 - lat_1
        d_lng = lng_2 - lng_1
        h = math.sin(d_lat / 2) ** 2 + math.cos(lat_1) * math.cos(lat_2) * math.sin(d_lng / 2) ** 2
        """
        distance from 0 to 1 (0 = same location, 1 = at the opposite side of the globe)
        notes:
        * not used here : distance_in_kilometer = distance * 6378.0 * 2 # diameter of Earth
        * math.asin(math.sqrt(h)) as an alternative form using math.atan2 which might
          be better when the arc cross a pole.
        """
        distance = math.asin(math.sqrt(h))
        # score from 1 to 0 (1 = same location, ~0 = 100km away)
        return float(math.exp(-100 * distance))
    except decimal.DecimalException:
        # may hide an error
        return np.nan


def get_score_elevationdepth(subject_occ, related_occ):
    """normalize_elevationdepth makes sure the elevation contains the revelant value
    so we can safely ignore the depth field  
    """
    return get_score_numeric(subject_occ['elevation'], related_occ['elevation'])


def get_scores(subject_occ, related_occ):
    # row: field, column: occurrences
    score_values = []
    labels = []
    weights = []

    #
    for field_name, field_desc in FIELDS.items():
        subject_value = subject_occ[field_name]
        related_value = related_occ[field_name]
        score_values.append([field_desc.get_score(subject_value, related_value)])
        labels.append(field_name)
        weights.append(field_desc.score_weight)

    for field_names, field_desc in MULTI_FIELDS.items():
        score_values.append([field_desc.get_score(subject_occ, related_occ)])
        labels.append(field_names[0])
        weights.append(field_desc.score_weight)

    score_array = np.array(score_values)
    # calculate the global score = weight average
    # use masked_invalid to use ma.average with some np.nan in score_array
    score_average = ma.average(ma.masked_invalid(score_array), axis=0, weights=weights)
    # add score to the array
    labels.append("$global")
    score_array = np.append(score_array, [score_average], axis=0)
    #
    score_array = np.around(score_array, decimals=3)

    # iterate over occurrences using score_array.transpose()
    result = []
    for row in score_array.transpose():
        result.append({key: None if np.isnan(value) else value for key, value in zip(labels, row.tolist())})
    return result[0]


# matching algorithm: which columns
FieldDescription = namedtuple("FieldDescription", ["score_weight", "normalize", "get_score"])

FIELDS = {
    "typeStatus": FieldDescription(2, normalize_str, get_score_string_exact),
    "basisOfRecord": FieldDescription(2, normalize_str, get_score_string_exact),
    "basisOfRecord": FieldDescription(2, normalize_str, get_score_string_exact),
    "recordedBy": FieldDescription(2, normalize_str, get_score_string_jw),
    "recordNumber": FieldDescription(2, normalize_str, get_score_string_exact),
    "recordedByIDs": FieldDescription(2, normalize_recordedbyids, get_score_recordedbyids),
    "collectionCode": FieldDescription(2, normalize_str_alphanum, get_score_string_exact_or_include),
    "catalogNumber": FieldDescription(2, normalize_str_alphanum, get_score_string_exact_or_include),
    "individualCount": FieldDescription(1, normalize_int, get_score_numeric),
    "family": FieldDescription(1, normalize_str, get_score_string_jw),
    "genus": FieldDescription(1, normalize_str, get_score_string_jw),
    "specificEpithet": FieldDescription(1, normalize_str, get_score_string_jw),
    "country": FieldDescription(1, normalize_str, get_score_string_exact),  # the value is normalized by GBIF, there is no typo
    "city": FieldDescription(1, normalize_str_or_none, get_score_string_jw),
    "locality": FieldDescription(0.5, normalize_str_or_none, get_score_string_jw),
}

MULTI_FIELDS = {
    ("elevation", "depth"): FieldDescription(1, normalize_elevationdepth, get_score_elevationdepth),
    ("year", "month", "day"): FieldDescription(1, normalize_yearmonthday, get_score_yearmonthday),
    ("decimalLatitude", "decimalLongitude"): FieldDescription(2, normalize_latlon, get_score_latlon),
}
