// Notification Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Mark single notification as read
    function markNotificationRead(notificationId) {
        fetch(`/api/notification/${notificationId}/read/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update UI to show notification as read
                const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
                if (notificationElement) {
                    notificationElement.classList.remove('unread');
                    notificationElement.classList.add('read');
                }
                updateNotificationCount();
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }

    // Mark all notifications as read
    function markAllNotificationsRead() {
        fetch('/notifications/mark-read/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update UI to show all notifications as read
                document.querySelectorAll('.notification-item.unread').forEach(item => {
                    item.classList.remove('unread');
                    item.classList.add('read');
                });
                updateNotificationCount();
            }
        })
        .catch(error => {
            console.error('Error marking all notifications as read:', error);
        });
    }

    // Update notification count in navbar
    function updateNotificationCount() {
        fetch('/notifications/count/')
        .then(response => response.json())
        .then(data => {
            const countElement = document.querySelector('.notification-count');
            if (countElement) {
                if (data.count > 0) {
                    countElement.textContent = data.count;
                    countElement.style.display = 'inline';
                } else {
                    countElement.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Error updating notification count:', error);
        });
    }

    // Get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Event listeners
    document.addEventListener('click', function(e) {
        // Mark single notification as read when clicked
        if (e.target.closest('.notification-item')) {
            const notificationItem = e.target.closest('.notification-item');
            const notificationId = notificationItem.dataset.notificationId;
            if (notificationId && notificationItem.classList.contains('unread')) {
                markNotificationRead(notificationId);
            }
        }

        // Mark all notifications as read
        if (e.target.matches('.mark-all-read') || e.target.closest('.mark-all-read')) {
            e.preventDefault();
            markAllNotificationsRead();
        }
    });

    // Auto-update notification count every 30 seconds
    setInterval(updateNotificationCount, 30000);
});