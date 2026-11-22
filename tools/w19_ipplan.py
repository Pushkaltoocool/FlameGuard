"""Generate the W19 IP addressing plan and the Packet Tracer configs for the upgrade (draft) file.

    python tools/w19_ipplan.py          # writes pt_config["draft"] for every device + "ip_plan" into w19-network.json
                                        # and docs/IP_PLAN.md (the full table for the slides)
    python tools/w19_sync.py build draft   # then rebuild W19-network-layout.pkt from the JSON

Everything here is derived from the links in w19-network.json, so adding a device + link and re-running keeps the plan whole.
"""
import ipaddress
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NET = ROOT / 'w19-network.json'
DOC = ROOT / 'docs' / 'IP_PLAN.md'

SITE = '10.19.0.0/16'
TRANSIT = {'R1-CORE': ('10.19.255.0/30', '10.19.255.1', '10.19.255.2'),
           'R1-CAMPUS': ('172.16.19.0/30', '172.16.19.2', '172.16.19.1')}   # campus side assumed (closet not surveyed)
DHCP_SRV, IOT_SRV, WLC_IP = '10.19.60.10', '10.19.60.20', '10.19.99.5'
IOT_USER, IOT_PASS = 'flameguard', 'flameguard'
NATIVE = 999

MGMT = {'W19-CORE': '10.19.99.1', 'W19-WLC': WLC_IP,
        '1F-ACC': '10.19.99.11', '2F-ACC': '10.19.99.12', '3F-ACC': '10.19.99.13',
        '1F-HUB-1': '10.19.99.21', '1F-HUB-2': '10.19.99.22', '02F_HUB_A': '10.19.99.23', '02F_HUB_B': '10.19.99.24',
        '1F-FIRE-N': '10.19.99.41', '1F-FIRE-S': '10.19.99.42', '2F-FIRE-N': '10.19.99.43', '2F-FIRE-E': '10.19.99.44',
        '2F-FIRE-S': '10.19.99.45', '3F-FIRE': '10.19.99.46'}
SERVERS = {'W19-SRV (DHCP/DNS)': DHCP_SRV, 'FIRE-IOT-SRV': IOT_SRV}
# PC groups: research labs / lecture rooms -> VLAN 20, staff offices -> VLAN 10
PC_VLAN = lambda name: 20 if re.search(r'PC (1\d\d|201|215|216|217)\b', name) else 10
FIRE_SOURCE = 'FIRE 221 (smoke source)'
# Detectors report to the server only when Alarm changes (not on every 1 % smoke step): with ~100 detectors the
# per-second level reports flooded Packet Tracer and the rules fired late or never.
DETECTOR_PATCH = [
    ['\tlevel = newLevel;\n\tif (level > ALARM_LEVEL)\n\t\tsetState(1);\n\telse\n\t\tsetState(0);\n\t\n\tsendReport();',
     '\tlevel = newLevel;\n\tvar ns = level > ALARM_LEVEL ? 1 : 0;   // Flame Guard: report on alarm change only\n\tif (ns !== state)\n\t\tsetState(ns);'],
    ['    level = newLevel\n    if level > ALARM_LEVEL:\n        setState(1)\n    else:\n        setState(0)\n\n    sendReport()',
     '    level = newLevel\n    ns = 1 if level > ALARM_LEVEL else 0   # Flame Guard: report on alarm change only\n    if ns != state:\n        setState(ns)'],
    # while in alarm, repeat the report every 5 s so a lost packet cannot leave a siren silent
    ['\t\tsetLevel(Environment.get(ENVIRONMENT_NAME));\n\n\tdelay(1000);\n}',
     '\t\tsetLevel(Environment.get(ENVIRONMENT_NAME));\n\tif (state === 1 && ++fgBeat % 5 === 0)   // Flame Guard: alarm heartbeat\n\t\tsendReport();\n\n\tdelay(1000);\n}\nvar fgBeat = 0;'],
    # the server only acts when Alarm goes 0 -> 1, so the heartbeat re-sends that edge: a lost packet or a siren that
    # registered late gets switched on within 5 s
    ['\tif (state === 1 && ++fgBeat % 5 === 0)   // Flame Guard: alarm heartbeat\n\t\tsendReport();',
     '\tif (state === 1 && ++fgBeat % 5 === 0) {   // Flame Guard: alarm heartbeat, re-sends the 0 to 1 edge\n\t\tIoEClient.reportStates("0," + level);\n\t\tIoEClient.reportStates("1," + level);\n\t}'],
    # the two reports in one tick were merged by the server, so send the 0 and the 1 one second apart
    ['\tif (state === 1 && ++fgBeat % 5 === 0) {   // Flame Guard: alarm heartbeat, re-sends the 0 to 1 edge\n\t\tIoEClient.reportStates("0," + level);\n\t\tIoEClient.reportStates("1," + level);\n\t}',
     '\tif (state === 1) {   // Flame Guard: alarm heartbeat, re-sends the 0 to 1 edge every 5 s\n\t\tfgBeat++;\n\t\tif (fgBeat % 5 === 0)\n\t\t\tIoEClient.reportStates("0," + level);\n\t\telse if (fgBeat % 5 === 1)\n\t\t\tIoEClient.reportStates("1," + level);\n\t}']]
