// region Variables

const maxCharLimit = 30;
const skillInput = document.getElementById('skill-input');
const skillContainer = document.getElementById('skills-container');
const skillHidden = document.getElementById('skills-hidden');
const addJobWindowWarningMsg = document.getElementById('add-job-window-warning-msg');

let skills = [];
let skillsLowerCase = [];
let isWarningMsgShowing = false;
let warningMsgTimeout = null;

// endregion

// region Events

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
            showTemporaryWarningMsg(`Maximum ${maxCharLimit} characters allowed!`);
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
    }
});

skillInput.addEventListener('input', function(e)
{
    // Enforce character limit
    if (this.value.length > maxCharLimit)
    {
        this.value = this.value.slice(0, maxCharLimit);
        showTemporaryWarningMsg(`Maximum ${maxCharLimit} characters!`);
    }

    // Remove any special characters (allow only letters, numbers, spaces, and hyphens)
    let value = this.value;

    // Regex: allows letters (a-z, A-Z), numbers (0-9), spaces, hyphens, and underscores
    let cleaned = value.replace(/[^a-zA-Z0-9\s\-_#]/g, '');

    if (cleaned !== value)
    {
        this.value = cleaned;
        showTemporaryWarningMsg('Only letters, numbers, spaces, hyphens, and underscores are allowed!');
    }
});

// endregion

// region Methods

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
    skillHidden.value = skillsLowerCase.join(',');
}

function removeSkill(index)
{
    skills.splice(index, 1);
    skillsLowerCase.splice(index, 1);

    renderSkills();
}

// endregion
