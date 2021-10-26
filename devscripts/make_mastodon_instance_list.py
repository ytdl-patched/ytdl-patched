# coding: utf-8
from __future__ import unicode_literals, print_function

import sys
import os
import re

sys.path[:0] = ['.']

from yt_dlp.utils import ExtractorError
from yt_dlp.extractor.common import InfoExtractor
from test.helper import FakeYDL


class TestIE(InfoExtractor):
    pass


ie = TestIE(FakeYDL({'verbose': False}))
script_id = 'mastodon'
results = set()


def sanitize_hostname(hostname):
    # trim trailing slashes
    hostname = re.sub(r'[/\\]+$', '', hostname)
    # trim port number
    hostname = re.sub(r':\d+$', '', hostname)
    return hostname


instance_social_api_key = os.environ['INSTANCE_SOCIAL_API_SECRET']
if not instance_social_api_key:
    raise ExtractorError('You must set INSTANCE_SOCIAL_API_SECRET to work')

min_id = None
while True:
    url = 'https://instances.social/api/1.0/instances/list'
    if min_id:
        url = f'{url}?min_id={min_id}'
    data = ie._download_json(
        url, script_id, note=f'Paging {min_id}, len(results)={len(results)}',
        headers={'Authorization': f'Bearer {instance_social_api_key}'})
    for instance in data['instances']:
        results.add(sanitize_hostname(instance['name']))
    min_id = data['pagination'].get('next_id')
    if not min_id:
        break

joinmastodon_categories = [
    'general', 'regional', 'art', 'music',
    'journalism', 'activism', 'lgbt', 'games',
    'tech', 'academia', 'adult', 'humor',
    'furry', 'food'
]
for category in joinmastodon_categories:
    url = f'https://api.joinmastodon.org/servers?category={category}'
    data = ie._download_json(
        url, script_id, note=f'Category {category}, len(results)={len(results)}')
    for instance in data:
        results.add(sanitize_hostname(instance['domain']))

if True:
    try:
        url = 'https://the-federation.info/graphql?query=query%20Platform(%24name%3A%20String!)%20%7B%0A%20%20platforms(name%3A%20%24name)%20%7B%0A%20%20%20%20name%0A%20%20%20%20code%0A%20%20%20%20displayName%0A%20%20%20%20description%0A%20%20%20%20tagline%0A%20%20%20%20website%0A%20%20%20%20icon%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20nodes(platform%3A%20%24name)%20%7B%0A%20%20%20%20id%0A%20%20%20%20name%0A%20%20%20%20version%0A%20%20%20%20openSignups%0A%20%20%20%20host%0A%20%20%20%20platform%20%7B%0A%20%20%20%20%20%20name%0A%20%20%20%20%20%20icon%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20countryCode%0A%20%20%20%20countryFlag%0A%20%20%20%20countryName%0A%20%20%20%20services%20%7B%0A%20%20%20%20%20%20name%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20statsGlobalToday(platform%3A%20%24name)%20%7B%0A%20%20%20%20usersTotal%0A%20%20%20%20usersHalfYear%0A%20%20%20%20usersMonthly%0A%20%20%20%20localPosts%0A%20%20%20%20localComments%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20statsNodes(platform%3A%20%24name)%20%7B%0A%20%20%20%20node%20%7B%0A%20%20%20%20%20%20id%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20usersTotal%0A%20%20%20%20usersHalfYear%0A%20%20%20%20usersMonthly%0A%20%20%20%20localPosts%0A%20%20%20%20localComments%0A%20%20%20%20__typename%0A%20%20%7D%0A%7D%0A&operationName=Platform&variables=%7B%22name%22%3A%22mastodon%22%7D'
        data = ie._download_json(
            url, script_id, note=f'Scraping https://the-federation.info/mastodon, len(results)={len(results)}',
            headers={
                'content-type': 'application/json, application/graphql',
                'accept': 'application/json, application/graphql',
            })
        for instance in data['data']['nodes']:
            results.add(sanitize_hostname(instance['host']))
    except BaseException:
        pass

ie.to_screen(f'{script_id}: len(results)={len(results)}')

if not results:
    raise ExtractorError('no instances found')

results = {x.encode('idna').decode('utf8') for x in results}
ie.to_screen(f'{script_id}: converted domain names to punycode, len(results)={len(results)}')

results = {x for x in results if '.' in x}
ie.to_screen(f'{script_id}: excluded domain names without dot, len(results)={len(results)}')

results = {x for x in results if not (x.endswith('.ngrok.io') or x.endswith('.localhost.run') or x.endswith('.serveo.net'))}
ie.to_screen(f'{script_id}: excluded temporary domain names, len(results)={len(results)}')

# for it in list(results):
#     try:
#         if not socket.getaddrinfo(it, None):
#             raise ValueError()
#     except BaseException:
#         results.remove(it)

# ie.to_screen(f'{script_id}: removed unavailable domains, len(results)={len(results)}')

lf = '\n'
pycode = f'''# coding: utf-8
# AUTOMATICALLY GENERATED FILE. DO NOT EDIT.
# Generated by ./devscripts/make_mastodon_instance_list.py
from __future__ import unicode_literals

instances = {{
    # list of instances here
{lf.join(f'    "{r}",' for r in sorted(results))}
}}

__all__ = ['instances']
'''

with open('./yt_dlp/extractor/mastodon/instances.py', 'w') as w:
    w.write(pycode)