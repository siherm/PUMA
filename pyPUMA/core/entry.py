import re

from pydantic import BaseModel, Field, validator, PrivateAttr
from typing import Union, List, Optional


class PUMAEntry(BaseModel):

    class Config:
        allow_population_by_field_name = True
        smart_union = True

    bibtex: dict = Field(
        ...,
        description="Raw bibtex file that can be utilized in later stages"
    )

    title: str = Field(
        ...,
        description="Title of the publication"
    )

    user: Union[str, dict] = Field(
        ...,
        description="User that has added the publication"
    )

    author: str = Field(
        ...,
        alias="author",
        description="Authors of the publication"
    )

    entrytype: str = Field(
        ...,
        description="Type of entry that is given in the PUMA entry"
    )

    group: str = Field(
        ...,
        description="PUMA group association of the entry"
    )

    tag: list = Field(
        default_factory=list,
        description="Tags the dataset has been assigned to"
    )

    journal: Optional[str] = Field(
        None,
        description="Journal in which the manuscript has been published"
    )

    preprint_id: Optional[dict] = Field(
        None,
        description="ID of the preprint as well as the server"
    )

    url: Optional[str] = Field(
        None,
        description="URL for various informations related to the publication"
    )

    doi: Optional[str] = Field(
        None,
        description="Digital Object Identifier of the publication"
    )

    isbn: Optional[str] = Field(
        None,
        description="ISBN of the book"
    )

    issn: Optional[str] = Field(
        None,
        description="ISSN of the book"
    )

    misc: Optional[str] = Field(
        None,
        description="Miscellaneous items, mainly used ot populate DOI and ISBN"
    )

    # * Private attributes
    _raw_data: dict = PrivateAttr()

    # ! Validators

    @validator("user")
    def fetch_username(cls, value: dict):
        """Parses a user dictionary and fetches the name"""
        return value["name"]

    @validator("tag", each_item=True, pre=True)
    def parse_tags(cls, tags: List[dict]):
        """Parses tag name dictionaries to strings"""
        return sorted([
            tag["name"] for tag in tags
        ])

    @validator("misc", always=True)
    def parse_misc(cls, misc: Optional[str], values: dict):
        """Uses the miscellaneous field to find DOIs"""

        if not misc:
            # DOI is already here
            return None

        if "doi = " in misc:
            # Use regular expression to fetch the DOI
            doi = cls._fetch_from_misc(misc.lower(), "doi")

            if doi:
                doi = doi[doi.find("10.")::]

                if doi.startswith("10."):
                    values["doi"] = doi

        if "issn = " in misc:
            values["issn"] = cls._fetch_from_misc(misc.lower(), "issn")

        if "isbn = " in misc:
            values["isbn"] = cls._fetch_from_misc(misc.lower(), "isbn")

        if "arxivid = " in misc:
            values["preprint_id"] = cls._fetch_from_misc(
                misc.lower(), "arxivid")

        return None

    @validator("url")
    def parse_url(cls, url: str, values: dict):
        """Parses url to get preprint info"""

        if not url:
            return None

        if "arxiv.org" in url:
            values["preprint_id"] = {
                "type": "arxiv",
                "id": url.split("/")[-1]
            }

        return url

    @validator("journal")
    def parse_journal(cls, journal: str, values: dict):
        """Extracts possible pre-prints from the journal"""

        if not journal:
            return None

        if "ArXiv e-print" in journal:
            values["preprint_id"] = {
                "type": "arxiv",
                "id": journal.split(" ")[-1]
            }

        return journal

    @staticmethod
    def _fetch_from_misc(misc: str, search_term: str):
        """Fetches any additional attribute in misc"""
        pattern = re.compile(f"{search_term} = " + r"{(.*?)}")

        try:
            return pattern.findall(misc)[0].strip("{}")
        except IndexError:
            return None

    # ! Initializers
    @classmethod
    def from_api_record(cls, api_record: dict, group: str = "SimTech"):
        """Initializes objects coming from an API fetch"""

        # Rearrange data for eeasy initialization
        api_record = {**api_record, **api_record["bibtex"]}
        api_record["group"] = group

        # Create class
        cls = cls(**api_record)
        cls._raw_data = api_record

        return cls

    @classmethod
    def from_multiple_entries(cls, entries: list, recursion: dict = {}):
        """Merges multiple entries to a single one

        This method is used to merge multiple entries to a single one in the
        duplicate analysis given within PyPUMA. It should be noted, that the
        static fields from the first entry will be preferred if not specified
        in the recursion dictionary. Fields that are lists will be added and
        duplicate values merged to a single.

        In order to apply preferences, a recursion dictionary can be given
        from which the fields value that matches will be used. For instance,
        if the entry_type attribute is mixed but specified as 'article' the
        latter will be used for the new entry. If no values apply to the
        recursion, the first will be used.


        Args:
          entries (list[PUMAEntry]): List of PUMAEntries that will be merged
          recursion (dict): Prefrences that will be used to merge.
        """

        # Initialize new parameter dict
        params = {}

        # Iterate through the data model
        for attr, annot in cls.__annotations__.items():
            if attr in ["bibtex", "_raw_data"]:
                # Skip raw data fields
                continue

            # Add up list entries
            if "list" in repr(annot):
                # Make values unique
                params[attr] = list({
                    value
                    for entry in entries
                    for value in entry.__dict__[attr]
                })
                continue

            # Get preferred value if specified
            if recursion.get(attr):
                params[attr] = cls._extract_value_by_preference(
                    key=attr, value=recursion[attr], entries=entries
                )
            else:
                params[attr] = entries[0].__dict__[attr]

        return cls.construct(**params)

    @staticmethod
    def _extract_value_by_preference(key, value, entries: list):
        """Uses a recursion dictionary to find the fitting value"""

        for entry in entries:
            if entry.__dict__.get(key) == value:
                return entry.__dict__.get(key)

        return entries[0].__dict_.get(key)

    # ! ReDefs

    def json(self, indent=2, **kwargs):
        return super().json(
            exclude={"bibtex", "_raw_data"},
            indent=indent,
            **kwargs
        )
