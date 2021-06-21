"""Define the function to query the API"""

from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json

from btag import Btag

from owapi.helper import make_url, header


def query_api(btag: Btag):
    """Query the API and return a JSON object"""
    url = make_url(btag)
    request = Request(url, None, header)
    response = urlopen(request).read()
    return json.loads(response.decode('utf-8'))


def check_btag_exists(btag: Btag):
    """Check if a btag exists"""
    try:
        data = query_api(btag)
        return 'name' in data.keys()
    except HTTPError:
        return False
