#!/usr/bin/env python3
"""Validate declared public export claims offline; stage only, never authorize reuse."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 10_000
ID = re.compile(r'[A-Za-z0-9_~]{6,120}', re.ASCII)
SOURCE_KEYS = {'format', 'version', 'source_type', 'issued_at', 'terms_ref',
               'verification_proof_ref', 'records'}
RECORD_KEYS = {'id', 'name', 'description', 'verified_public', 'source_url'}


def canonical(value):
    """UTF-8, sorted keys, compact separators, no trailing newline or NaN."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def text(value, limit):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError('Invalid or oversized text')
    if any(unicodedata.category(char).startswith('C') for char in value):
        raise ValueError('Control or non-text character')
    value = unicodedata.normalize('NFC', value).strip()
    if not value or len(value) > limit:
        raise ValueError('Empty or oversized text')
    return value


def keys(value, allowed, required):
    if not isinstance(value, dict) or set(value) - allowed or required - set(value):
        raise ValueError('Unexpected or missing fields')


def validate(data):
    """Validate syntax/claims only. References are opaque, unverified strings."""
    keys(data, SOURCE_KEYS, SOURCE_KEYS)
    if (data['format'] != 'public-chatgpt-directory-export'
            or type(data['version']) is not int or data['version'] != 1
            or data['source_type'] != 'official_public_chatgpt_directory'):
        raise ValueError('Unsupported export format, version or source type')
    issued = text(data['issued_at'], 20)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', issued):
        raise ValueError('Expected UTC issue timestamp')
    datetime.strptime(issued, '%Y-%m-%dT%H:%M:%SZ')
    source = {key: data[key] for key in ('format', 'version', 'source_type')}
    source.update(issued_at=issued, terms_ref=text(data['terms_ref'], 1024),
                  verification_proof_ref=text(data['verification_proof_ref'], 1024),
                  verification_status='unverified_claims')
    records = data['records']
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError('Invalid or oversized record list')
    entries, seen = [], set()
    for record in records:
        keys(record, RECORD_KEYS, RECORD_KEYS - {'description'})
        identifier = record['id']
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            raise ValueError('Invalid public plugin ID')
        if identifier in seen:
            raise ValueError('Duplicate public plugin ID')
        seen.add(identifier)
        url = 'https://chatgpt.com/plugins/' + identifier
        if record['source_url'] != url or record['verified_public'] is not True:
            raise ValueError('Noncanonical link or missing public-scope claim')
        entry = {'id': identifier, 'name': text(record['name'], 200),
                 'source_url': url, 'verified_public': True}
        if 'description' in record:
            entry['description'] = text(record['description'], 4000)
        entries.append(entry)
    entries.sort(key=lambda entry: entry['id'])
    artifact = {'format': 'public-chatgpt-directory-staging', 'version': 1,
                'publication_authorized': False, 'source': source, 'entries': entries,
                'counts': {'entries': len(entries),
                           'with_description': sum('description' in e for e in entries)}}
    artifact['sha256'] = hashlib.sha256(canonical(artifact)).hexdigest()
    return artifact


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Nonstandard JSON constant')


def stage(input_path, output_path):
    """Validate fully before touching output; replace via same-directory temp file."""
    if input_path.resolve() == output_path.resolve():
        raise ValueError('Input and output must differ')
    with input_path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Input exceeds byte limit')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
        artifact = validate(data)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('Invalid JSON encoding or nesting') from error
    encoded = canonical(artifact)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output_path.parent, prefix='.stage-',
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'counts': artifact['counts'], 'sha256': artifact['sha256'],
            'publication_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path, help='Local UTF-8 export JSON')
    parser.add_argument('--output', required=True, type=Path, help='Local staging JSON')
    args = parser.parse_args()
    try:
        summary = stage(args.input, args.output)
    except (ValueError, OSError, RecursionError):
        # Do not echo input contents, sensitive fields or filesystem error details.
        print('BLOCKED: invalid snapshot or staging I/O failure', file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
