// Dropdown functionality
document.addEventListener('DOMContentLoaded', function()
{
    document.querySelectorAll('.menu-container').forEach(menu =>
    {
        menu.querySelector('.menu-show-btn').addEventListener('click', function(e)
        {
            e.stopPropagation();
            menu.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e)
        {
            if (!menu.contains(e.target))
            {
                menu.classList.remove('show');
            }
        });
        // Close dropdown when pressing Escape key
        document.addEventListener('keydown', function(e)
        {
            if (e.key === 'Escape' && menu.classList.contains('show'))
            {
                menu.classList.remove('show');
            }
        });
    });
});
