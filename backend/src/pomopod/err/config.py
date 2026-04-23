class SpaceAlreadyExists(Exception):
  """Exception raised when a space with the same name already exists."""

  def __init__(self, message="Space with the same name already exists"):
    """
    Args:
      message (str): The main error message.
    """
    self.message = message
    super().__init__(self.message)


class SpaceDoesNotExist(Exception):
  """Exception raised when a space with the given name does not exists."""

  def __init__(self, message="Space with that name does not exist"):
    """
    Args:
      message (str): The main error message.
    """
    self.message = message
    super().__init__(self.message)
