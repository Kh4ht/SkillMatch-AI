# region IMPORTS


# Standard library imports


# Local imports


# endregion
# #####################################################################

# #####################################################################
# region Job Class


class Job:
    def __init__(
        self,
        user_id: int,
        job_title: str,
        min_edu: str,
        min_years_exp: int,
        skill_name_weight: dict[str, int],
        min_edu_weight: int = 1,
        min_exp_weight: int = 1,
    ):
        self.user_id = user_id
        self.job_title = job_title
        self.min_edu = min_edu
        self.min_years_exp = min_years_exp
        self.skill_name_weight = skill_name_weight
        self.min_edu_weight = min_edu_weight
        self.min_exp_weight = min_exp_weight


# endregion