SIM_ROOM = '221'


def net_of(vlans, vid):
    v = next(x for x in vlans if x['id'] == vid)
    return ipaddress.ip_network(v['subnet']) if v.get('subnet') else None


def fire_ip(name, seq):
    """2F: Smoke 2xx -> .1xx, Siren 2xx -> .2xx (Conference Room uses the free number 219). 1F: .11-.40. 3F: .41-.60."""
    m = re.match(r'(Smoke|Siren) (2\d\d|Conf)$', name)
    if m:
        room = 19 if m.group(2) == 'Conf' else int(m.group(2)) - 200
        return '10.19.40.%d' % ((100 if m.group(1) == 'Smoke' else 200) + room)
    return '10.19.40.%d' % seq


def main():
    net = json.loads(NET.read_text(encoding='utf8'))
    vlans = net['vlans']
    devs = {d['name']: d for d in net['devices']}
    draft = [d for d in net['devices'] if d.get('only') != 'as-is']
    names = {d['name'] for d in draft}
    links = [l for l in net['links'] if l.get('only') != 'as-is' and l['a'] in names and l['b'] in names]
    nbrs = {}
    for l in links:
        nbrs.setdefault(l['a'], []).append((l['a_port'], l['b'], l['b_port']))
        nbrs.setdefault(l['b'], []).append((l['b_port'], l['a'], l['a_port']))

    # ---------------- fire source in office 221 (Packet Tracer "Old Car" with its script turned into a fast fire)
    s221 = devs['Smoke ' + SIM_ROOM]
    if FIRE_SOURCE not in devs:
        net['devices'].append({'name': FIRE_SOURCE, 'kind': 'firesource', 'pt_model': 'Old Car', 'status': 'proposed',
                               'floor': 2, 'x': round(s221['x'] + 1.2, 2), 'z': round(s221['z'] + 0.8, 2), 'only': 'draft',
                               'pt_template': 'IoT1', 'pt_template_file': 'C:/Program Files/Cisco Packet Tracer 9.0.1/saves/04 IoT/Solution Examples/smoke_detector.pkt',
                               'logical': [1700, 1150],
                               'notes': 'Fire simulation (scenario S1, office 221). Packet Tracer has no fire object, so a Things > Old Car '
                                        'stands in as the smoke source; its script was changed to add 1.5 % smoke and 0.5 C per second. '
                                        'Alt+click it to start the fire.'})
        devs[FIRE_SOURCE] = net['devices'][-1]
        draft.append(devs[FIRE_SOURCE])

    # ---------------- addressing
    plan = {'site': SITE, 'transit': [], 'mgmt': [], 'servers': [], 'fire': [], 'dhcp_pools': [], 'svis': []}
    for k, (sub, a, b) in TRANSIT.items():
        plan['transit'].append({'link': k, 'subnet': sub, 'a': a, 'b': b})
    for v in vlans:
        n = net_of(vlans, v['id'])
        if n:
            plan['svis'].append({'vlan': v['id'], 'name': v['name'], 'subnet': str(n), 'gateway': str(n.network_address + 1),
                                 'mask': str(n.netmask), 'hosts': n.num_addresses - 2, 'use': v['use']})
    seq1, seq3 = 11, 41
    fire_ips = {}
    for d in draft:
        if d['kind'] in ('smoke', 'siren', 'heat') and d.get('vlan') == 40:
            if d['floor'] == 1:
                ip, seq1 = fire_ip(d['name'], seq1), seq1 + 1
            elif d['floor'] == 3:
                ip, seq3 = fire_ip(d['name'], seq3), seq3 + 1
            else:
                ip = fire_ip(d['name'], 0)
            fire_ips[d['name']] = ip
    assert len(set(fire_ips.values())) == len(fire_ips), 'duplicate fire IP'

    vl = {v['id']: v for v in vlans}
    all_vlans = [(v['id'], v['name']) for v in vlans]

    def trunk(port, desc, l2=True):
        out = ['interface ' + port, ' description ' + desc]
        if l2:
            out.append(' switchport trunk encapsulation dot1q')
        out += [' switchport trunk native vlan %d' % NATIVE, ' switchport mode trunk', '!']
        return out

    def access(port, desc, vid, portfast=True):
        out = ['interface ' + port, ' description ' + desc, ' switchport mode access', ' switchport access vlan %d' % vid]
        if portfast:
            out.append(' spanning-tree portfast')
        return out + ['!']

    def head(host):
        return ['!', 'version 16.3.2', 'no service timestamps log datetime msec', 'no service timestamps debug datetime msec',
                'no service password-encryption', '!', 'hostname ' + host, '!', 'enable secret flameguard', '!',
                'spanning-tree mode rapid-pvst', '!']

    tail = ['!', 'line con 0', '!', 'line aux 0', '!', 'line vty 0 4', ' login', '!', 'end']

    def port_role(dev, port, other):
        k = devs[other]['kind']
        if k in ('core', 'hub', 'access', 'fire-switch', 'wlc'):
            return 'trunk'
        if k in ('smoke', 'siren', 'heat'):
            return 40
        if k == 'ap':
            return 99
        if k == 'server':
            return 60
        if k == 'pc':
            return PC_VLAN(other)
        return None

    for d in draft:
        nm, k = d['name'], d['kind']
        cfg = None
        host = re.sub(r'[^A-Za-z0-9-]+', '-', re.sub(r'\s*\(.*?\)', '', nm)).strip('-')
        if k == 'router':
            r_core, r_camp = TRANSIT['R1-CORE'], TRANSIT['R1-CAMPUS']
            ios = ['!', 'version 15.4', 'no service timestamps log datetime msec', 'no service timestamps debug datetime msec',
                   'no service password-encryption', '!', 'hostname ' + host, '!', 'enable secret flameguard', '!', 'ip cef', 'no ipv6 cef', '!',
                   'interface GigabitEthernet0/0/0', ' description to WSU Campus Network (campus side assumed)',
                   ' ip address %s 255.255.255.252' % r_camp[1], ' duplex auto', ' speed auto', '!',
                   'interface GigabitEthernet0/0/1', ' description to W19-CORE (routed /30)',
                   ' ip address %s 255.255.255.252' % r_core[1], ' duplex auto', ' speed auto', '!',
                   'interface GigabitEthernet0/0/2', ' no ip address', ' shutdown', '!',
                   'ip classless', 'ip route 0.0.0.0 0.0.0.0 %s' % r_camp[2], 'ip route 10.19.0.0 255.255.0.0 %s' % r_core[2], '!'] + tail
            cfg = {'ios': ios}
        elif k == 'core':
            ios = head(host) + ['ip routing', '!']
            used = {p for p, _, _ in nbrs.get(nm, [])}
            for p, o, op in sorted(nbrs.get(nm, []), key=lambda t: [int(x) for x in re.findall(r'\d+', t[0])]):
                if devs[o]['kind'] == 'router':
                    ios += ['interface ' + p, ' description to %s (routed /30)' % o, ' no switchport',
                            ' ip address %s 255.255.255.252' % TRANSIT['R1-CORE'][2], '!']
                elif port_role(nm, p, o) == 'trunk':
                    ios += trunk(p, 'trunk to ' + o)
                else:
                    ios += access(p, 'to ' + o, port_role(nm, p, o))
            for v in plan['svis']:
                ios += ['interface Vlan%d' % v['vlan'], ' description %s' % v['name'], ' ip address %s %s' % (v['gateway'], v['mask'])]
                if v['vlan'] not in (60,):
                    ios.append(' ip helper-address ' + DHCP_SRV)
                if v['vlan'] == 40:
                    ios += [' ip access-group FIRE-IN in', ' ip access-group FIRE-OUT out']
                ios.append('!')
            ios += ['ip classless', 'ip route 0.0.0.0 0.0.0.0 %s' % TRANSIT['R1-CORE'][1], '!',
                    'ip access-list extended FIRE-IN',
                    ' remark VLAN 40 fire devices may only talk to the fire alert server',
                    ' permit ip 10.19.40.0 0.0.0.255 host %s' % IOT_SRV,
                    ' permit udp any any eq bootps',
                    ' deny ip any any',
                    'ip access-list extended FIRE-OUT',
                    ' remark only the alert server and management may reach the fire devices',
                    ' permit ip host %s 10.19.40.0 0.0.0.255' % IOT_SRV,
                    ' permit ip 10.19.99.0 0.0.0.255 10.19.40.0 0.0.0.255',
                    ' deny ip any any', '!'] + tail
            cfg = {'ios': ios, 'vlans': all_vlans}
        elif k in ('hub', 'access', 'fire-switch'):
            l2_encap = d['pt_model'].startswith('3560')
            ios = head(host)
            ports = sorted(nbrs.get(nm, []), key=lambda t: (t[0][:3], [int(x) for x in re.findall(r'\d+', t[0])]))
            sw_vlans = {99}
            for p, o, op in ports:
                role = port_role(nm, p, o)
                if role == 'trunk':
                    ios += trunk(p, 'uplink to ' + o, l2_encap)
                elif role:
                    sw_vlans.add(role)
                    ios += access(p, o, role)
            ios += ['interface Vlan1', ' no ip address', ' shutdown', '!',
                    'interface Vlan99', ' description MGMT', ' ip address %s 255.255.255.0' % MGMT[nm], '!',
                    'ip default-gateway 10.19.99.1', '!'] + tail
            cfg = {'ios': ios, 'vlans': [(v, vl[v]['name']) for v in sorted(sw_vlans | {NATIVE})]}
        elif k == 'server':
            ip = SERVERS[nm]
            cfg = {'ip': {'ip': ip, 'mask': '255.255.255.0', 'gw': '10.19.60.1', 'dns': DHCP_SRV}}
            if nm.startswith('W19-SRV'):
                pools = []
                for v in plan['svis']:
                    if v['vlan'] in (40, 60):
                        continue                       # servers and fire devices are static
                    n = ipaddress.ip_network(v['subnet'])
                    start = n.network_address + (100 if v['vlan'] == 99 else 11)
                    pools.append({'name': 'V%d-%s' % (v['vlan'], v['name']), 'network': str(n.network_address), 'mask': v['mask'],
                                  'gw': v['gateway'], 'dns': DHCP_SRV, 'start': str(start),
                                  'max': int(n.broadcast_address) - int(start), 'wlc': WLC_IP if v['vlan'] == 99 else '0.0.0.0'})
                cfg['dhcp_pools'] = pools
                cfg['dns_records'] = [('fire-iot.w19.local', IOT_SRV), ('dhcp.w19.local', DHCP_SRV), ('wlc.w19.local', WLC_IP)]
                plan['dhcp_pools'] = pools
            else:
                rules = []
                for floor_sirens, dets in ((2, None), (3, None)):
                    sirens = [x['name'] for x in draft if x['kind'] == 'siren' and x.get('floor') == floor_sirens and x['name'] in fire_ips]
                    for det in [x['name'] for x in draft if x['kind'] in ('smoke', 'heat') and x.get('floor') == floor_sirens and x['name'] in fire_ips]:
                        # own office siren; a detector without one (3F lobby, roof) sounds every siren on its floor
                        own = 'Siren ' + det.split(' ', 1)[1]
                        targets = [own] if own in sirens else sirens
                        rules.append({'name': 'FIRE %s' % det.split(' ', 1)[1], 'if': [det, 'Alarm', '1'], 'then': [[s, 'On', '1'] for s in targets]})
                cfg['iot_server'] = {'user': IOT_USER, 'password': IOT_PASS, 'register': sorted(fire_ips), 'rules': rules}
            plan['servers'].append({'name': nm, 'ip': ip, 'vlan': 60})
        elif k in ('smoke', 'siren', 'heat') and nm in fire_ips:
            cfg = {'ip': {'ip': fire_ips[nm], 'mask': '255.255.255.0', 'gw': '10.19.40.1', 'dns': ''},
                   'iot_client': {'server': IOT_SRV, 'user': IOT_USER, 'password': IOT_PASS}}
            if d['pt_model'] == 'Smoke Detector':
                cfg['script_patch'] = DETECTOR_PATCH
            plan['fire'].append({'name': nm, 'ip': fire_ips[nm], 'floor': d['floor'], 'zone': d.get('zone'),
                                 'switch': nbrs[nm][0][1], 'port': nbrs[nm][0][2]})
        elif k == 'pc':
            cfg = {'dhcp': True}
        elif k == 'firesource':
            cfg = {'script_patch': [['var SMOKE_RATE = 3/3600;', 'var SMOKE_RATE = 1.5;   // Flame Guard: fire, 1.5 % smoke per second'],
                                    ['var TEMPERATURE_RATE = 1/3600;', 'var TEMPERATURE_RATE = 0.5;   // Flame Guard: +0.5 C per second'],
                                    ['var volumeRatio = VOLUME_AT_RATE / Environment.getVolume();', 'var volumeRatio = 1;'],
                                    ['SMOKE_RATE = 3./3600', 'SMOKE_RATE = 1.5'], ['TEMPERATURE_RATE = 1./3600', 'TEMPERATURE_RATE = 0.5'],
                                    ['volumeRatio = VOLUME_AT_RATE / Environment.getVolume()', 'volumeRatio = 1.']]}
        if nm in MGMT and nm not in ('W19-CORE',):
            plan['mgmt'].append({'name': nm, 'ip': MGMT[nm], 'model': d['pt_model']})
        if cfg:
            d.setdefault('pt_config', {})['draft'] = cfg

    net['ip_plan'] = plan
    net['variants']['fire-demo'] = {
        'pt_file': 'W19-fire-demo.pkt', 'template_file': 'W19-network-layout.pkt', 'zones': ['N', 'S', 'E'],
        'names': ['W19-CORE', 'FIRE-IOT-SRV', '2F-FIRE-N', '2F-FIRE-S', '2F-FIRE-E', FIRE_SOURCE, 'Power Distribution Device0'],
        'about': 'Fast demo of fire scenario S1: same configs as the draft, only the core, the alert server and all three 2F '
                 'fire zones (202-217, 220-232, Conference Room). Open it, wait ~30 s, Physical > 2F, Alt+click the fire source.'}
    # every config written for the draft also applies to the demo file
    for d in net['devices']:
        if (d.get('pt_config') or {}).get('draft'):
            d['pt_config']['fire-demo'] = d['pt_config']['draft']
    if devs[FIRE_SOURCE].get('only') == 'draft':
        devs[FIRE_SOURCE]['only'] = ['draft', 'fire-demo']
    net.setdefault('pt_notes', {})['draft'] = {'Team Flame Guard - W19 Endicott network': '\n'.join([
        'Team Flame Guard - W19 Endicott network, upgrade draft v0.2 (22 Nov 2026)',
        'Addressing: 10.19.0.0/16, one VLAN per role, gateways = SVIs on W19-CORE (see docs/IP_PLAN.md).',
        'VLAN 10 Faculty, 20 Labs, 30-38 Wi-Fi, 40 Fire IoT, 50 Security, 60 Servers, 99 Mgmt, 999 native.',
        'W19-R1 10.19.255.1/30 to W19-CORE 10.19.255.2/30. DHCP: W19-SRV 10.19.60.10 via ip helper.',
        'Fire: every protected room = Smoke + Siren on VLAN 40 (2F: Smoke 2xx = .1xx, Siren 2xx = .2xx),',
        'registered to FIRE-IOT-SRV 10.19.60.20 (user flameguard). ACL FIRE-IN/FIRE-OUT isolate VLAN 40.',
        'FIRE SIMULATION (S1): wait ~1 min after opening, then Physical, 2F, Alt+click "FIRE 221 (smoke source)".',
        'Smoke rises on 2F, each detector trips at 40 %, the server rule turns on that office\'s siren.',
        'Grey = network closet: no access for students (confirmed), so its devices are ASSUMED from the Cisco design guide.'])}
    closet = {'Still to verify on site:': '\n'.join([
        'Still to verify on site:',
        '- AP + hub model numbers, which hub feeds which AP',
        '- wall ports per room, 3F layout',
        "- existing fire devices in each professor's office",
        'Network closet: NO ACCESS (confirmed) - router, core, WLC, servers',
        'and closet switches stay assumed, sized from the Cisco design guide.']),
        'Network closet / campus uplink': 'Network closet / campus uplink - NO ACCESS (assumed devices)'}
    for v in ('draft', 'as-is'):
        net['pt_notes'].setdefault(v, {}).update(closet)
    k = 'Team Flame Guard - W19 Endicott network'
    net['pt_notes']['fire-demo'] = dict(closet)
    net['pt_notes']['fire-demo'][k] = ( net['pt_notes']['draft'][k].replace('upgrade draft v0.2', 'FIRE DEMO (cut-down copy of the upgrade draft v0.2:')
                                    .replace('(22 Nov 2026)', 'core, alert server, all three 2F fire zones only)', 1))
    NET.write_text(json.dumps(net, indent=1, ensure_ascii=False) + '\n', encoding='utf8')
    write_doc(plan, vlans)
    print('IP plan: %d VLAN subnets, %d mgmt IPs, %d fire devices, %d DHCP pools, %d IoT rules'
          % (len(plan['svis']), len(plan['mgmt']), len(plan['fire']), len(plan['dhcp_pools']),
             len(devs['FIRE-IOT-SRV']['pt_config']['draft']['iot_server']['rules'])))


