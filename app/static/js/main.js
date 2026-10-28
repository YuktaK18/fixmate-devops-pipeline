// FixMate — Client-side Interactivity Script

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss alerts after 6 seconds
  const autoAlerts = document.querySelectorAll('.alert-dismissible');
  autoAlerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 6000);
  });

  // Countdown timer for 5-minute provider acceptance window
  const timerElements = document.querySelectorAll('[data-countdown-deadline]');
  timerElements.forEach(function (el) {
    const deadline = new Date(el.getAttribute('data-countdown-deadline')).getTime();

    function updateTimer() {
      const now = new Date().getTime();
      const distance = deadline - now;

      if (distance <= 0) {
        el.innerHTML = "<span class='badge bg-danger'>Window Expired</span>";
      } else {
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        el.innerHTML = `<span class='badge bg-warning text-dark'><i class='bi bi-clock-history me-1'></i> ${minutes}m ${seconds}s remaining</span>`;
      }
    }
    updateTimer();
    setInterval(updateTimer, 1000);
  });

  // Live ETA tracker on booking details page
  const trackingContainer = document.getElementById('live-eta-tracker');
  if (trackingContainer) {
    const bookingId = trackingContainer.getAttribute('data-booking-id');
    function fetchTracking() {
      fetch(`/api/v1/tracking/${bookingId}`)
        .then(response => response.json())
        .then(data => {
          if (!data.error) {
            const etaBadge = document.getElementById('tracking-eta-badge');
            const statusText = document.getElementById('tracking-status-text');
            if (etaBadge && data.eta_minutes !== null) {
              etaBadge.innerText = data.eta_minutes > 0 ? `~${data.eta_minutes} mins` : 'Arrived / On Site';
            }
            if (statusText) {
              statusText.innerText = data.status_text;
            }
          }
        })
        .catch(err => console.debug('Tracking polling:', err));
    }
    fetchTracking();
    setInterval(fetchTracking, 15000);
  }
});
