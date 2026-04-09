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
