let skills = [];

const skillInput = document.getElementById("skill-input");
const skillContainer = document.getElementById("skill-container");
const skillHidden = document.getElementById("skill-hidden");

skillInput.addEventListener("keydown", function (e)
{
    if (e.key === "Enter" && skillInput.value.trim() !== "")
    {
        e.preventDefault();

        const skill = skillInput.value.trim();
    }
});