# AI Model Hosting API

A production-ready, containerized AI image classification API with comprehensive security features, built with Flask, Docker, and ngrok.

##  Features

- **AI Image Classification** - EfficientNet-based model for binary image classification
- **ONNX Runtime** - Optimized inference with ONNX
- **Containerized** - Fully Dockerized with docker-compose
- **Secure** - API key authentication, rate limiting, input validation
- **Public Access** - ngrok tunnel for secure public access without exposing your IP
- **Reverse Proxy** - nginx for load balancing and additional security
- **Auto-restart** - Services automatically restart on failure
- **CORS Enabled** - Ready for web application integration

##  Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose
- ngrok account (free tier available at https://ngrok.com)
- Python 3.10+ (for local development)
- Node.js (for testing)

##  Architecture

```
User → ngrok Tunnel → nginx Proxy → Flask API → ONNX Model
        (HTTPS)        (Port 80)    (Port 5001)  (128x128 images)
```

### Components:

1. **Flask API Server** (`server.py`) - Main application with API endpoints
2. **nginx Reverse Proxy** - Load balancing, rate limiting, security headers
3. **ngrok Tunnel** - Secure public access without exposing your IP
4. **ONNX Model** - Optimized AI inference engine

##  Project Structure

```
ai-hosting/
├── server.py              # Flask API server
├── model_arc.py          # AI model architecture and ONNX inference
├── onnx_inference.py     # ONNX inference utilities
├── export_model.py       # Model export script
├── Dockerfile            # Container image definition
├── docker-compose.yml    # Multi-container orchestration
├── nginx.conf            # nginx reverse proxy configuration
├── ngrok.yml             # ngrok tunnel configuration
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create from .env.example)
├── .env.example          # Environment variables template
├── package.json          # Node.js dependencies for testing
├── test.js               # API testing script
└── models/
    ├── All_nz_regions_model.onnx  # ONNX model file
    └── All_nz_regions_model.pth   # PyTorch model file
```

##  Setup

### 1. Clone Repository

```bash
git clone https://github.com/seCRet-blip/ai-hosting.git
cd ai-hosting
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Generate a secure API key
API_KEY=your-secure-api-key-here

# Get your ngrok auth token from https://dashboard.ngrok.com
NGROK_AUTHTOKEN=your-ngrok-token-here
```

**Generate secure API key:**
```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using PowerShell
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

### 3. Build and Start Services

```bash
# Build and start all containers
docker-compose up -d --build

# Check container status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Get Your Public URL

```bash
# View ngrok logs to get your public URL
docker-compose logs ngrok

# Or visit the ngrok web interface
# http://localhost:4040
```

Look for output like:
```
started tunnel    url=https://abc123.ngrok-free.app
```

##  Testing

### Health Check

```bash
curl https://your-ngrok-url.ngrok-free.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### Prediction Test

```bash
curl -X POST \
  -F "file=@your-image.jpg" \
  -H "X-API-Key: your-api-key-here" \
  https://your-ngrok-url.ngrok-free.app/predict
```

Expected response:
```json
{
  "prediction": 0,
  "probabilities": [0.8234, 0.1766],
  "confidence": 0.8234
}
```

### Using Test Script

```bash
# Install Node.js dependencies
npm install

# Update test.js with your ngrok URL and API key
# Then run:
node test.js
```

##  Security Features

### 1. API Key Authentication
- All `/predict` requests require `X-API-Key` header
- Health checks remain open for monitoring

### 2. Rate Limiting
- **General API**: 20 requests/minute per IP
- **Predictions**: 5 requests/minute per IP (stricter)
- **Health checks**: 30 requests/minute
- Burst allowance for traffic spikes

### 3. Connection Limits
- Max 10 concurrent connections per IP (general)
- Max 5 concurrent connections for predictions

### 4. Input Validation
- **File type check**: Only images (png, jpg, jpeg, gif, bmp, webp)
- **File size limit**: 10MB maximum
- **Image dimension check**: 4096x4096 maximum
- **Image verification**: Validates image format and integrity
- **Empty file detection**

### 5. Security Headers
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-XSS-Protection` - XSS attack protection
- `Referrer-Policy` - Controls referrer information

### 6. DDoS Protection
- Request rate limiting at nginx level
- Connection limits per IP
- Buffer size limits
- Timeout configurations
- ngrok's built-in DDoS protection

##  API Endpoints

### GET `/`
Returns API information and available endpoints.

**Response:**
```json
{
  "message": "AI Model API is running!",
  "endpoints": {
    "health": "/health",
    "predict": "/predict (POST with file upload)"
  },
  "note": "API key required for /predict endpoint"
}
```

### GET `/health`
Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### POST `/predict`
Image classification endpoint.

**Headers:**
- `X-API-Key`: Your API key (required)
- `Content-Type`: multipart/form-data

**Body:**
- `file`: Image file (max 10MB)

**Response:**
```json
{
  "prediction": 0,
  "probabilities": [0.8234, 0.1766],
  "confidence": 0.8234
}
```

**Error Responses:**
- `401`: Invalid or missing API key
- `400`: Invalid file or file type
- `413`: File too large
- `429`: Rate limit exceeded
- `500`: Internal server error

##  Usage in Web Applications

###  Important Security Note

**Never expose your API key in frontend JavaScript!** The key will be visible in:
- Browser DevTools
- Page source
- Network requests

###  Secure Implementation

Create a backend proxy to hide your API key:

```javascript
// backend.js (Your website's backend server)
import express from 'express';
import fetch from 'node-fetch';
import FormData from 'form-data';

const app = express();
const AI_API_KEY = process.env.AI_API_KEY;  // Secure!
const AI_API_URL = 'https://your-ngrok-url.ngrok-free.app';

app.post('/api/predict', upload.single('image'), async (req, res) => {
    const formData = new FormData();
    formData.append('file', req.file.buffer, req.file.originalname);

    const response = await fetch(`${AI_API_URL}/predict`, {
        method: 'POST',
        body: formData,
        headers: {
            ...formData.getHeaders(),
            'X-API-Key': AI_API_KEY  // Hidden from users
        }
    });

    res.json(await response.json());
});
```

```javascript
// frontend.js (Runs in user's browser - Safe)
async function predictImage(imageFile) {
    const formData = new FormData();
    formData.append('image', imageFile);
    
    // Call YOUR backend, not the AI API directly
    const response = await fetch('/api/predict', {
        method: 'POST',
        body: formData
        // No API key needed!
    });
    
    return await response.json();
}
```

##  Management Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs ai-model-api
docker-compose logs nginx-proxy
docker-compose logs ngrok

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# Check container status
docker-compose ps

# Access ngrok dashboard
# Open http://localhost:4040 in browser
```

##  Monitoring

### ngrok Dashboard
Access at http://localhost:4040 to view:
- Active tunnel URL
- Request history
- Response times
- Traffic statistics

### Container Logs
```bash
# Follow all logs
docker-compose logs -f

# Check for errors
docker-compose logs | grep -i error

# View last 100 lines
docker-compose logs --tail 100
```

##  Troubleshooting

### ngrok authentication failed
**Issue:** ngrok container shows authentication error

**Solution:**
1. Get your auth token from https://dashboard.ngrok.com
2. Update `.env` file with correct `NGROK_AUTHTOKEN`
3. Restart: `docker-compose restart ngrok`

### API returns 401 Unauthorized
**Issue:** Invalid or missing API key

**Solution:**
- Ensure `X-API-Key` header is included in request
- Verify API key matches the one in `.env` file
- Check for extra spaces or dashes in the key

### Rate limit exceeded
**Issue:** Too many requests

**Solution:**
- Wait 1 minute for rate limit to reset
- Reduce request frequency
- Upgrade nginx rate limits in `nginx.conf` if needed

### Model not loaded
**Issue:** Health check shows `"model_loaded": false`

**Solution:**
1. Check if model files exist in `models/` directory
2. View logs: `docker-compose logs ai-model-api`
3. Rebuild: `docker-compose up -d --build`

### Container keeps restarting
**Issue:** Container exits immediately

**Solution:**
```bash
# Check container logs
docker-compose logs [service-name]

# Common causes:
# - Invalid configuration file
# - Missing environment variables
# - Port conflicts
```

##  Updating the Model

1. Export new ONNX model:
```bash
python export_model.py
```

2. Rebuild containers:
```bash
docker-compose down
docker-compose up -d --build
```

##  Scaling

### Increase Rate Limits

Edit `nginx.conf`:
```nginx
# Change from 5r/m to 20r/m
limit_req_zone $binary_remote_addr zone=predict_limit:10m rate=20r/m;
```

Restart:
```bash
docker-compose restart nginx-proxy
```

### Add More Workers

Edit `server.py`:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, threaded=True, processes=4)
```

### Permanent ngrok URL

Upgrade to ngrok paid plan ($8/month) for:
- Custom subdomain
- Reserved domain
- No connection limits

##  Production Deployment

### Best Practices

1. **Change default API key** - Generate a strong, unique key
2. **Set up user authentication** - Add your own user system
3. **Enable HTTPS only** - Disable HTTP in nginx
4. **Implement logging** - Add request logging for audit
5. **Monitor usage** - Track API usage per user
6. **Set up alerts** - Get notified of errors/downtime
7. **Regular backups** - Backup model and configuration
8. **Keep updated** - Regular security updates

### Cloud Deployment

For production, consider deploying to:
- **AWS ECS/Fargate** - Scalable container hosting
- **Google Cloud Run** - Serverless containers
- **Azure Container Instances** - Simple container hosting
- **Railway/Render** - Easy deployment platforms

##  Model Details

- **Architecture**: EfficientNet-B3
- **Input Size**: 128x128 RGB images
- **Output**: Binary classification (2 classes)
- **Framework**: PyTorch → ONNX
- **Preprocessing**: 
  - Resize to 128x128
  - Normalize: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]

##  Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

##  License

This project is private. All rights reserved.

##  Support

For issues or questions:
1. Check the Troubleshooting section
2. Review container logs: `docker-compose logs`
3. Open an issue on GitHub

##  Acknowledgments

- Flask - Web framework
- ONNX Runtime - Optimized inference
- nginx - Reverse proxy
- ngrok - Secure tunneling
- Docker - Containerization

---
