let skills = [];
let skillsLowerCase = [];
const maxCharNum = 20;

const skillInput = document.getElementById("skill-input");
const skillContainer = document.getElementById("skills-container");
const skillHidden = document.getElementById("skills-hidden");

skillInput.addEventListener("keydown", function (e)
{
    if (e.key === "Enter")
    {
        e.preventDefault(); // stop form submit

        const skill = skillInput.value.trim();

        if (skill === "")
            return; // do nothing if empty

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
        skillsLowerCase.push(skill.toLowerCase())

        renderSkills();

        skillInput.value = "";
    }
});

// Prevent spaces in skill input
document.addEventListener('DOMContentLoaded', function() {
    const skillInput = document.getElementById('skill-input');
    
    if (skillInput) {
        // Prevent space key
        skillInput.addEventListener('keydown', function(e) {
            if (e.key === ' ') {
                e.preventDefault();
                // Optional: Show a small warning
                showTemporaryMessage('Spaces not allowed!');
            }
        });
        
        // Clean any spaces from paste events
        skillInput.addEventListener('input', function(e) {
            this.value = this.value.replace(/\s/g, '');
        });

        // Clean any spaces from paste events AND enforce character limit
        skillInput.addEventListener('input', function(e) {
            // Remove spaces
            this.value = this.value.replace(/\s/g, '');
            
            // Enforce character limit
            if (this.value.length > maxCharNum) {
                this.value = this.value.slice(0, maxCharNum);
                showTemporaryMessage(`Maximum <b>${maxCharNum}</b> characters reached!`);
            }
            
            // Optional: Show character count
            showCharacterCount(this.value.length);
        });
    }
});

// Optional: Show temporary warning
function showTemporaryMessage(msg) {
    // Create or get warning element
    let warning = document.getElementById('space-warning');
    
    warning.innerHTML = msg;
    setTimeout(() => {
        warning.innerHTML = '';
    }, 2000);
}

function renderSkills()
{
    skillContainer.innerHTML = "";

    skills.forEach((skill, i) =>
    {
        const tag = document.createElement("span")
        tag.className = "skill-tag"
        tag.innerHTML = `<button class='added-skill' onclick="removeSkill(${i})">${skill}</button>`

        skillContainer.appendChild(tag)
    });

    // Store Data In Lower Case
    skillHidden.value = skillsLowerCase.join(",");
}

function removeSkill(index)
{
    skills.splice(index, 1);
    skillsLowerCase.splice(index, 1);

    renderSkills();
}
