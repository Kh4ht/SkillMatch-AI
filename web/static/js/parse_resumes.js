// region Variables

const clearSearchInputBtn = document.getElementById('clear_search_btn');
const searchInput = document.getElementById('search_txt_input');
const candidatesTable = document.getElementById('candidates-table');
const jobDetailsTable = document.getElementById('job_details_table');
const maxCharLimit = 30;
const skillInput = document.getElementById('skill-input');
const skillContainer = document.getElementById('skills-container');
const skillHidden = document.getElementById('skills-hidden');
const warning = document.getElementById('warning');
const noSearchResultsRow = document.getElementById('no_search_results');

let selectedJobElement = null;
let skills = [];
let skillsLowerCase = [];
let isWarningMsgShowing = false;
let warningMsgTimeout = null;

// endregion

// region Events

// Add event listeners when page loads
document.addEventListener('DOMContentLoaded', function()
{
    // Search as you type
    searchInput.addEventListener('input', searchTable);

    // Call searchTable on load to set initial button state
    searchTable();

    setMatchScoreColors();
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

        // Add character limit check
        if (skill.length > maxCharLimit)
        {
            showTemporaryMessage(`Maximum ${maxCharLimit} characters allowed!`);
            return;
        }

        if (skillsLowerCase.includes(skill.toLowerCase()))
        {
            showTemporaryMessage('Skill already added!');
            return;
        }

        skills.push(skill);
        skillsLowerCase.push(skill.toLowerCase());

        renderSkills();

        skillInput.value = '';
    }
});

