"""Validate recap polishing handoff; this does not assess editorial quality."""
import hashlib
import json
import sys
from pathlib import Path

CHECKS = (
    'humanizer_completed', 'shuorenhua_annotation_completed',
    'issues_resolved', 'semantic_fidelity_checked',
    'voice_and_continuity_readthrough',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_text(path):
    """Remove only quote lines in explicit narration blocks; protect everything else."""
    output = []
    narration = False
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        stripped = line.strip()
        if stripped.startswith('**旁白**'):
            if stripped not in ('**旁白**', '**旁白**：', '**旁白**:'):
                raise ValueError('Narration marker must be on its own line')
            narration = True
            output.append(line)
        elif narration and stripped.startswith('>'):
            continue
        else:
            if stripped:
                narration = False
            output.append(line)
    return '\n'.join(output)


def validate(script):
    errors = []
    base = script.parent
    receipt = base / 'narration-review.json'
    if not script.is_file():
        return ['Script is missing']
    if not receipt.is_file():
        return ['Review receipt is missing; complete Layer 4 before handoff']
    try:
        data = json.loads(receipt.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or data.get('schema_version') != 1:
            return ['Unsupported review receipt schema']
        if data.get('script_sha256') != digest(script):
            errors.append('Review is stale: current script hash differs')

        def file_check(label, name, sha):
            if not isinstance(name, str) or not name.strip():
                errors.append(f'{label}: path is missing')
                return None
            path = Path(name)
            if not path.is_absolute():
                path = base / path
            if not path.is_file():
                errors.append(f'{label}: file is missing')
                return None
            if sha != digest(path):
                errors.append(f'{label}: hash differs or is missing')
            return path

        before = file_check('Before snapshot', data.get('before_path'), data.get('before_sha256'))
        notes = file_check('Review notes', data.get('notes_path'), data.get('notes_sha256'))
        if before and before.resolve() == script.resolve():
            errors.append('Before snapshot must be separate from the current script')
        if notes and not notes.read_text(encoding='utf-8-sig').strip():
            errors.append('Review notes are empty')
        skills = data.get('skills', {})
        if not isinstance(skills, dict):
            skills = {}
        for name in ('humanizer-zh', 'shuorenhua'):
            item = skills.get(name, {})
            if not isinstance(item, dict):
                item = {}
            path = file_check(name, item.get('path'), item.get('sha256'))
            if path:
                import re
                if not re.search(r'^name:\s*[\"\']?' + re.escape(name) + r'[\"\']?\s*$',
                                 path.read_text(encoding='utf-8-sig'), re.MULTILINE):
                    errors.append(f'{name}: dependency skill name does not match')
        checks = data.get('checks', {})
        if not isinstance(checks, dict):
            checks = {}
        for name in CHECKS:
            if checks.get(name) is not True:
                errors.append(f'Incomplete review: {name}')
        if before and protected_text(before) != protected_text(script):
            errors.append('Protected non-narration fields changed; return to the responsible layer')
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f'Cannot validate review: {exc}')
    return errors


def main():
    if len(sys.argv) != 2:
        print('Usage: python validate_narration_review.py <recap-script.md>')
        return 1
    errors = validate(Path(sys.argv[1]).resolve())
    for error in errors:
        print('ERR: ' + error)
    print('FAILED' if errors else 'OK: review matches current script; editorial quality requires actual review')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
