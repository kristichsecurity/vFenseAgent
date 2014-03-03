def try_long_cast(string):
    """Wrapper to cast a string into a long. No try/except all over the place.

     Returns:
        (bool) True if cast is successful. False otherwise.
    """
    try:
        long(string)
        return True
    except ValueError:
        return False
