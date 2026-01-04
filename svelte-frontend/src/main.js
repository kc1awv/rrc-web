import './app.css'
import App from './App.svelte'
import LoginDialog from './components/LoginDialog.svelte'
import { connectWebSocket } from './websocket'

// Check if authentication is required
async function checkAuth() {
    try {
        const response = await fetch('/api/auth-status');
        if (!response.ok) {
            // If endpoint doesn't exist, assume no auth (backward compatibility)
            return true;
        }
        const data = await response.json();
        // Return true if authenticated or auth not required
        return !data.auth_required || data.is_authenticated;
    } catch (error) {
        console.error('Failed to check auth status:', error);
        // If we can't reach the server, assume no auth for now
        return true;
    }
}

// Initialize the application
async function init() {
    const isAuthenticated = await checkAuth();
    
    if (!isAuthenticated) {
        // Show login dialog
        const loginApp = new LoginDialog({
            target: document.getElementById('app'),
        });
    } else {
        // Show main app
        const app = new App({
            target: document.getElementById('app'),
        });
        
        // Connect WebSocket after app is mounted
        connectWebSocket();
    }
}

init();

export default {}

