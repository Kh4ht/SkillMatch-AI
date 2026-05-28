// region Variables

const maxSkillCharLimit = 30;

const titleInput = document.getElementById('job_title');
const skillInput = document.getElementById('skill-input');
const jobExperienceInput = document.getElementById('jobExperience');
const EducationInput = document.getElementById('min_edu');

const skillContainer = document.getElementById('skills-container');
const skillHidden = document.getElementById('skills-hidden');
const skillWeightHidden = document.getElementById('skills-weight-hidden');

const addJobWindowWarningMsg = document.getElementById('add-job-window-warning-msg');

const summaryAndWeightsTable = document.getElementById('summary_and_weights_table');

let skillsLowerCase = [];
let skills = [];
let skillWeights = [];

let isWarningMsgShowing = false;
let warningMsgTimeout = null;

// Store weights in an object
let weightValues = {
    skills: [], // Array of skill weights
    experience: 50,
    education: 50,
};

// endregion

// region Events

document.addEventListener('DOMContentLoaded', function()
{
    updateSummaryAndWeightsTable();

    // Add form submit handler
    const form = document.getElementById('addJobForm');
    if (form)
    {
        form.addEventListener('submit', function(e)
        {
            // Populate hidden fields before submission
            populateHiddenFields();

            // Validate that skills exist
            if (skills.length === 0)
            {
                e.preventDefault();
                showTemporaryWarningMsg('Please add at least one required skill!');
                return false;
            }
        });
    }
});

// Add this function to populate hidden fields
function populateHiddenFields()
{
    // Populate skills (names)
    if (skillHidden)
    {
        skillHidden.value = skills.join(',');
    }

    // Populate skills weights
    if (skillWeightHidden)
    {
        skillWeightHidden.value = weightValues.skills.join(',');
    }

    // Debug: Log what's being sent
    console.log('Submitting skills:', skills);
    console.log('Submitting weights:', weightValues.skills);
    console.log('Experience weight:', weightValues.experience);
    console.log('Education weight:', weightValues.education);
}

titleInput.addEventListener('keydown', function(e)
{
    if (e.key === 'Enter')
    {
        e.preventDefault();
        skillInput.focus();
    }
});

skillInput.addEventListener('keydown', function(e)
{
    if (e.key === 'Enter')
    {
        e.preventDefault(); // stop form submit

        const skill = skillInput.value.trim();

        if (skill === '')
        {
            return; // do nothing if empty
        }

        if (skill.length < 2)
        {
            showTemporaryWarningMsg('Skill must be at least 2 letters!');
            return;
        }

        // Add character limit check
        if (skill.length > maxSkillCharLimit)
        {
            showTemporaryWarningMsg(`Maximum ${maxSkillCharLimit} characters allowed!`);
            return;
        }

        if (skillsLowerCase.includes(skill.toLowerCase()))
        {
            showTemporaryWarningMsg('Skill already added!');
            return;
        }

        skills.push(skill);
        skillsLowerCase.push(skill.toLowerCase());

        renderSkills();

        skillInput.value = '';

        updateSummaryAndWeightsTable();
    }
});

jobExperienceInput.addEventListener('keydown', function(e)
{
    if (e.key === 'Enter')
    {
        e.preventDefault();
        EducationInput.focus();
    }
});

EducationInput.addEventListener('keydown', function(e)
{
    if (e.key === 'Enter')
    {
        e.preventDefault();
        e.target.blur();
    }
});

titleInput.addEventListener('input', function(e)
{
    if (this.value[0] === ' ')
    {
        this.value = this.value.trimStart();
    }

    if (this.value.length > maxSkillCharLimit)
    {
        this.value = this.value.slice(0, maxSkillCharLimit);
        showTemporaryWarningMsg(`Maximum ${maxSkillCharLimit} characters!`);
    }
});

jobExperienceInput.addEventListener('input', function(e)
{
    if (this.value[0] === ' ')
    {
        this.value = this.value.trimStart();
    }

    if (this.value > 50)
    {
        this.value = 50;
        showTemporaryWarningMsg('Maximum 50 years of experience allowed!');
    } else if (this.value < 0)
    {
        this.value = 0;
        showTemporaryWarningMsg('Minimum experience is 0 years!');
    }

    // Allow only numbers and a single dot for decimal input
    let value = this.value;
    let cleaned = value.replace(/[^0-9]/g, '');

    // Ensure only one dot is allowed
    const parts = cleaned.split('.');
    if (parts.length > 2)
    {
        cleaned = parts[0] + '.' + parts.slice(1).join('');
    }

    if (cleaned !== value)
    {
        this.value = cleaned;
        showTemporaryWarningMsg('Only numbers and a single dot are allowed!');
    }

    updateSummaryAndWeightsTable();
});

