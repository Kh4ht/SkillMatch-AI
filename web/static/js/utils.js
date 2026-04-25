// region WINDOWS

function toggleWindow(elementID)
{
    const windowElement = document.getElementById(elementID);

    if (windowElement)
    {
        if (windowElement.style.display === 'block')
        {
            windowElement.style.display = 'none';
        } else
        {
            windowElement.style.display = 'block';
        }
    }
}

function closeWindow(elementID)
{
    const windowElement = document.getElementById(elementID);

    if (windowElement)
    {
        windowElement.style.display = 'none';
    }
}

function openWindow(elementID)
{
    const windowElement = document.getElementById(elementID);

    if (windowElement)
    {
        windowElement.style.display = 'block';
    }
}

// endregion
////////////////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////////////////
// region escapeHtml

// Helper function to escape HTML, for user inputs.
function escapeHtml(text)
{
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// endregion
////////////////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////////////////
// region clamp

function clamp(value, min, max)
{
    return Math.min(Math.max(value, min), max);
}

// endregion
