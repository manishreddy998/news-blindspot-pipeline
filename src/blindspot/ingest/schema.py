"""Column layouts for the GDELT 2.0 Events and Mentions export files.

The files have no header row, so order matters. Taken from the GDELT 2.0
Event and Mentions codebooks.
"""

def _actor(prefix: str) -> list[tuple[str, str]]:
    cols = ["Code", "Name", "CountryCode", "KnownGroupCode", "EthnicCode",
            "Religion1Code", "Religion2Code", "Type1Code", "Type2Code", "Type3Code"]
    return [(f"{prefix}{c}", "STRING") for c in cols]


def _geo(prefix: str) -> list[tuple[str, str]]:
    return [
        (f"{prefix}_Type", "INT64"),
        (f"{prefix}_FullName", "STRING"),
        (f"{prefix}_CountryCode", "STRING"),
        (f"{prefix}_ADM1Code", "STRING"),
        (f"{prefix}_ADM2Code", "STRING"),
        (f"{prefix}_Lat", "FLOAT64"),
        (f"{prefix}_Long", "FLOAT64"),
        (f"{prefix}_FeatureID", "STRING"),
    ]


EVENTS = [
    ("GlobalEventID", "INT64"),
    ("Day", "INT64"),
    ("MonthYear", "INT64"),
    ("Year", "INT64"),
    ("FractionDate", "FLOAT64"),
    *_actor("Actor1"),
    *_actor("Actor2"),
    ("IsRootEvent", "INT64"),
    ("EventCode", "STRING"),  # kept as text: codes like "010" lose meaning as ints
    ("EventBaseCode", "STRING"),
    ("EventRootCode", "STRING"),
    ("QuadClass", "INT64"),
    ("GoldsteinScale", "FLOAT64"),
    ("NumMentions", "INT64"),
    ("NumSources", "INT64"),
    ("NumArticles", "INT64"),
    ("AvgTone", "FLOAT64"),
    *_geo("Actor1Geo"),
    *_geo("Actor2Geo"),
    *_geo("ActionGeo"),
    ("DateAdded", "INT64"),  # YYYYMMDDHHMMSS, UTC
    ("SourceURL", "STRING"),
]

MENTIONS = [
    ("GlobalEventID", "INT64"),
    ("EventTimeDate", "INT64"),
    ("MentionTimeDate", "INT64"),
    ("MentionType", "INT64"),
    ("MentionSourceName", "STRING"),
    ("MentionIdentifier", "STRING"),  # article URL for web sources
    ("SentenceID", "INT64"),
    ("Actor1CharOffset", "INT64"),
    ("Actor2CharOffset", "INT64"),
    ("ActionCharOffset", "INT64"),
    ("InRawText", "INT64"),
    ("Confidence", "INT64"),
    ("MentionDocLen", "INT64"),
    ("MentionDocTone", "FLOAT64"),
    ("MentionDocTranslationInfo", "STRING"),
    ("Extras", "STRING"),
]

# Every raw table also records which file a row came from, for reloads and lineage.
LINEAGE = [("source_file", "STRING")]

TABLES = {
    "export": ("raw_gdelt_events", EVENTS),
    "mentions": ("raw_gdelt_mentions", MENTIONS),
}

assert len(EVENTS) == 61 and len(MENTIONS) == 16

DUCKDB_TYPES = {"INT64": "BIGINT", "FLOAT64": "DOUBLE", "STRING": "VARCHAR"}
