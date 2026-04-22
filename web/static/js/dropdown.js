// Dropdown functionality
document.addEventListener('DOMContentLoaded', function()
{
    const dropdown = document.querySelector('.dropdown');

    if (dropdown)
    {
        const dropbtn = dropdown.querySelector('.dropbtn');

        // Toggle dropdown on button click
        dropbtn.addEventListener('click', function(e)
        {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e)
        {
            if (!dropdown.contains(e.target))
            {
                dropdown.classList.remove('show');
            }
        });

        // Close dropdown when pressing Escape key
        document.addEventListener('keydown', function(e)
        {
            if (e.key === 'Escape' && dropdown.classList.contains('show'))
            {
                dropdown.classList.remove('show');
            }
        });
    }
});
