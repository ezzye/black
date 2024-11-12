import os
import time
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# Retrieve your BFL API key from environment variables
BFL_API_KEY = os.environ.get("BFL_API_KEY")

# Mapping of endpoints and their parameters
ENDPOINTS = {
    'flux-pro-1.1': {
        'url': 'https://api.bfl.ml/v1/flux-pro-1.1',
        'params': ['prompt', 'width', 'height', 'prompt_upsampling', 'seed', 'safety_tolerance', 'output_format']
    },
    'flux-pro': {
        'url': 'https://api.bfl.ml/v1/flux-pro',
        'params': ['prompt', 'width', 'height', 'steps', 'prompt_upsampling', 'seed', 'guidance', 'safety_tolerance', 'interval', 'output_format']
    },
    'flux-dev': {
        'url': 'https://api.bfl.ml/v1/flux-dev',
        'params': ['prompt', 'width', 'height', 'steps', 'prompt_upsampling', 'seed', 'guidance', 'safety_tolerance', 'output_format']
    },
    'flux-pro-1.1-ultra': {
        'url': 'https://api.bfl.ml/v1/flux-pro-1.1-ultra',
        'params': ['prompt', 'seed', 'aspect_ratio', 'safety_tolerance', 'output_format', 'raw']
    },
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        endpoint_key = request.form.get('endpoint')
        if endpoint_key not in ENDPOINTS:
            return render_template('index.html', error="Invalid endpoint selected.")
        endpoint_info = ENDPOINTS[endpoint_key]
        endpoint_url = endpoint_info['url']
        endpoint_params = endpoint_info['params']

        # Build the payload
        payload = {}
        for param in endpoint_params:
            if param in ['prompt_upsampling', 'raw']:
                value = param in request.form  # True if checked, False if not
                payload[param] = value
            else:
                value = request.form.get(param)
                if value:
                    # Convert types as necessary
                    if param in ['width', 'height', 'steps', 'seed', 'safety_tolerance']:
                        value = int(value)
                    elif param in ['guidance', 'interval']:
                        value = float(value)
                    # else, keep as string
                    payload[param] = value

        # Submit image generation request to BFL API
        headers = {
            'accept': 'application/json',
            'x-key': BFL_API_KEY,
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(endpoint_url, headers=headers, json=payload)
            generation_request = response.json()
        except Exception as e:
            return render_template('index.html', error="Error communicating with the API.")

        if 'id' not in generation_request:
            error_message = generation_request.get('message', 'Error creating image generation request.')
            return render_template('index.html', error=error_message)

        request_id = generation_request["id"]

        # Poll for the result
        max_attempts = 60  # Timeout after 60 attempts (about 1 minute)
        attempts = 0
        while attempts < max_attempts:
            time.sleep(1)
            result = requests.get(
                'https://api.bfl.ml/v1/get_result',
                headers={
                    'accept': 'application/json',
                    'x-key': BFL_API_KEY,
                },
                params={
                    'id': request_id,
                },
            ).json()
            if result["status"] == "Ready":
                image_url = result['result']['sample']
                break
            elif result["status"] == "Error":
                return render_template('index.html', error="Error generating image.")
            else:
                print(f"Status: {result['status']}")
                attempts += 1
                continue
        else:
            return render_template('index.html', error="Image generation timed out.")

        # Fetch the generated image
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            image_bytes = image_response.content
            # Determine the file extension based on the output format
            file_extension = payload.get('output_format', 'png')
            image_filename = f"generated_image_{request_id}.{file_extension}"
            image_path = os.path.join('static', image_filename)
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
            return render_template('index.html', image_filename=image_filename)
        else:
            return render_template('index.html', error="Error fetching generated image.")

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)