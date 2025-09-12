"""
Update or insert SPDX headers in Python files.

- Ensures SPDX-FileCopyrightText has the current year.
- Ensures SPDX-License-Identifier is set to BSD-3-Clause.
"""

import datetime
import re
from pathlib import Path

CURRENT_YEAR = datetime.datetime.now().year
COPYRIGHT_TEXT = (
    f'# SPDX-FileCopyrightText: {CURRENT_YEAR} Badgery contributors '
    '<https://github.com/enhantica/badgery>'
)
LICENSE_TEXT = '# SPDX-License-Identifier: MIT'


def update_spdx_header(file_path: Path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Patterns to match existing SPDX lines
    copy_re = re.compile(r'^#\s*SPDX-FileCopyrightText:.*$')
    lic_re = re.compile(r'^#\s*SPDX-License-Identifier:.*$')

    new_lines = []
    found_copy = False
    found_lic = False

    for line in lines:
        if copy_re.match(line):
            new_lines.append(COPYRIGHT_TEXT + '\n')
            found_copy = True
        elif lic_re.match(line):
            new_lines.append(LICENSE_TEXT + '\n')
            found_lic = True
        else:
            new_lines.append(line)

    # If not found, insert at top
    insert_pos = 0
    if not found_copy:
        new_lines.insert(insert_pos, COPYRIGHT_TEXT + '\n')
        insert_pos += 1
    if not found_lic:
        new_lines.insert(insert_pos, LICENSE_TEXT + '\n')
        insert_pos += 1
        new_lines.insert(insert_pos, '\n')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def main():
    """Recursively update or insert SPDX headers in all Python files
    under the 'src' directory, skipping files located in virtual
    environment folders ('venv' or '.venv')."""
    for py_file in Path('src').rglob('*.py'):
        if 'venv' in py_file.parts or '.venv' in py_file.parts:
            continue
        update_spdx_header(py_file)


if __name__ == '__main__':
    main()
