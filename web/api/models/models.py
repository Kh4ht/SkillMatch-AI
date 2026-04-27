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
        id: int,
        user_id: int,
        job_title: str,
        min_edu: str,
        min_years_exp: int,
        skill_name_weight: dict[str, int],
        min_edu_weight: int = 1,
        min_exp_weight: int = 1,
    ):
        self.id = id
        self.user_id = user_id
        self.job_title = job_title
        self.min_edu = min_edu
        self.min_years_exp = min_years_exp
        self.skill_name_weight = skill_name_weight
        self.min_edu_weight = min_edu_weight
        self.min_exp_weight = min_exp_weight

        self.skills_comma_sep = self.comma_separate_skills()

    def comma_separate_skills(self) -> str:

        return ", ".join(self.skill_name_weight.keys())


# endregion
# #####################################################################

# #####################################################################
# region Job Skill Class


class JobSkill:

    def __init__(self, id: int, job_id: int, name: str, weight: int):
        self.id = id
        self.job_id = job_id
        self.name = name
        self.weight = weight


# endregion