def write_doc(plan, vlans):
    L = ['# W19 IP addressing plan (Team Flame Guard)', '',
         'Generated by `tools/w19_ipplan.py` from `w19-network.json`. Site block **%s**; one /24 per role, Wi-Fi student pools /23.' % plan['site'], '',
         '## 1. VLANs and subnets (gateways are SVIs on W19-CORE)', '',
         '| VLAN | Name | Subnet | Gateway | Usable hosts | DHCP | Used for |', '|---|---|---|---|---|---|---|']
    pools = {p['name'].split('-')[0][1:]: p for p in plan['dhcp_pools']}
    for v in plan['svis']:
        p = pools.get(str(v['vlan']))
        dh = '%s – .%s' % (p['start'], p['start'].split('.')[-1] if False else '') if p else 'static'
        if p:
            n = ipaddress.ip_network(v['subnet'])
            dh = '%s – %s' % (p['start'], n.broadcast_address - 1)
        L.append('| %d | %s | %s | %s | %d | %s | %s |' % (v['vlan'], v['name'], v['subnet'], v['gateway'], v['hosts'], dh, v['use']))
    L += ['| 999 | NATIVE | – | – | – | – | Native VLAN on every trunk (unused, no IP) |', '',
          '## 2. Point-to-point links', '', '| Link | Subnet | Side A | Side B |', '|---|---|---|---|']
    for t in plan['transit']:
        a, b = t['link'].split('-')
        L.append('| %s ↔ %s | %s | %s %s | %s %s |' % (a, b, t['subnet'], a.replace('R1', 'W19-R1'), t['a'],
                                                      b.replace('CORE', 'W19-CORE').replace('CAMPUS', 'campus'), t['b']))
    L += ['', '## 3. Servers (VLAN 60)', '', '| Server | IP | Role |', '|---|---|---|',
          '| W19-SRV | %s | DHCP for every client VLAN (via ip helper on W19-CORE), DNS `*.w19.local` |' % DHCP_SRV,
          '| FIRE-IOT-SRV | %s | IoT registration server + fire rules; the only host VLAN 40 may reach |' % IOT_SRV, '',
          '## 4. Network management (VLAN 99)', '', '| Device | Model (Packet Tracer) | IP |', '|---|---|---|',
          '| W19-CORE | 3650-24PS | 10.19.99.1 (gateway) |']
    for m in plan['mgmt']:
        L.append('| %s | %s | %s |' % (m['name'], m['model'], m['ip']))
    L += ['| Access points (13) | LAP-PT | DHCP 10.19.99.100+, join WLC %s |' % WLC_IP, '',
          '## 5. Fire devices (VLAN 40, static)', '',
          'Rule of thumb on 2F: **Smoke 2xx = 10.19.40.1xx, Siren 2xx = 10.19.40.2xx** (Conference Room uses the free number 19). '
          '1F detectors 10.19.40.11–.40, 3F devices 10.19.40.41+. Gateway 10.19.40.1. Every device registers to FIRE-IOT-SRV.', '',
          '| Device | IP | Floor | Zone | Switch | Port |', '|---|---|---|---|---|---|']
    for f in sorted(plan['fire'], key=lambda x: ipaddress.ip_address(x['ip'])):
        L.append('| %s | %s | %dF | %s | %s | %s |' % (f['name'], f['ip'], f['floor'], f['zone'], f['switch'], f['port']))
    L += ['', '## 6. Security on the fire VLAN', '',
          '- `FIRE-IN` (in on Vlan40): fire devices may only reach %s; everything else is dropped.' % IOT_SRV,
          '- `FIRE-OUT` (out on Vlan40): only the alert server and the management VLAN can reach the fire devices.',
          '- Trunks use native VLAN 999; fire switches only carry VLANs 40 and 99.', '']
    DOC.parent.mkdir(exist_ok=True)
    DOC.write_text('\n'.join(L), encoding='utf8')


if __name__ == '__main__':
    main()
