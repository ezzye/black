import os
import time
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# Retrieve your BFL API key from environment variables
BFL_API_KEY = os.environ.get("BFL_API_KEY")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        prompt = request.form['prompt']

        # Submit image generation request to BFL API
        generation_request = requests.post(
            'https://api.bfl.ml/v1/flux-pro-1.1',
            headers={
                'accept': 'application/json',
                'x-key': BFL_API_KEY,
                'Content-Type': 'application/json',
            },
            json={
                'prompt': prompt,
                'width': 512,
                'height': 512,
            },
        ).json()

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
            # Save the image to the static folder
            image_filename = f"generated_image_{request_id}.png"
            image_path = os.path.join('static', image_filename)
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
            return render_template('index.html', image_filename=image_filename)
        else:
            return render_template('index.html', error="Error fetching generated image.")

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)