let skills = [];

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
        
        if (skills.includes(skill))
        {
            alert("Skill already added!");
            return;
        }

        skills.push(skill);

        renderSkills();

        skillInput.value = "";
    }
});


function renderSkills()
{
    skillContainer.innerHTML = "";

    skills.forEach((skill, i) =>
    {
        const tag = document.createElement("span")
        tag.className = "skill-tag"
        tag.innerHTML = skill + ' <button onclick="removeSkill('+i+')">x</button>'

        skillContainer.appendChild(tag)
    });

    skillHidden.value = skills.join(",");
}

function removeSkill(index)
{
    skills.splice(index, 1);

    renderSkills();
}