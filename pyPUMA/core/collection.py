import pandas as pd
import requests

from pydantic import BaseModel, Field
from typing import List, Dict

from pyPUMA.core.entry import PUMAEntry


class PUMACollection(BaseModel):
    """
    Collection of PUMAEntry classes as well as functionalities to perform
    analysis and data export.
    """

    records: List[PUMAEntry] = Field(
        default_factory=list,
        description="Collection of PUMA entries"
    )

    # ! Initializers
    @classmethod
    def from_web_api(
        cls,
        username: str,
        token: str,
        collection_type: str = "user",
        start: int = 0,
        end: int = 10000
    ):
        """Initializes a PUMA collection using the REST API"""

        # Initialize object
        cls = cls()

        # Get all entries
        records = cls._fetch_from_remote(
            username, token, collection_type, start, end
        )

        # Iterate through entries as convert to objects
        for record in records:
            cls.records.append(
                PUMAEntry.from_api_record(record)
            )

        return cls

    @staticmethod
    def _fetch_from_remote(
        username: str,
        token: str,
        collection_type: str = "user",
        start: int = 0,
        end: int = 10000
    ):
        """Returns a list of all posts present in the SimTech group

        Args:

            username (str): Username that is used to evaluate rights. Usually the profile name of your PUMA account.
            token (str): Token required to grant access to functionalities found in Bibsonomy.
            collection_type (str): From which type of collection to fetch the data. Defaults to 'user'
            start (int): From which data entry to strat. Defaults to 0.
            end (int): Index to the last entry that will be fetched. Defaults to 10000.

        Returns:

            list[dict]: All posts as a list of ditionary that include metadata to PUMA specifics and the corresponding bibtex as dict.
        """
        return requests.get(
            f"https://puma.ub.uni-stuttgart.de/api/posts?{collection_type}=simtech&resourcetype=bibtex&start={start}&end={end}&format=json",
            auth=(username, token)
        ).json()["posts"]["post"]

    # ! Utilities
    def gather_duplicates(self, criteria: str) -> Dict[str, list]:
        """Collects duplicates based on a criteria.

        Args:
          criteria (str): Name of the attribute from which duplicates should be found.

        Returns:
            Dict[str, list]: Collection that is keyed by the criteria to a list of the duplicates.
        """

        # Get criteria from all entries
        criteria_values = set([
            entry.__dict__.get(criteria)
            for entry in self.records
            if entry.__dict__.get(criteria)
        ])

        # Initialize data strcuture with all duplicates
        duplicates = {}

        for value in criteria_values:
            filtered = list(filter(
                lambda record: record.__dict__.get(criteria) == value,
                self.records
            ))

            if len(filtered) > 1:
                duplicates[value] = filtered

        return duplicates

    # ! Exports
    def to_dataframe(self):
        """Turns the given collection into a Pandas DataFrame for further analysis"""

        data = [record.dict(exclude={"_raw_data", "bibtex"})
                for record in self.records]

        return pd.DataFrame(data)

    def __iter__(self):
        return iter(self.records)
