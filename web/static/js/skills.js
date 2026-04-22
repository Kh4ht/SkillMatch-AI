let skills = [];
let skillsLowerCase = [];
const maxCharNum = 20;

const skillInput = document.getElementById('skill-input');
const skillContainer = document.getElementById('skills-container');
const skillHidden = document.getElementById('skills-hidden');
const warning = document.getElementById('warning');

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
        if (skill.length > maxCharNum)
        {
            showTemporaryMessage(`Maximum ${maxCharNum} characters allowed!`);
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

// Prevent spaces in skill input
document.addEventListener('DOMContentLoaded', function()
{
    const skillInput = document.getElementById('skill-input');

    if (skillInput)
    {
        // Prevent space key
        skillInput.addEventListener('keydown', function(e)
        {
            if (e.key === ' ')
            {
                e.preventDefault();
                // Optional: Show a small warning
                showTemporaryMessage('Spaces NOT allowed!');
            }
        });

        // Clean any spaces from paste events
        skillInput.addEventListener('input', function(e)
        {
            this.value = this.value.replace(/\s/g, '');
        });

        // Clean any spaces from paste events AND enforce character limit
        skillInput.addEventListener('input', function(e)
        {
            // Remove spaces
            this.value = this.value.replace(/\s/g, '');

            // Enforce character limit
            if (this.value.length > maxCharNum)
            {
                this.value = this.value.slice(0, maxCharNum);
                showTemporaryMessage(`Maximum <b>${maxCharNum}</b> characters reached!`);
            }

            // Optional: Show character count
            showCharacterCount(this.value.length);
        });
    }
});

let isMessageShowing = false;
let messageTimeout = null;

// Show temporary warning
function showTemporaryMessage(msg)
{
    // Prevent showing if already showing
    if (isMessageShowing) return;

    isMessageShowing = true;

    // Remove the popup-effect class
    warning.classList.remove('popup-effect');

    // Force a reflow to restart the animation
    void warning.offsetWidth;

    warning.style.display = 'block';
    warning.innerHTML = msg;

    // Re-add the class to trigger animation
    warning.classList.add('popup-effect');

    // Clear existing timeout
    if (messageTimeout)
    {
        clearTimeout(messageTimeout);
    }

    messageTimeout = setTimeout(() =>
    {
        warning.style.display = 'none';
        isMessageShowing = false;
        messageTimeout = null;
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
