import asyncio
import logging
import os
import sys
from abc import ABC, abstractmethod

import numpy as np
import scipy.stats as stats

sys.path.append(os.getcwd())

from datetime import datetime
from typing import Dict, List

from azure.core import exceptions as azure_exceptions
from azure.cosmos.aio import CosmosClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
logging.getLogger("azure").setLevel(logging.WARNING)


class AnalysisFactory(ABC):
    """Abstract factory class defining the factory method to create analysis (product)."""

    @abstractmethod
    def create_analysis(self):
        pass


class ConcreteAnalysisFactory(AnalysisFactory):
    """Concrete factory for creating ScoreTranscriptionsAnalysis objects."""

    def create_analysis(self):
        return ScoreTranscriptionsAnalysis()


class Analysis(ABC):
    """Defines the interface for all analysis products."""

    @abstractmethod
    def extract_date_from_filename(self, filename: str):
        pass

    @abstractmethod
    async def calculates_score(self, call_ids: list, scores: list, round_score_decimal: int = 2):
        pass

    @abstractmethod
    async def gets_specific_data(self, specialist_name: str):
        pass


class ScoreTranscriptionsAnalysis(Analysis):

    def __init__(self):
        self.cosmos_endpoint = os.getenv("COSMOS_ENDPOINT", "")
        self.cosmos_key = os.getenv("COSMOS_KEY", "")
        self.data_base_name = "db_transcriptions"

    async def extract_date_from_filename(self, filename: str) -> datetime:
        """
        Extracts a date from a filename and converts it into a datetime object.

        The function assumes the filename contains a date in the format 'YYYYMMDDHHMMSS'
        starting from the 6th character (index 5) up to the 20th character (index 19),
        and that the filename is a text file with a '.txt' extension.

        Args:
            filename (str): The path to the file, including its name and extension.

        Returns:
            datetime.datetime or None: The extracted date as a datetime object if
            the year is 2024 or later; otherwise, None. If any errors occur during
            parsing, None is returned and an error message is printed.

        Examples:
            >>> extract_date_from_filename('/path/to/file_20230914123045.txt')
            datetime.datetime(2023, 9, 14, 12, 30, 45)

            >>> extract_date_from_filename('/path/to/file_19991231235959.txt')
            Error parsing date from /path/to/file_19991231235959.txt: not a valid year: 1999
            None
        """
        try:
            # Extracting the part that contains the date (after the initial code)
            date_str = filename.split("/")[-1].replace(".txt", "")[5:19]
            # Convert to datetime
            date = datetime.strptime(date_str, "%Y%m%d%H%M%S")

            year = int(date_str[:4])

            # Check if the year is 2024 or later
            if year < 2024:
                logging.error(f"Error parsing date from {filename}: not a valid year: {year}")
                return None

            return date
        except Exception as e:
            logging.error(f"Error parsing date from {filename}: {e}")
            return None

    async def calculates_score(
        self, call_ids: list, scores: list, round_score_decimal: int = 2
    ) -> dict:
        """
        Asynchronously calculates Z-scores for a given list of scores, returning a dictionary mapping call IDs to their respective Z-scores.

        The Z-score indicates how many standard deviations a given score is from the mean of the score distribution.
        The Z-scores are rounded to the specified number of decimal places.

        Args:
            call_ids (list): A list of unique identifiers (call IDs) corresponding to the transcriptions.
            scores (list): A list of scores (floats or ints) corresponding to the call IDs, for which the Z-scores will be calculated.
            round_score_decimal (int, optional): The number of decimal places to round each Z-score to. Default is 2.

        Returns:
            dict: A dictionary where the keys are `call_ids` and the values are the calculated Z-scores for the corresponding scores.

        Raises:
            ValueError: If the length of `call_ids` does not match the length of `scores`.

        Example:
            >>> call_ids = [1, 2, 3]
            >>> scores = [85, 90, 75]
            >>> zscore_dict = await calculates_score(call_ids, scores)
            >>> print(zscore_dict)
            {1: 0.39, 2: 1.23, 3: -1.62}
        """

        # Ensure call_ids and scores lists are the same length
        if len(call_ids) != len(scores):
            raise ValueError("The length of call_ids must match the length of scores.")

        # Convert the scores list to a numpy array for efficient calculations
        scores_arr = np.array(scores)

        # Calculate the mean and standard deviation of the scores
        mean = np.mean(scores_arr)
        std_score = np.std(scores_arr)

        # Calculate Z-scores
        z_score_arr = (scores_arr - mean) / std_score

        # Round Z-scores to the specified number of decimal places
        z_score_arr = [round(float(z), round_score_decimal) for z in z_score_arr]

        # Create a dictionary mapping call IDs to Z-scores
        id_score_dict = dict(zip(call_ids, z_score_arr))

        return id_score_dict

    async def run_hypothesis_test_zscore_mean(self, call_ids: list, scores: list) -> dict:
        """
        Calculates the Z-score for each unique call ID and assesses whether the score significantly
        differs from the sample mean using a two-tailed Z-test.

        This function compares the score of each unique call ID to the mean of all scores in the
        dataset and determines if the difference is statistically significant at the 5% significance level.

        Args:
            call_ids (list): A list of call IDs corresponding to each score.
            scores (list): A list of numerical scores associated with the call IDs and dates.

        Returns:
            dict: A dictionary where the keys are unique call IDs and the values are strings
                indicating whether the score for that ID significantly differs from the sample mean
                along with the Z-score and critical value.

        Examples:
            >>> call_ids = [1, 1, 2, 2, 3, 3]
            >>> scores = [70, 75, 80, 85, 90, 95]
            >>> zscore_mean_hypothesis_test(call_ids, dates, scores)
            {1: 'The score 70 from id 1 significantly differs from the sample mean - (Z= -2.57).',
            2: 'The score 80 from id 2 does not significantly differ from the sample mean - (Z= -0.51).',
            3: 'The score 90 from id 3 does not significantly differ from the sample mean - (Z= 0.51).'}
        """

        # Data
        scores = np.array(scores)
        test_result = {}

        for specific_id in call_ids:

            indices = [i for i, id_ in enumerate(call_ids) if id_ == specific_id]
            specific_score = [scores[i] for i in indices]

            specific_score = specific_score[0]

            # Sample statistics
            sample_mean = np.mean(scores)
            sample_std = np.std(scores, ddof=1)  # Sample standard deviation
            n = len(scores)

            # Z-score calculation (compared to sample mean)
            z = (specific_score - sample_mean) / (sample_std / np.sqrt(n))

            # Significance level (alpha)
            alpha = 0.05
            critical_value = stats.norm.ppf(1 - alpha / 2)  # Critical value for two-tailed test (z)

            # Test
            if abs(z) > critical_value:
                test_result[specific_id] = (
                    f"The score {specific_score} from id {specific_id} significantly differs from the sample mean - (Z= {z:.2f})."
                )
            else:
                test_result[specific_id] = (
                    f"The score {specific_score} from id {specific_id} does not significantly differ from the sample mean - (Z= {z:.2f})."
                )
        return test_result

    async def gets_specific_data(self, specialist_name: str) -> List[Dict]:
        """
        Asynchronously loads and processes transcription data for a given specialist from an Azure Cosmos DB
        container, calculates Z-scores for the transcription scores, and returns the data enriched with Z-score information.

        This function queries the "evaluation" container in Cosmos DB to retrieve transcription data related to
        the specified specialist. It processes the data by extracting relevant fields (e.g., transcription ID
        and total score), computes Z-scores for the scores, and appends the Z-score results to each transcription entry.

        Args:
            specialist_name (str): The name of the specialist whose transcription data will be retrieved and processed.

        Returns:
            List[Dict]: A list of dictionaries containing transcription data. Each dictionary includes the following keys:
                - 'id' (int): The transcription ID.
                - 'pontuacao-total' (float): The total score of the transcription.
                - 'zscore' (float): The calculated Z-score for the transcription.
            If an error occurs during database access, a dictionary with an error message is returned instead.

        Raises:
            azure_exceptions.ServiceRequestError: Raised if there is an issue connecting to the Azure Cosmos DB service.

        Example:
            >>> transcriptions = await gets_specific_data("Specialist A")
            >>> print(transcriptions)
            [
                {
                    "id": 19,
                    "pontuacao-total": 70,
                    "zscore": 1.32
                },
                {
                    "id": 20,
                    "pontuacao-total": 33,
                    "zscore": 0.06
                },
                ...
            ]
        """

        async with CosmosClient(self.cosmos_endpoint, self.cosmos_key) as cosmos_client:
            try:
                database = cosmos_client.get_database_client(self.data_base_name)
                container = database.get_container_client("evaluation")
                query = "SELECT * FROM c WHERE c.assistant = @assistant_name"
                parameters = [{"name": "@assistant_name", "value": specialist_name}]

                specialist_transcriptions = []
                async for item in container.query_items(query=query, parameters=parameters):
                    try:
                        specialist_transcription = {
                            "id": int(item["id"]),
                            "pontuacao-total": item.get("evaluation", {}).get("pontuacao-total", 0),
                        }
                        specialist_transcriptions.append(specialist_transcription)
                    except Exception as exc:
                        # logger.error("Error loading transcription data: %s", str(exc))
                        pass
                        continue

                # Extract dates and scores
                scores = [item["pontuacao-total"] for item in specialist_transcriptions]
                call_ids = [int(item["id"]) for item in specialist_transcriptions]
                zscore_results = await self.calculates_score(call_ids, scores)

                # Assuming specialist_transcriptions and zscore_results are already defined
                for transcription in specialist_transcriptions:
                    transcription_id = int(
                        transcription["id"]
                    )  # Convert 'id' to int to match zscore_results
                    if transcription_id in zscore_results:
                        transcription["zscore"] = zscore_results[transcription_id]  # Append zscore

                # # Append Z-score information to each entry in the data list
                # for entry in specialist_transcriptions:
                #     try:
                #         id_num = int(entry['id'])
                #         if id_num in zscore_results:
                #             entry['z_score_info'] = zscore_results[id_num]
                #         else:
                #             entry['z_score_info'] = 'No Z-score information available.'
                #     except:
                #         pass

                return specialist_transcriptions

            except azure_exceptions.ServiceRequestError as exc:
                return [{"Error connecting to Azure": str(exc)}]


if __name__ == "__main__":
    factory = ConcreteAnalysisFactory()
    analysis = factory.create_analysis()
    specialist = input("Please enter the name of the specialist: ")  # TODO: to change when deployed
    data = asyncio.run(analysis.gets_specific_data(specialist))

    if data:
        print("Data was collected.")