skillInput.addEventListener('input', function(e)
{
    if (this.value[0] === ' ')
    {
        this.value = this.value.trimStart();
        return;
    }

    // Enforce character limit
    if (this.value.length > maxSkillCharLimit)
    {
        this.value = this.value.slice(0, maxSkillCharLimit);
        showTemporaryWarningMsg(`Maximum ${maxSkillCharLimit} characters!`);
    }

    // Remove any special characters (allow only letters, numbers, spaces, and hyphens)
    let value = this.value;

    // Regex: allows letters (a-z, A-Z), numbers (0-9), spaces, hyphens, and underscores
    let cleaned = value.replace(/[^a-zA-Z0-9\s\-_#\+\$]/g, '');

    if (cleaned !== value)
    {
        this.value = cleaned;
        showTemporaryWarningMsg('Only letters, numbers, spaces, hyphens, and underscores are allowed!');
    }
});

EducationInput.addEventListener('input', function(e)
{
    if (this.value[0] === ' ')
    {
        this.value = this.value.trimStart();
    }

    updateSummaryAndWeightsTable();
});

// endregion

// region Methods

function updateSummaryAndWeightsTable()
{
    const tbody = summaryAndWeightsTable.querySelector('tbody');
    tbody.innerHTML = '';

    // Initialize weights array if empty
    if (weightValues.skills.length !== skills.length)
    {
        resetWeights();
    }

    // Add skills rows
    for (let i = 0; i < skills.length; i++)
    {
        const row = document.createElement('tr');
        row.style.backgroundColor = '#f8f9fa';

        if (i === 0)
        {
            row.innerHTML = `
                <td rowspan="${skills.length}">Skills</td>
                <td>${escapeHtml(skills[i])}</td>
                <td><input type="number" class="weight-input skill-weight" name="weight_${i}" data-type="skill" data-index="${i}" min="1" max="100" value="${
                weightValues.skills[i]
            }"></td>
            `;
        } else
        {
            row.innerHTML = `
                <td>${escapeHtml(skills[i])}</td>
                <td><input type="number" class="weight-input skill-weight" name="weight_${i}" data-type="skill" data-index="${i}" min="1" max="100" value="${
                weightValues.skills[i]
            }"></td>
            `;
        }

        tbody.appendChild(row);
    }

    // Add Experience Row
    const experienceRow = document.createElement('tr');
    experienceRow.style.backgroundColor = 'white';
    experienceRow.innerHTML = `
        <td>Experience</td>
        <td>${jobExperienceInput.value > 0 ? jobExperienceInput.value + '+ years' : 'No experience needed'}</td>
        <td><input type="number" class="weight-input experience-weight" name="min_years_exp_weight" data-type="experience" min="1" max="100" value="${weightValues.experience}"></td>
    `;
    tbody.appendChild(experienceRow);

    // Add Education Row
    const educationRow = document.createElement('tr');
    educationRow.style.backgroundColor = '#f8f9fa';
    educationRow.innerHTML = `
        <td>Education</td>
        <td>${EducationInput.value !== '' ? EducationInput.value : 'Fresh Graduate'}</td>
        <td><input type="number" class="weight-input education-weight" name="min_education_weight" data-type="education" min="1" max="100" value="${weightValues.education}"></td>
    `;
    tbody.appendChild(educationRow);

    // Attach event listeners to all weight inputs
    attachWeightEventListeners();
}

function attachWeightEventListeners()
{
    const weightInputs = document.querySelectorAll('.weight-input');
    weightInputs.forEach(input =>
    {
        input.removeEventListener('change', handleWeightChange);
        input.addEventListener('change', handleWeightChange);
    });
}

function handleWeightChange(event)
{
    const input = event.target;
    const newValue = parseInt(input.value);
    const type = input.dataset.type;

    if (isNaN(newValue)) return;

    // Get current total of all weights
    let oldTotal = calculateTotalWeight();

    if (type === 'skill')
    {
        const index = parseInt(input.dataset.index);
        const oldValue = weightValues.skills[index];
        weightValues.skills[index] = newValue;

        // Distribute the difference to other weights
        const difference = newValue - oldValue;
        redistributeWeight(difference, [type, index]);
    } else if (type === 'experience')
    {
        const oldValue = weightValues.experience;
        weightValues.experience = newValue;

        const difference = newValue - oldValue;
        redistributeWeight(difference, [type]);
    } else if (type === 'education')
    {
        const oldValue = weightValues.education;
        weightValues.education = newValue;

        const difference = newValue - oldValue;
        redistributeWeight(difference, [type]);
    }

    // Update all input fields to reflect new values
    updateAllWeightInputs();
}

function redistributeWeight(difference, excludeItems)
{
    if (difference === 0) return;

    // Get all weight categories that can be adjusted
    let adjustableItems = [];

    // Add skills
    for (let i = 0; i < weightValues.skills.length; i++)
    {
        if (!(excludeItems[0] === 'skill' && excludeItems[1] === i))
        {
            adjustableItems.push({ type: 'skill', index: i, currentValue: weightValues.skills[i] });
        }
    }

    // Add experience
    if (!(excludeItems[0] === 'experience'))
    {
        adjustableItems.push({ type: 'experience', index: null, currentValue: weightValues.experience });
    }

    // Add education
    if (!(excludeItems[0] === 'education'))
    {
        adjustableItems.push({ type: 'education', index: null, currentValue: weightValues.education });
    }

    if (adjustableItems.length === 0) return;

    // Calculate how much to adjust each item
    const adjustmentPerItem = difference / adjustableItems.length;

    adjustableItems.forEach(item =>
    {
        let newValue = item.currentValue - adjustmentPerItem;
        newValue = Math.min(100, Math.max(1, Math.round(newValue))); // Constrain between 1-100

        if (item.type === 'skill')
        {
            weightValues.skills[item.index] = newValue;
        } else if (item.type === 'experience')
        {
            weightValues.experience = newValue;
        } else if (item.type === 'education')
        {
            weightValues.education = newValue;
        }
    });

    // Ensure total is exactly 100
    normalizeWeights(excludeItems);
}

function normalizeWeights(excludeItems)
{
    let currentTotal = calculateTotalWeight();
    const targetTotal = 100;

    if (currentTotal === targetTotal) return;

    const difference = targetTotal - currentTotal;

    // Get all adjustable items again
    let adjustableItems = [];
    for (let i = 0; i < weightValues.skills.length; i++)
    {
        if (!(excludeItems[0] === 'skill' && excludeItems[1] === i))
        {
            adjustableItems.push({ type: 'skill', index: i });
        }
    }
    if (!(excludeItems[0] === 'experience'))
    {
        adjustableItems.push({ type: 'experience', index: null });
    }
    if (!(excludeItems[0] === 'education'))
    {
        adjustableItems.push({ type: 'education', index: null });
    }

    if (adjustableItems.length === 0) return;

    const adjustmentPerItem = difference / adjustableItems.length;

    adjustableItems.forEach(item =>
    {
        if (item.type === 'skill')
        {
            let newValue = weightValues.skills[item.index] + adjustmentPerItem;
            newValue = Math.min(100, Math.max(1, Math.round(newValue)));
            weightValues.skills[item.index] = newValue;
        } else if (item.type === 'experience')
        {
            let newValue = weightValues.experience + adjustmentPerItem;
            newValue = Math.min(100, Math.max(1, Math.round(newValue)));
            weightValues.experience = newValue;
        } else if (item.type === 'education')
        {
            let newValue = weightValues.education + adjustmentPerItem;
            newValue = Math.min(100, Math.max(1, Math.round(newValue)));
            weightValues.education = newValue;
        }
    });
}

function calculateTotalWeight()
{
    let total = 0;

    // Sum skills
    weightValues.skills.forEach(weight =>
    {
        total += weight;
    });

    // Add experience and education
    total += weightValues.experience;
    total += weightValues.education;

    return total;
}

function updateAllWeightInputs()
{
    // Update skill inputs
    document.querySelectorAll('.skill-weight').forEach(input =>
    {
        const index = parseInt(input.dataset.index);
        input.value = weightValues.skills[index];
    });

    skillWeightHidden.value = weightValues.skills.join(',');

    // Update experience input
    const experienceInput = document.querySelector('.experience-weight');
    if (experienceInput)
    {
        experienceInput.value = weightValues.experience;
    }

    // Update education input
    const educationInput = document.querySelector('.education-weight');
    if (educationInput)
    {
        educationInput.value = weightValues.education;
    }
}

// Show temporary warning
function showTemporaryWarningMsg(msg)
{
    // Prevent showing if already showing
    if (isWarningMsgShowing)
    {
        return;
    }

    isWarningMsgShowing = true;

    // Remove the popup-effect class
    addJobWindowWarningMsg.classList.remove('popup-effect');

    // Force a reflow to restart the animation
    void addJobWindowWarningMsg.offsetWidth;

    addJobWindowWarningMsg.style.display = 'block';
    addJobWindowWarningMsg.innerHTML = msg;

    // Re-add the class to trigger animation
    addJobWindowWarningMsg.classList.add('popup-effect');

    // Clear existing timeout
    if (warningMsgTimeout)
    {
        clearTimeout(warningMsgTimeout);
    }

    warningMsgTimeout = setTimeout(() =>
    {
        addJobWindowWarningMsg.style.display = 'none';
        isWarningMsgShowing = false;
        warningMsgTimeout = null;
    }, 2000);
}

function renderSkills()
{
    skillContainer.innerHTML = '';

    skills.forEach((skill, i) =>
    {
        const tag = document.createElement('span');
        tag.className = 'skill-tag';
        tag.innerHTML = `<button class='added-skill' onclick="removeSkill(${i})">${skill}</button>`;

        skillContainer.appendChild(tag);
    });

    // Store Data In Lower Case
    skillHidden.value = skills.join(',');
}

function removeSkill(index)
{
    skills.splice(index, 1);
    skillsLowerCase.splice(index, 1);

    renderSkills();
    updateSummaryAndWeightsTable();
}

function resetWeights()
{
    const totalCategories = skills.length + 2; // Skills + Experience + Education
    const equalWeight = Math.floor(100 / totalCategories);

    weightValues.experience = equalWeight;
    weightValues.education = equalWeight;
    weightValues.skills = skills.map(() => equalWeight);

    updateAllWeightInputs();
}

// endregion
