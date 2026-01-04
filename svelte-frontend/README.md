# Svelte + daisyUI Frontend for RRC Browser

This directory contains a frontend for the RRC Browser built with Svelte and daisyUI.

### Prerequisites

You need Node.js (v16 or higher) and npm installed on your system.

### Build Steps

1. Install dependencies:
   ```bash
   cd svelte-frontend
   npm install
   ```

2. Build the production bundle:
   ```bash
   npm run build
   ```

3. The built files will be output to `../rrc_web/static-svelte/`

### Development

To run the development server with hot reload:

```bash
npm run dev
```

Then open your browser to the URL shown (usually `http://localhost:5173`).

Note: The WebSocket connection expects the backend to be running on the same host/port as the frontend is served from.
