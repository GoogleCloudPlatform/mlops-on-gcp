import base64
import json


IMAGE_PATH = 'grace_hopper.jpg'
MODEL_SIGNATURE = 'serving_preprocess'
JSON_REQUEST_PATH = 'request-body.json'

def _get_image_bytes(image_path):
    """
    Reads image bytes from a file.
    """

    with open(image_path, 'rb') as f:
        image_content = f.read()

    return image_content

def _prepare_predict_request(image_path):
    """
    Prepares a JSON representation of TF Serving
    Predict request.
    """

    image_bytes = _get_image_bytes(image_path)
    instances = [{'b64': base64.b64encode(image_bytes).decode('utf-8')}]
    request_body = {
        'signature_name': 'serving_preprocess',
        'instances': instances
    }
    

    return request_body


if __name__ == '__main__':
    predict_request = _prepare_predict_request(IMAGE_PATH)
    
    with open(JSON_REQUEST_PATH, 'w') as f:
        json.dump(predict_request, f)