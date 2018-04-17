import requests
import os
import json
from collections import Mapping
import re


def merge_dict_inplace(src, dst, overwrite_dst=True):
    """
    recursively merge dict src into dst

    Parameters
    ----------
    src: Mapping
        source dict, will be left as-is
    dst: Mapping
        destination dict, will be modified
    overwrite_dst: bool
        whether to overwrite existing (scalar) values in dst or ignore them
    """
    for k,v in src.items():
        if not k in dst:
            dst[k] = v
        elif isinstance(v, list) and isinstance(dst[k], list):
            dst[k].extend(v)
        elif isinstance(v, Mapping) and isinstance(dst[k], Mapping):
            merge_dict_inplace(v, dst[k])
        else:
            if overwrite_dst:
                dst[k] = v
            else:
                pass


def query_wiki(base_url, pages, query_content=None, rev_query=None):
    if query_content is None:
        query_content = ['revisions', 'links', 'images']
    if rev_query is None:
        rev_query = ['content']
        if not 'revisions' in query_content:
            query_content.append('revisions')

    res = {}
    request = {
        'titles': '|'.join(pages),
        'prop': '|'.join(query_content),
        'rvprop': '|'.join(rev_query)
    }
    for r in query(base_url, request):
        merge_dict_inplace(r, res)
    return res


def query(base_url, request):
    """
    modified from https://www.mediawiki.org/wiki/API:Query
    :param base_url:
    :param request:
    :return:
    """
    request['action'] = 'query'
    request['format'] = 'json'
    lastContinue = {}
    while True:
        # Clone original request
        req = request.copy()
        # Modify it with the values returned in the 'continue' section of the last result.
        req.update(lastContinue)
        # Call API
        result = requests.get('/'.join([base_url ,'api.php']), params=req).json()
        if 'error' in result:
            raise Error(result['error'])
        if 'warnings' in result:
            print(result['warnings'])
        if 'query' in result:
            yield result['query']
        if 'continue' not in result:
            break
        lastContinue = result['continue']


def query_img_info(base_url, files, add_file=False):
    res = {}
    request = {
        'titles': '|'.join(map(lambda f: 'File:'+f, files) if add_file else files),
        'prop': 'imageinfo',
        'iiprop': 'url'
    }
    for r in query(base_url, request):
        merge_dict_inplace(r, res)
    return res


if __name__ == '__main__':

    outdir = 'dump'
    with open('pages.txt', 'r') as fd:
        pages_to_read = [l.strip() for l in fd.readlines() if l.strip()!='' and not l.strip().startswith('#')]

    print(pages_to_read)

    if not os.path.exists(outdir):
        os.mkdir(outdir)

    res1 = query_wiki("http://imagej.net", pages_to_read)
    print(json.dumps(res1, indent=1))

    imgs = []
    for _, v in res1['pages'].items():

        title = v['title'] + '.mediawiki'
        content = v['revisions'][0]['*']

        with open(os.path.join(outdir, title), 'w') as fd:
            fd.write(content)

        for img in v['images']:
            imgs.append(img['title'])

    res2 = query_img_info("http://imagej.net", imgs)
    print(json.dumps(res2, indent=1))

    p = re.compile('File:(.*)')

    for _, v in res2['pages'].items():
        title = p.match(v['title']).groups()[0].replace(' ', '_')
        url = v['imageinfo'][0]['url']

        r = requests.get(url)
        with open(os.path.join(outdir, title), 'wb') as fd:
            fd.write(r.content)

        print('{} at {}'.format(title, url))
