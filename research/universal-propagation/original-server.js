// =============================================================================
// EXPRESS HTTP & ISOLATION SERVER
// File: server.js
// =============================================================================

import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8080;

// Enforce isolation headers required for SharedArrayBuffer / WASM web memory
app.use((req, res, next) => {
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
    next();
});

app.use(express.static(path.join(__dirname, 'public')));

app.listen(PORT, () => {
    console.log(`[Enterprise Server] Runtime active at http://localhost:${PORT}`);
});

