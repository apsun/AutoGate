import re
import io
import time
import itertools
import urllib.parse
import requests
import bs4

_BANDWIDTH_REGEX = re.compile(r"^(\d+\.?\d*) Mbps$")
_OWNER_REGEX = re.compile(r"^(By )?(.*?)('s owner)?$")
_SESSIONS_REGEX = re.compile(r"^(\d+) sessions$")
_MIRROR_LOCATION_REGEX = re.compile(r"^.*\(Mirror location: (.+?)\)$")
_TCP_REGEX = re.compile(r"^TCP: (\d+)$")
_UDP_REGEX = re.compile(r"^UDP: (\d+)$")


def _fetch_server_list_html():
    request = requests.get("http://www.vpngate.net/en/")
    return request.text


def _parse_openvpn_cell(td):
    if len(td.contents) == 0:
        return None
    
    openvpn = {}

    # Get the 'hid' parameter (for getting the OpenVPN config later)
    download_url = td.a["href"]
    download_query = urllib.parse.urlparse(download_url).query
    hid = urllib.parse.parse_qs(download_query)["hid"][0]
    openvpn["hid"] = int(hid)

    # Now we get the protocol ports
    ports = list(td.a.next_sibling.children)

    # There can only be two entries at most
    assert 1 <= len(ports) <= 2

    # The second item is enclosed by <br></br>, turn it into text first
    if len(ports) == 2:
        ports[1] = ports[1].string

    for port in ports:
        udp_match = _UDP_REGEX.match(port)
        if udp_match:
            openvpn["udp"] = int(udp_match.group(1))
            continue

        tcp_match = _TCP_REGEX.match(port)
        if tcp_match:
            openvpn["tcp"] = int(tcp_match.group(1))
            continue

    return openvpn


def _parse_owner_cell(td):
    try:
        owner_str = str(td.i.b.string)
    except:
        return ""
    return _OWNER_REGEX.match(owner_str).group(2)


def _parse_server_list_table_rows(rows):
    for row in rows:
        cols = row.find_all("td")

        # Skip header rows. Here we check the first td item's class, 
        # since tr doesn't carry any meaningful information
        if cols[0]["class"][0] == "vg_table_header":
            continue

        # Column 0: Country
        # Column 1: Hostname/IP
        # Column 2: Session count/Uptime
        # Column 3: Bandwidth/Ping
        # Column 4: Enable SSL-VPN?
        # Column 5: Enable L2TP?
        # Column 6: Enable OpenVPN?
        # Column 7: Enable MS-SSTP?
        # Column 8: Owner name/Message
        # Column 9: Score
        country = str(cols[0].br.string)
        ip = str(cols[1].br.span.string)
        sessions = int(_SESSIONS_REGEX.match(cols[2].b.span.string).group(1))
        bandwidth = float(_BANDWIDTH_REGEX.match(cols[3].b.span.string).group(1))
        l2tp = (len(cols[5].contents) != 0)
        openvpn = _parse_openvpn_cell(cols[6])
        owner = _parse_owner_cell(cols[8])
        score = int(cols[9].b.span.string.replace(",", ""))
        
        # Return data as a dict, for JSON serialization
        server = {
            "country": country,
            "ip": ip,
            "sessions": sessions,
            "bandwidth": bandwidth,
            "l2tp": l2tp,
            "owner": owner,
            "score": score
        }

        if openvpn:
            server["openvpn"] = openvpn

        yield server


def _parse_server_list_html(html):
    bs = bs4.BeautifulSoup(html, "html.parser")

    # For some reason, some of the table rows are outside the <html> tag,
    # so we have to find those separately.
    internal_rows = bs.find(id="vpngate_inner_table").find_all("tr", recursive=False)[2:]
    external_rows = bs.find_all("tr", recursive=False)[:-1]
    all_rows = itertools.chain(internal_rows, external_rows)

    # Convert HTML to data objects
    # This returns an iterable object, not a list
    return _parse_server_list_table_rows(all_rows)


def _fetch_mirror_list_html():
    request = requests.get("http://www.vpngate.net/en/sites.aspx")
    return request.text


def _parse_mirror_list_items(items):
    for item in items:
        url = item.strong.span.a.string
        country_full = item.strong.next_sibling
        country = _MIRROR_LOCATION_REGEX.match(country_full).group(1)
        yield {
            "url": url,
            "country": country
        }


def _parse_mirror_list_html(html):
    bs = bs4.BeautifulSoup(html, "html.parser")
    mirror_list = bs.find(id="vpngate_inner_contents_td").find_all("ul")[1].find_all("li")
    return _parse_mirror_list_items(mirror_list)


def _fetch_openvpn_config(ip, protocol, port, hid):
    url = "http://www.vpngate.net/common/openvpn_download.aspx"
    params = {
        # UNIX time with milliseconds (3 extra digits)
        "sid": int(time.time() * 1000),
        "host": ip,
        # Necessary for obtaining the correct config file, for some reason.
        # This value can be found in the servers JSON.
        "hid": hid,
        "port": port,
        protocol: 1
    }

    response = requests.get(url, params=params, allow_redirects=False)
    assert response.status_code == 200
    stream = io.BytesIO(response.content)
    return stream


def get_server_list():
    """Fetches the list of VPN Gate servers.

    Returns a list of dict objects, each in the following format:
    {
        "country": "United States",
        "ip": "123.123.123.123",
        "sessions": 12,
        "bandwidth": 34.56,
        "l2tp": true,
        "openvpn": {
            "hid": 0678, 
            "tcp": 1234, 
            "udp": 5678
        },
        "owner": "Cactus-PC",
        "score": 123456
    }

    The 'openvpn' entry is optional; it will not be included if 
    the server does not support the OpenVPN protocol.
    """
    html = _fetch_server_list_html()
    servers = _parse_server_list_html(html)
    return list(servers)


def get_mirror_list():
    """Fetches the list of VPN Gate mirror sites.

    Returns a list of dict objects, each in the following format:
    {
        "url": "http://example.com/",
        "country": "Japan"
    }
    """
    html = _fetch_mirror_list_html()
    mirrors = _parse_mirror_list_html(html)
    return list(mirrors)


def get_openvpn_config(ip, protocol, port, hid):
    """Fetches the OpenVPN configuration file for the specified server.

    Arguments:
        ip (str): The IP address of the server.
        protocol (str): Either 'udp' or 'tcp'.
        port (int): The port of the protocol to use.
        hid (int): The ID of the server.

    Returns an in-memory byte stream containing the config data. 
    """
    return _fetch_openvpn_config(ip, protocol, port, hid)