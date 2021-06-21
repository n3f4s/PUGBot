"""Define helper function to query the API"""

from urllib.parse import quote_plus

from btag import Btag

header = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive'
}


def make_url(btag: Btag) -> str:
    """Return the encoded url for a btag"""
    fmt_btag = quote_plus(btag.for_api())
    return "https://ow-api.com/v1/stats/pc/EU/{}/profile".format(fmt_btag)
