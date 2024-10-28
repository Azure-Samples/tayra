
class RetrievalException(Exception):
    """
    RetrievalException Exception raised when there is an error retrieving data from the database.
    """
    
    def __init__(self, message: str) -> None:
        """
        Initializes the RetrievalException.

        Args:
            message (str): The message to be displayed when the exception is raised.
        """
        super().__init__(message)
        self.message = message
