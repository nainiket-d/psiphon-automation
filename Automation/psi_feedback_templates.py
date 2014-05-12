#!/usr/bin/python
# coding=utf-8
#
# Copyright (c) 2011, Psiphon Inc.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import yaml
import json
import hashlib

FEEDBACK_LANGUAGES = [
    'en',
    'fa',
    'ar',
    'tr',
    'zh',
    'uz@cyrillic',
    'uz@Latn',
    'ru',
    'kk',
    'az',
    'tk',
    'th',
    'ug@Latn',
    'es',
    'vi',
    'nb'
]


def make_feedback_html():
    lang = {}
    for language in FEEDBACK_LANGUAGES:
        lang[language] = get_language_from_template(language)

    feedback_path = os.path.join('.', 'FeedbackSite', 'feedback.html')
    feedback_template_path = os.path.join('.', 'FeedbackSite', 'Templates', 'feedback.html.tpl')

    format = {
        "langJSON": json.JSONEncoder().encode(lang),
        "speed": hashlib.md5(lang['en']['speed_title']).hexdigest(),
        "speed_en": lang['en']['speed_title'],
        "connectivity": hashlib.md5(lang['en']['connectivity_title']).hexdigest(),
        "connectivity_en": lang['en']['connectivity_title'],
        "compatibility": hashlib.md5(lang['en']['compatibility_title']).hexdigest(),
        "compatibility_en": lang['en']['compatibility_title']
    }

    with open(feedback_template_path) as f:
        rendered_feedback_html = (f.read()).format(**format)

    # Make line endings consistently Unix-y.
    rendered_feedback_html = rendered_feedback_html.replace('\r\n', '\n')

    # Insert a comment warning about the file being auto-generated. This
    # comment should go below the `DOCTYPE` line to avoid potential problems
    # (see http://stackoverflow.com/a/4897850/729729).
    # Don't start at the very beginning in case there are leading newlines.
    idx = rendered_feedback_html.index('\n', 5)
    rendered_feedback_html = \
        rendered_feedback_html[:idx] \
        + '\n\n<!-- THIS FILE IS AUTOMATICALLY GENERATED. DO NOT MODIFY DIRECTLY. -->\n' \
        + rendered_feedback_html[idx:]

    with open(feedback_path, 'wb') as f:
        f.write(rendered_feedback_html)


def get_language_from_template(language):
    path = os.path.join('.', 'FeedbackSite', 'Templates', language + '.yaml')
    with open(path) as f:
        return yaml.load(f.read())[language]


if __name__ == '__main__':
    make_feedback_html()
