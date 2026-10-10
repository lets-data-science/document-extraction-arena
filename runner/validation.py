"""Bounded, explicit validation for untrusted uploads and provider responses."""
import io
import json
import re
import warnings
from datetime import date
from PIL import Image, UnidentifiedImageError
from learner.normalize import to_decimal

SCALAR_FIELDS = ('invoice_number', 'vendor', 'invoice_date', 'currency', 'subtotal', 'tax', 'total')


def load_json(data):
    if len(data) > 256_000:
        raise ValueError('The answer key must be smaller than 256 KB.')
    def reject(value):
        raise ValueError('JSON numbers must be finite.')
    try:
        value = json.loads(data, parse_constant=reject)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise ValueError('Use a valid JSON object with finite numbers.') from exc
    if not isinstance(value, dict):
        raise ValueError('The invoice must be a JSON object.')
    return value


def validate_invoice(value, *, partial=False):
    if not isinstance(value, dict):
        raise ValueError('The invoice must be an object.')
    for key in (*SCALAR_FIELDS, 'line_items'):
        if partial and value.get(key) is None:
            continue
        if key not in value:
            raise ValueError(f'Missing field: {key}.')
        field = value[key]
        if key in ('subtotal', 'tax', 'total'):
            if to_decimal(field) is None:
                raise ValueError(f'{key} must be a finite decimal number without currency symbols.')
        elif key == 'line_items':
            if not isinstance(field, list) or len(field) > 100:
                raise ValueError('line_items must be a list of at most 100 rows.')
            for i, row in enumerate(field, 1):
                if not isinstance(row, dict) or not isinstance(row.get('description'), str) or not 0 < len(row['description'].strip()) <= 300:
                    raise ValueError(f'Line {i} needs a description of 1–300 characters.')
                for name in ('quantity', 'unit_price', 'amount'):
                    if to_decimal(row.get(name)) is None:
                        raise ValueError(f'Line {i}: {name} must be a finite decimal number.')
        elif not isinstance(field, str) or not 0 < len(field.strip()) <= 300:
            raise ValueError(f'{key} must be text of 1–300 characters.')
        elif key == 'invoice_date':
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', field):
                    raise ValueError()
                date.fromisoformat(field)
            except ValueError as exc:
                raise ValueError('invoice_date must be a real date in YYYY-MM-DD format.') from exc
        elif key == 'currency' and not re.fullmatch(r'[A-Z]{3}', field):
            raise ValueError('currency must be a three-letter uppercase code, such as USD.')
    return value


def validate_image(data):
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError('Choose a PNG or JPEG smaller than 10 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('PNG', 'JPEG') or image.width * image.height > 20_000_000:
                    raise ValueError('Use a PNG or JPEG with at most 20 million pixels.')
                fmt = image.format
                image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('This file is not a readable PNG or JPEG image.') from exc
    return '.png' if fmt == 'PNG' else '.jpg'