skillInput.addEventListener('input', function(e)
{
    // Enforce character limit
    if (this.value.length > maxCharLimit)
    {
        this.value = this.value.slice(0, maxCharLimit);
        showTemporaryMessage(`Maximum ${maxCharLimit} characters!`);
    }

    // Remove any special characters (allow only letters, numbers, spaces, and hyphens)
    let value = this.value;

    // Regex: allows letters (a-z, A-Z), numbers (0-9), spaces, hyphens, and underscores
    let cleaned = value.replace(/[^a-zA-Z0-9\s\-_#]/g, '');

    if (cleaned !== value)
    {
        this.value = cleaned;
        showTemporaryMessage('Only letters, numbers, spaces, hyphens, and underscores are allowed!');
    }
});

// endregion

// region METHODS

// Show temporary warning
function showTemporaryMessage(msg)
{
    // Prevent showing if already showing
    if (isWarningMsgShowing)
    {
        return;
    }

    isWarningMsgShowing = true;

    // Remove the popup-effect class
    warning.classList.remove('popup-effect');

    // Force a reflow to restart the animation
    void warning.offsetWidth;

    warning.style.display = 'block';
    warning.innerHTML = msg;

    // Re-add the class to trigger animation
    warning.classList.add('popup-effect');

    // Clear existing timeout
    if (warningMsgTimeout)
    {
        clearTimeout(warningMsgTimeout);
    }

    warningMsgTimeout = setTimeout(() =>
    {
        warning.style.display = 'none';
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
    skillHidden.value = skillsLowerCase.join(',');
}

function removeSkill(index)
{
    skills.splice(index, 1);
    skillsLowerCase.splice(index, 1);

    renderSkills();
}

function setMatchScoreColors()
{
    const scoreCells = document.querySelectorAll('.match-score');

    scoreCells.forEach((cell) =>
    {
        const score = parseFloat(cell.textContent);

        if (!isNaN(score))
        {
            const ratio = Math.min(100, Math.max(0, score)) / 100;

            const red = Math.floor(255 * clamp(1 - ratio, 0, 0.45) * 2); // 0.5 to 1 maps to 255-0 red and 0 to 0.5 maps to 255 red

            const green = Math.floor(255 * clamp(ratio, 0, 0.45) * 2); // 0 to 0.5 maps to 0-255 green and 0.5 to 1 maps to 255 green

            cell.style.color = `rgb(${red}, ${green}, 0)`;
        }
    });
}

function searchTable()
{
    const searchTerm = searchInput.value.toLowerCase().trim();
    const tbody = candidatesTable.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');

    let hasMatches = false;

    rows.forEach((row) =>
    {
        // Skip the "no results" row
        if (row.id === 'noResultsRow')
        {
            return;
        }

        // Get all text content from the row (excluding the checkbox column)
        const cells = row.querySelectorAll('td:not(.checkbox-col)');
        let rowText = '';

        cells.forEach((cell) =>
        {
            rowText += cell.textContent.toLowerCase() + ' ';
        });

        // Check if search term matches any content in the row
        if (searchTerm === '' || rowText.includes(searchTerm))
        {
            row.style.display = ''; // Show row
            hasMatches = true;
        } else
        {
            row.style.display = 'none'; // Hide row
        }
    });

    // Update clear button disabled state
    clearSearchInputBtn.disabled = searchTerm === '';

    if (!hasMatches)
    {
        noSearchResultsRow.style.display = 'block';
    } else
    {
        noSearchResultsRow.style.display = 'none';
    }
    // Optional: Show "no results" message
}

function clearSearchInput()
{
    searchInput.value = '';
    searchTable();
    searchInput.focus();
}

function selectJob(newElement)
{
    // Do Nothing If The Selected Job Card Is Reselected.
    if (selectedJobElement === newElement) return;

    selectedJobElement = newElement;

    // Update active state in UI
    document.querySelectorAll('.job-card').forEach(card =>
    {
        card.classList.remove('active');
    });
    selectedJobElement.classList.add('active');

    // Get all data from data attributes
    const jobData = {
        id: selectedJobElement.dataset.jobId,
        job_title: selectedJobElement.dataset.jobTitle,
        min_years_exp: selectedJobElement.dataset.minYearsExp,
        min_edu: selectedJobElement.dataset.minEdu,
        min_edu_weight: selectedJobElement.dataset.minEduWeight,
        min_exp_weight: selectedJobElement.dataset.minExpWeight,
        skill_name_weight: JSON.parse(selectedJobElement.dataset.skills),
    };

    // Update UI
    updateJobDetailsTable(jobData);
}

function updateJobDetailsTable(jobData)
{
    // Get the table body
    const tbody = jobDetailsTable.querySelector('tbody');

    // Clear existing rows
    tbody.innerHTML = '';

    // Get skills as array of [skill_name, weight]
    const skills = Object.entries(jobData.skill_name_weight || {});

    // Add Skills section with rowspan
    if (skills.length > 0)
    {
        // First skill row with rowspan
        const firstSkillRow = tbody.insertRow();
        const skillCategoryCell = firstSkillRow.insertCell(0);
        skillCategoryCell.rowSpan = skills.length;
        skillCategoryCell.innerHTML = '<strong>Skills</strong>';

        // First skill
        firstSkillRow.insertCell(1).textContent = skills[0][0];
        firstSkillRow.insertCell(2).textContent = `${skills[0][1]}%`;

        // Remaining skills
        for (let i = 1; i < skills.length; i++)
        {
            const skillRow = tbody.insertRow();
            // skillRow.insertCell(0); // Empty cell (because of rowspan)
            skillRow.insertCell(0).textContent = skills[i][0];
            skillRow.insertCell(1).textContent = `${skills[i][1]}%`;
        }
    } else
    {
        // No skills case
        const noSkillsRow = tbody.insertRow();
        noSkillsRow.insertCell(0).innerHTML = '<strong>Skills</strong>';
        noSkillsRow.insertCell(1).textContent = 'No skills specified';
        noSkillsRow.insertCell(2).textContent = '0%';
    }

    // Add Experience row
    const expRow = tbody.insertRow();
    expRow.insertCell(0).innerHTML = '<strong>Experience</strong>';
    expRow.insertCell(1).textContent = `${jobData.min_years_exp}+ years`;
    expRow.insertCell(2).textContent = `${jobData.min_exp_weight || 1}%`;

    // Add Education row
    const eduRow = tbody.insertRow();
    eduRow.insertCell(0).innerHTML = '<strong>Education</strong>';
    eduRow.insertCell(1).textContent = jobData.min_edu || 'Not specified';
    eduRow.insertCell(2).textContent = `${jobData.min_edu_weight || 1}%`;
}

// endregion
