// region TEXT INPUT

function emptyTextInput(inputElement)
{
    if (inputElement & inputElement.value !== undefined)
    {
        inputElement.value = '';
    } else
    {
        console.error('Invalid input element provided !');
    }
}

function emptyTextInputById(inputId)
{
    const inputElement = document.getElementById(inputId);

    if (inputElement)
    {
        inputElement.value = '';
    } else
    {
        console.error(`Input element with ID ${inputId} not found`);
    }
}

function emptyMultipleInputs(...inputElements)
{
    inputElements.forEach(input =>
    {
        if (input && input.value !== undefined)
        {
            input.value = '';
        }
    });
}

// endregion
////////////////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////////////////
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
