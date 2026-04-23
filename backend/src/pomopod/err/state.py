class ActiveSpaceNotSet(Exception):
  """Exception raised when the active space is not set."""

  def __init__(self, message="Active space value is not set"):
    """
    Args:
      message (str): The main error message.
    """
    self.message = message
    super().__init__(self.message)
