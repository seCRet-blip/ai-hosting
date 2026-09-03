# NZ Aerial Imagery Classification API

A production-style inference service that classifies New Zealand aerial imagery with a custom EfficientNet-B3 model, served over HTTPS through a hardened Docker stack.

Upload a tile. Get a prediction, class probabilities, and a confidence score. The model never talks to the internet directly — nginx, hashed API keys, and dual-layer rate limits sit in front of it.

```
Client  ──HTTPS──►  ngrok  ──►  nginx  ──►  Flask  ──►  ONNX Runtime
                    tunnel      proxy       API         EfficientNet-B3
```

Built to show how I take a trained model off a notebook and run it like a real product: containerized, authenticated, rate-limited, and reachable without exposing a home IP.

---

## Why this exists

Training a model is the easy half. Hosting one is where most student projects stop.

This repo is the other half — a small production pipeline for a binary classifier trained on NZ regional aerial tiles (the sample in-repo is an Auckland zoom-15 tile). PyTorch weights are exported to ONNX so inference stays fast on CPU, then the model is wrapped in a public API with the controls you would expect before handing it to another app.

| Layer | What it does |
| --- | --- |
| **Model** | EfficientNet-B3 with a custom classification head, ImageNet-initialized, exported to ONNX opset 18 |
| **Inference** | ONNX Runtime on 128×128 RGB tiles, ImageNet normalization, softmax probabilities |
| **API** | Flask endpoints for health and authenticated prediction, hashed API-key comparison |
| **Edge** | nginx reverse proxy, CORS allowlist, security headers, upload and connection limits |
| **Access** | ngrok HTTPS tunnel so the stack can be demoed without opening inbound ports |
| **Ops** | Docker Compose, healthchecks, `unless-stopped` restarts, structured error logging |

---

## Design choices

**End-to-end ML serving, not a Flask demo.** Weights live in `models/`. `export_model.py` converts a `.pth` checkpoint to ONNX. `server.py` loads the improved ONNX graph once at startup and never reloads it per request.

**Defense in depth, not a single if-statement.** `/predict` requires `X-API-Key`. The key is hashed with SHA-256 at boot and compared as a hash. nginx and Flask-Limiter both throttle traffic. Uploads are checked for type, size (10 MB), dimensions (max 4096×4096), and actual image integrity before they reach the model.

**The public internet never hits Flask first.** Request path is ngrok → nginx → API. nginx adds `X-Frame-Options`, `nosniff`, XSS, and referrer headers, caps body size, and applies tighter limits on `/predict` than on `/health`.

**Secrets stay out of the image.** API key and ngrok token come from `.env`. There is no hardcoded fallback key in Compose. `.env` is gitignored; `.env.example` is the only template committed.

---

## Architecture

```
  HTTPS                 :80                    :5001
Client -------> ngrok -------> nginx -------> Flask API
                tunnel         proxy          ONNX Runtime
                               CORS           EfficientNet-B3
                               rate limits
                               security headers
```

**Three containers, one command.**

1. `ai-model-api` — Python 3.10 slim image, model baked in, `/health` used by Docker healthchecks
2. `ai-proxy` — nginx Alpine, config mounted read-only
3. `ngrok-tunnel` — HTTPS in front of nginx, inspector on `localhost:4040`

---

## Model

| | |
| --- | --- |
| Architecture | EfficientNet-B3 + dropout / Linear / ReLU / BatchNorm head |
| Task | Binary classification on NZ regional aerial tiles |
| Input | 128×128 RGB, mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]` |
| Output | `{ prediction, probabilities, confidence }` |
| Train → serve | PyTorch `.pth` → `export_model.py` → ONNX → ONNX Runtime |

Served weights: `models/improved_All_nz_regions_model.onnx`

---

## Security (the short version)

- **Auth:** `X-API-Key` on `/predict`; SHA-256 compare; `/health` stays open for probes
- **Rate limits:** nginx `1r/m` on general routes (burst 20) and `10r/m` on `/predict` (burst 5); Flask-Limiter caps predict at 30/hour
- **Connections:** 10 concurrent per IP generally, 5 on `/predict`
- **Uploads:** png / jpg / jpeg / gif / bmp / webp only, 10 MB max, 4096² max, `Image.verify()`
- **Headers:** `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, `Referrer-Policy`
- **Errors:** clients get generic messages; logs record exception type only

Never put the API key in frontend JavaScript. Call this service from your own backend.

---

## API

### `GET /health`

No key. Used by Docker and load balancers.

```json
{ "status": "healthy", "model_loaded": true }
```

### `POST /predict`

Headers: `X-API-Key`, `Content-Type: multipart/form-data`  
Body: `file` — image, max 10 MB

```json
{
  "prediction": 0,
  "probabilities": [0.8234, 0.1766],
  "confidence": 0.8234
}
```

| Status | Meaning |
| --- | --- |
| 401 | Missing or wrong API key |
| 400 | Bad / empty / non-image file |
| 413 | Over 10 MB |
| 429 | Rate limit |
| 500 | Model missing or inference failed |

