var checkbox = document.getElementById('view-all-chicken');

checkbox.addEventListener('change', function() {
    var isChecked = checkbox.checked;

    // Send an HTTP request to the server to update the state
    fetch('/update_checkbox_state', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'isChecked=' + isChecked, // Send the checkbox state as a form parameter
    })
    .then(response => response.text())
    .then(data => {
        // Handle the response from the server if needed
        console.log('Server response:', data);
    })
    .catch(error => {
        console.error('Error:', error);
    });
});

var chickenIdSelect = document.getElementById('chicken-id');
var image = document.getElementById('plot-image');
var previousSelectedChickenId = null; // Initialize to null
var refreshInterval = 30000; // milliseconds

function updateGraphImage() {
    var selectedChickenId = chickenIdSelect.value;
    var timestamp = new Date().getTime();  // Generate a unique timestamp

    // Update the image source with selected ID and timestamp as query parameters
    image.src = "/graph?id=" + selectedChickenId + "&timestamp=" + timestamp;
    previousSelectedChickenId = selectedChickenId; // Update the previous ID

    // Set a timeout to refresh the image again after the refresh interval
    timeoutId = setTimeout(updateGraphImage, refreshInterval);
}

// Start checking for graph updates when the page loads
updateGraphImage();

// Listen for changes in the selected ID and trigger an immediate refresh
chickenIdSelect.addEventListener('change', function() {
    // Clear the existing timeout
    clearTimeout(timeoutId);

    // Call the updateGraphImage immediately
    updateGraphImage();
});

