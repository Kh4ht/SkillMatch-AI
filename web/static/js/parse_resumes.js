// region Variables

const clearSearchInputBtn = document.getElementById('clear_search_btn');
const searchCandidatesTableInput = document.getElementById('search_txt_input');
const candidatesTable = document.getElementById('candidates-table');
const jobDetailsTable = document.getElementById('job_details_table');
const noSearchResultsRow = document.getElementById('no_search_results');

let selectedJobElement = null;

// endregion

// region Events

// Add event listeners when page loads
document.addEventListener('DOMContentLoaded', function()
{
    // Search as you type
    searchCandidatesTableInput.addEventListener('input', searchTable);

    // Call searchTable on load to set initial button state
    searchTable();

    setMatchScoreColors();
});

// endregion

// region METHODS

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
    const searchTerm = searchCandidatesTableInput.value.toLowerCase().trim();
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
    searchCandidatesTableInput.value = '';
    searchTable();
    searchCandidatesTableInput.focus();
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
