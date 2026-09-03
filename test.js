import 'dotenv/config';
import fs from 'fs';
import FormData from 'form-data';
import fetch from 'node-fetch';
const API_KEY = process.env.AI_API_KEY;
const API_URL = process.env.AI_API_URL || 'http://localhost';
async function getPrediction(imagePath) {
    const formData = new FormData();
    formData.append('file', fs.createReadStream(imagePath));

    const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        body: formData,
        headers: {
            ...formData.getHeaders(),
            'X-API-Key': API_KEY
        }
    });

    console.log(await response.json());
}

getPrediction("./auckland_15_32258_19983.jpg");