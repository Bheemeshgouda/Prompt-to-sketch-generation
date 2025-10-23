// Close alert messages
document.addEventListener('DOMContentLoaded', function() {
    // Close buttons for alerts
    const closeButtons = document.querySelectorAll('.close-btn');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });
    
    // Confirm before marking as accurate
    const accurateButtons = document.querySelectorAll('[name="accurate"]');
    accurateButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure this composite is accurate? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
    
    // Case number formatting
    const caseNumberInputs = document.querySelectorAll('input[name="case_number"]');
    caseNumberInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    });
});