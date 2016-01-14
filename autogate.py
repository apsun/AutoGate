#!/usr/bin/env python3
import os
import bs4
import cherrypy
import vgscraper

class AutoGateWebController:
    @cherrypy.expose
    def index(self):
        return """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>AutoGate | Home</title>
<meta http-equiv="content-type" content="text/html;charset=utf-8" />
<style type="text/css">
p {
    font-family: "Georgia", sans-serif;
    font-size: 16px;
}
</style>
</head>
<body>
<p>
Welcome to AutoGate, a project to bring <a href="http://www.vpngate.net/en/">VPN Gate</a> 
to those behind the Great Firewall of China.
</p>

<p>
Are you looking for a VPN server? Check here:<br />
<a href="/servers">Server list (click here for the list of servers)</a><br />
<a href="/mirrors">Mirror list (click here for a list of VPN Gate mirror websites)</a>
</p>

<p>
Are you a programmer searching for the API? We have you covered too:<br />
<a href="/api/v1/servers">Server list (JSON)</a><br />
<a href="/api/v1/mirrors">Mirror list (JSON)</a>
</p>

<p>
Copyright (c) 2014-2015 Andrew Sun<br />
This website is not affiliated with VPN Gate or the SoftEther project.
</p>

<p>
Nyaa! &lt;3~
</p>
</body>
</html>
"""

    @cherrypy.expose
    def servers(self):
        html = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>AutoGate | Servers</title>
<meta http-equiv="content-type" content="text/html;charset=utf-8" />
<style type="text/css">
table {
    border-collapse: collapse;
    font-family: "Lucida Grande", sans-serif;
    width: 100%;
    font-size: 13px;
}

table, th, td {
    border: 2px solid #d3d3d3;
}

th {
    color: #fff;
    background-color: #2c76b5;
}

tr {
    text-align: center;
    height: 60px;
}

tr:nth-child(odd) {
    background-color: #ffffff;
}

tr:nth-child(even) {
    background-color: #ffffef;
}
</style>
</head>
<body>
    <table>
        <thead>
            <tr>
                <th>Country</th>
                <th>Server IP</th>
                <th>Sessions</th>
                <th>Bandwidth</th>
                <th>L2TP/IPSec</th>
                <th>OpenVPN</th>
                <th>Owner</th>
                <th>Score</th>
            </tr>
        </thead>
        <tbody id="table-body">
        </tbody>
    </table>
</body>
</html>
"""

        bs = bs4.BeautifulSoup(html, "html.parser")
        table_body = bs.find(id="table-body")
        server_list = vgscraper.get_server_list()
        server_list.sort(key=lambda s: s["score"], reverse=True)
        server_list.sort(key=lambda s: 0 if s["l2tp"] else 1)

        for server_data in server_list:
            # Ignore if neither L2TP nor OpenVPN are available
            if not server_data["l2tp"] and "openvpn" not in server_data:
                continue

            table_row = bs.new_tag("tr")

            # Country
            country_col = bs.new_tag("td")
            country_col.string = server_data["country"]
            table_row.append(country_col)

            # IP
            ip_col = bs.new_tag("td")
            ip_col.string = server_data["ip"]
            table_row.append(ip_col)

            # Sessions
            sessions_col = bs.new_tag("td")
            sessions_col.string = str(server_data["sessions"]) + " sessions"
            table_row.append(sessions_col)

            # Bandwidth
            bandwidth_col = bs.new_tag("td")
            bandwidth_col.string = str(server_data["bandwidth"]) + " Mbps"
            table_row.append(bandwidth_col)

            # L2TP
            l2tp_col = bs.new_tag("td")
            l2tp_col.string = "YES" if server_data["l2tp"] else ""
            table_row.append(l2tp_col)

            # OpenVPN
            openvpn_col = bs.new_tag("td")
            openvpn_data = server_data.get("openvpn")
            first = True
            if openvpn_data:
                for protocol in ("udp", "tcp"):
                    port = openvpn_data.get(protocol)
                    if port:
                        # Add newline when multiple protocols available
                        if first:
                            first = False
                        else:
                            openvpn_col.append(bs.new_tag("br"))

                        # Create config download URL
                        config_link = bs.new_tag("a", href="/api/v1/openvpn?ip={0}&protocol={1}&port={2}&hid={3}".format(
                            server_data["ip"],
                            protocol,
                            port,
                            openvpn_data["hid"]
                        ))
                        config_link.string = "{0}: Port {1}".format(protocol.upper(), port)
                        openvpn_col.append(config_link)

            table_row.append(openvpn_col)

            # Owner
            owner_col = bs.new_tag("td")
            owner_col.string = server_data["owner"]
            table_row.append(owner_col)

            # Score
            score_col = bs.new_tag("td")
            score_col.string = "{0:,}".format(server_data["score"])
            table_row.append(score_col)

            table_body.append(table_row)

        return str(bs)

    @cherrypy.expose
    def mirrors(self):
        html = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>AutoGate | Mirrors</title>
<meta http-equiv="content-type" content="text/html;charset=utf-8" />
<style type="text/css">
table {
    border-collapse: collapse;
    font-family: "Lucida Grande", sans-serif;
    width: 100%;
    font-size: 13px;
}

table, th, td {
    border: 2px solid #d3d3d3;
}

th {
    color: #fff;
    background-color: #2c76b5;
}

tr {
    text-align: center;
    height: 60px;
}

tr:nth-child(odd) {
    background-color: #ffffff;
}

tr:nth-child(even) {
    background-color: #ffffef;
}
</style>
</head>
<body>
    <table>
        <thead>
            <tr>
                <th>Country</th>
                <th>URL</th>
            </tr>
        </thead>
        <tbody id="table-body">
        </tbody>
    </table>
</body>
</html>
"""
        
        bs = bs4.BeautifulSoup(html, "html.parser")
        table_body = bs.find(id="table-body")
        mirror_list = vgscraper.get_mirror_list()

        for mirror_data in mirror_list:
            table_row = bs.new_tag("tr")

            # Country
            country_col = bs.new_tag("td")
            country_col.string = mirror_data["country"]
            table_row.append(country_col)

            # URL
            url_col = bs.new_tag("td")
            url_link = bs.new_tag("a", href=mirror_data["url"])
            url_link.string = mirror_data["url"]
            url_col.append(url_link)
            table_row.append(url_col)

            table_body.append(table_row)

        return str(bs)


class AutoGateApiController:
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def servers(self):
        return vgscraper.get_server_list()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def mirrors(self):
        return vgscraper.get_mirror_list()

    @cherrypy.expose
    def openvpn(self, ip, protocol, port, hid):
        stream = vgscraper.get_openvpn_config(ip, protocol, port, hid)
        filename = "vpngate_{0}_{1}_{2}.ovpn".format(ip, protocol, port)
        return cherrypy.lib.static.serve_fileobj(stream, "application/x-openvpn-profile", "attachment", filename)


if __name__ == "__main__":
    cherrypy.config.update({
        "server.socket_host": "0.0.0.0",
        "server.socket_port": int(os.environ["PORT"])
    })

    cherrypy.tree.mount(AutoGateWebController(), "/")
    cherrypy.tree.mount(AutoGateApiController(), "/api/v1")
    cherrypy.engine.start()
    cherrypy.engine.block()
