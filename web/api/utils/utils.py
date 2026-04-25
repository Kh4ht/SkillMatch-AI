# region IMPORTS

# Standard library imports
from flask import request

# Local imports


# endregion
# #####################################################################

# #####################################################################
# region request_form_get


def request_form_get(element_id: str, strip=True) -> str:
    """For String Values"""

    result = request.form.get(element_id)

    if result is not None:
        if strip:
            result = result.strip()
        return result
    else:
        raise ValueError(f"The Request Field: '{element_id}' Is NONE")


# endregion
