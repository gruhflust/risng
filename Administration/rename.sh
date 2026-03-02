#!/bin/bash
# Replace occurrences of a string with another string in various files starting from the current directory.

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <old_string> <new_string>"
    exit 1
fi

OLD_STRING="$1"
NEW_STRING="$2"

OLD_ESC=$(printf '%s' "$OLD_STRING" | sed -e 's/[\\&/]/\\&/g')
NEW_ESC=$(printf '%s' "$NEW_STRING" | sed -e 's/[\\&/]/\\&/g')

# Search from the current directory
find . -type f \( \
    -name '*.py' -o \
    -name '*.yml' -o \
    -name '*.j2' -o \
    -name '*.md' -o \
    -name '*.hosts' -o \
    -name 'hosts' -o \
    -name '*.cfg' \
\) | while read -r file; do
    if grep -qF "$OLD_STRING" "$file"; then
        COUNT=$(grep -oF "$OLD_STRING" "$file" | wc -l)
        sed -i "s/${OLD_ESC}/${NEW_ESC}/g" "$file"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - Replaced $COUNT occurrence(s) in $file"
    fi
done