### `GET /`

Service info and endpoint list.

---

# Setup

## Prerequisites

- Docker Desktop (Windows / Mac) or Docker Engine (Linux)
- Docker Compose
- An [ngrok](https://ngrok.com) account (free tier is enough)
- Python 3.10+ if you are exporting models locally
- Node.js if you want to run `test.js`

## 1. Clone

```bash
git clone https://github.com/seCRet-blip/ai-hosting.git
cd ai-hosting
```

## 2. Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
AI_API_KEY=your-secure-api-key-here
NGROK_AUTHTOKEN=your-ngrok-token-here
AI_API_URL=http://localhost
```

Get the ngrok token from [the ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken). Generate an API key:

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# PowerShell
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

## 3. Start the stack

```bash
docker-compose up -d --build
docker-compose ps
docker-compose logs -f
```

## 4. Public URL

```bash
docker-compose logs ngrok
# or open http://localhost:4040
```

You want a line like `url=https://abc123.ngrok-free.app`. Put that in `.env` as `AI_API_URL` if you are calling the public tunnel from `test.js`.

---

## Try it

Health (no key):

```bash
curl https://your-ngrok-url.ngrok-free.app/health
```

Prediction:

```bash
curl -X POST \
  -F "file=@auckland_15_32258_19983.jpg" \
  -H "X-API-Key: your-api-key-here" \
  https://your-ngrok-url.ngrok-free.app/predict
```

Or the Node script:

```bash
npm install
# AI_API_KEY and AI_API_URL must be set in .env
node test.js
```

---

## Using it from a web app

**Do not send `X-API-Key` from the browser.** Proxy through your own backend.

```javascript
// your-backend.js — key stays on the server
import express from 'express';
import fetch from 'node-fetch';
import FormData from 'form-data';

const AI_API_KEY = process.env.AI_API_KEY;
const AI_API_URL = process.env.AI_API_URL;

app.post('/api/predict', upload.single('image'), async (req, res) => {
    const formData = new FormData();
    formData.append('file', req.file.buffer, req.file.originalname);

    const response = await fetch(`${AI_API_URL}/predict`, {
        method: 'POST',
        body: formData,
        headers: {
            ...formData.getHeaders(),
            'X-API-Key': AI_API_KEY
        }
    });

    res.json(await response.json());
});
```

```javascript
// frontend.js — no secrets
async function predictImage(imageFile) {
    const formData = new FormData();
    formData.append('image', imageFile);
    const response = await fetch('/api/predict', { method: 'POST', body: formData });
    return response.json();
}
```

---

## Day-to-day commands

```bash
docker-compose up -d
docker-compose down
docker-compose logs -f
docker-compose logs ai-model-api
docker-compose logs nginx-proxy
docker-compose logs ngrok
docker-compose restart
docker-compose up -d --build
docker-compose ps
```

ngrok inspector: [http://localhost:4040](http://localhost:4040)

---

## Swap in a new model

```bash
python export_model.py
docker-compose down
docker-compose up -d --build
```

`export_model.py` reads `models/improved_All_nz_regions_model.pth` and writes the ONNX file the API loads at startup.

---

## Project layout

```
ai-hosting/
├── server.py              # Flask API — auth, validation, inference
├── model_arc.py           # EfficientNet-B3 + ONNXInference
├── export_model.py        # PyTorch → ONNX
├── Dockerfile             # API image
├── docker-compose.yml     # API + nginx + ngrok
├── nginx.conf             # Limits, CORS, security headers
├── ngrok.yml              # HTTPS tunnel onto nginx
├── requirements.txt
├── .env.example           # Template only — copy to .env
├── package.json
├── test.js                # Smoke test against AI_API_URL
├── auckland_15_32258_19983.jpg
└── models/
    └── improved_All_nz_regions_model.onnx
```

`.env` is local-only and is not in git.

---

## Troubleshooting

**ngrok auth failed**  
Put a valid `NGROK_AUTHTOKEN` in `.env`, then `docker-compose restart ngrok`.

**401 on `/predict`**  
Send `X-API-Key` and make sure it matches `AI_API_KEY` in `.env` (no extra spaces).

**429**  
Wait for the window to reset. Limits are there on purpose.

**`model_loaded: false`**  
Confirm `models/improved_All_nz_regions_model.onnx` exists, then `docker-compose logs ai-model-api` and rebuild.

**Container restart loop**

```bash
docker-compose logs [service-name]
```

Usual causes: missing env vars, bad nginx config, port 4040 already in use.

---

## Going further

- Raise nginx rates in `nginx.conf` if you are load-testing, then `docker-compose restart nginx-proxy`
- A reserved ngrok domain needs a paid ngrok plan
- For a real deploy, drop ngrok and put the same Compose stack behind AWS ECS, Cloud Run, or Azure Container Apps with a proper domain and TLS

---

## License

Private. All rights reserved.
