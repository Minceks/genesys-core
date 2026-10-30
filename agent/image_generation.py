"""Generated imagery for new projects. A failed image must never fail a build."""
import base64
import logging
import os
import re
import struct
import zlib

from .model_context import reconcile_model_budget, reserve_model_budget
from .progress import model_request_timeout

logger = logging.getLogger(__name__)
IMAGE_PATH = re.compile(r'public/images/[a-z0-9][a-z0-9-]*\.png')
SIZES = {'1536x1024', '1024x1536', '1024x1024'}
MAX_IMAGE_BYTES = 8_000_000
RESERVED_TOKENS = 12000  # Provider usage settles this once the image returns.
IMAGE_RULES = ('Original artwork or photography of the subject only. No text, lettering, logos, watermarks, brand marks '
               'or identifiable real people. ')


def enabled():
    return os.getenv('GENESYS_IMAGE_GENERATION', '1') != '0'


def planned_images(plan):
    """Valid, bounded image requests. The plan is model output, so nothing is trusted."""
    limit = max(0, min(6, int(os.getenv('GENESYS_IMAGE_LIMIT', '3'))))
    images, seen = [], set()
    for item in plan.get('generatedImages') or []:
        if not isinstance(item, dict):
            continue
        path, prompt, alt = item.get('path'), item.get('prompt'), item.get('alt')
        if not (isinstance(path, str) and IMAGE_PATH.fullmatch(path) and path not in seen):
            continue
        if not (isinstance(prompt, str) and prompt.strip() and isinstance(alt, str) and alt.strip()):
            continue
        seen.add(path)
        size = item.get('size') if item.get('size') in SIZES else '1536x1024'
        images.append({'path': path, 'prompt': prompt.strip()[:1500], 'alt': alt.strip()[:200], 'size': size})
    return images[:limit]


def placeholder():
    """A neutral 1x1 PNG, so a failed image crops to a quiet panel instead of a broken icon."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    pixel = zlib.compress(bytes((0, 0xe2, 0xe8, 0xf0)))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', pixel) + chunk(b'IEND', b''))


def generate(client, image):
    reservation = reserve_model_budget(RESERVED_TOKENS)
    response = client.images.generate(
        model=os.getenv('GENESYS_IMAGE_MODEL', 'gpt-image-2.5-flare'),
        prompt=IMAGE_RULES + image['prompt'], size=image['size'],
        quality=os.getenv('GENESYS_IMAGE_QUALITY', 'medium'), n=1,
        timeout=model_request_timeout(120))
    reconcile_model_budget(reservation, getattr(getattr(response, 'usage', None), 'total_tokens', None))
    from .user_allowance import record
    record(response)
    data = base64.b64decode(response.data[0].b64_json)
    if not data.startswith(b'\x89PNG') or len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Generated image was not a usable PNG')
    return data


def produce_image(client, image, save):
    try:
        data = generate(client, image)
    except Exception as error:
        logger.warning('image_generation_failed path=%s type=%s reason=%s', image['path'], type(error).__name__, str(error)[:250])
        data = placeholder()
    try:
        save(image['path'], data)
    except Exception as error:
        logger.warning('image_save_failed path=%s type=%s', image['path'], type(error).__name__)
