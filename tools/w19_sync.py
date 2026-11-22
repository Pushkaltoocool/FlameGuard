"""Keep the W19 3D model and the Packet Tracer file in step, using w19-network.json as the single source of truth.

    python tools/w19_sync.py check   # report every difference between the JSON, the 3D model and the .pkt
    python tools/w19_sync.py pull    # copy device positions moved in the 3D editor back into the JSON
    python tools/w19_sync.py build   # write the .pkt (devices, links, floor-plan maps) and the 3D model from the JSON

What lives where
  w19-network.json        network devices (name, Packet Tracer model, floor, x/z in metres, status, VLAN), links, VLAN plan
  index.html              3D model; its embedded "layout" (devices) and "building" (rooms, walls) blocks
  W19-network-layout.pkt  Packet Tracer file; physical view = floor plans drawn from the 3D building at 24 px per metre
"""
import base64
import copy
import hashlib
import io
import json
import random
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pkt_crypto  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NET = ROOT / 'w19-network.json'
HTML = ROOT / 'index.html'
LAYOUT_JSON = ROOT / 'w19-layout.json'
PX, OX, OY = 24, 25, 85          # floor-plan image: px = OX + PX * x_m, py = OY + PX * z_m
IMG_W, IMG_H = 1752, 1404
PANEL_X = 1340                   # beyond this x (px) = "photographed, position not recorded" panel
KIND_3D = {'ap': 'ap', 'hub': 'hub', 'smoke': 'smoke', 'heat': 'heat', 'siren': 'siren', 'pc': 'pc'}   # kinds drawn in the 3D model


def in_3d(d):
    """One JSON device = one 3D item (grouped PCs with a 'rooms' list are checked by count instead)."""
    return d['kind'] in KIND_3D and d.get('where') != 'closet' and not d.get('rooms')
POS_TOL = 0.25                   # metres
FLOORS = (1, 2, 3)
OUTDOOR_PROTECTED = ('Roof garden',)   # outdoor areas: need >= 1 flame/heat detector and >= 1 siren

rnd = random.Random()


# ------------------------------------------------------------------ 3D model (index.html)
def _block(html, name):
    m = re.search(r'(<script type="application/json" id="%s">)(.*?)(</script>)' % name, html, re.S)
    return m


def load_3d():
    html = HTML.read_text(encoding='utf8')
    return html, json.loads(_block(html, 'layout').group(2)), json.loads(_block(html, 'building').group(2))


def save_3d(html, layout):
    m = _block(html, 'layout')
    txt = json.dumps(layout, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = html[:m.start(2)] + txt + html[m.end(2):]
    HTML.write_text(html, encoding='utf8', newline='')
    return html


def room_at(building, f, x, z):
    best = None
    for r in building['rooms']:
        if r['f'] == f and r['k'] != 'void' and r['x'] <= x <= r['x'] + r['w'] and r['z'] <= z <= r['z'] + r['d']:
            if best is None or r['w'] * r['d'] < best['w'] * best['d']:
                best = r
    return best['n'] if best else 'corridor'


def protected_rooms(building):
    """Rooms that must each get a networked smoke detector and siren: professor offices, Dean, Conference Room."""
    return [r for r in building['rooms'] if r['f'] == 2 and (r['k'] == 'office' and 'TA office' not in r['n']
                                                           or r['n'] == 'Conference Room')]


def room_tag(name):
    m = re.match(r'(\d{3})', name)
    return m.group(1) if m else ('Conf' if name.startswith('Conference') else name)


# ------------------------------------------------------------------ Packet Tracer file
class PT:
    def __init__(self, path):
        self.path = Path(path)
        self.root = ET.fromstring(pkt_crypto.decode(self.path.read_bytes()))
        self.devices = self.root.find('NETWORK/DEVICES')
        self.links = self.root.find('NETWORK/LINKS')
        self.phys = self.root.find('PHYSICALWORKSPACE/NODE')

    # lookups
    def by_name(self):
        return {d.find('ENGINE').findtext('NAME'): d for d in self.devices}

    def ref_names(self):
        return {d.find('ENGINE').findtext('SAVE_REF_ID'): d.find('ENGINE').findtext('NAME') for d in self.devices}

    def node(self, name, start=None, path=()):
        """Physical-view node by name -> (node, [uuid path of its parents])."""
        n = start if start is not None else self.phys
        here = list(path) + [n.findtext('UUID_STR')]
        if n.findtext('NAME') == name and start is not None:
            return n, list(path)
        for c in (n.find('CHILDREN') if n.find('CHILDREN') is not None else []):
            hit = self.node(name, c, here)
            if hit:
                return hit
        return None

    def device_info(self, d):
        e = d.find('ENGINE')
        name = e.findtext('NAME')
        n = self.node(name)
        parent = None
        if n:
            par = self.node_by_uuid(n[1][-1])
            parent = par.findtext('NAME') if par is not None else None
        return {'name': name, 'model': e.find('TYPE').get('model'), 'type': e.findtext('TYPE'),
                'logical': [int(float(d.findtext('WORKSPACE/LOGICAL/X'))), int(float(d.findtext('WORKSPACE/LOGICAL/Y')))],
                'parent': parent, 'px': _center(n[0]) if n else None}

    def node_by_uuid(self, u, start=None):
        n = start if start is not None else self.phys
        if n.findtext('UUID_STR') == u:
            return n
        for c in (n.find('CHILDREN') if n.find('CHILDREN') is not None else []):
            hit = self.node_by_uuid(u, c)
            if hit is not None:
                return hit
        return None

    def link_list(self):
        names = self.ref_names()
        out = []
        for l in self.links:
            c = l.find('CABLE')
            ports = [p.text for p in c.findall('PORT')]
            out.append({'a': names.get(c.findtext('FROM')), 'a_port': ports[0], 'b': names.get(c.findtext('TO')),
                        'b_port': ports[1], 'cable': c.findall('TYPE')[-1].text if c.findall('TYPE') else None})
        return out

    def save(self, path=None):
        xml = ET.tostring(self.root, encoding='utf-8')
        (Path(path) if path else self.path).write_bytes(pkt_crypto.encode(xml))


ICON_HALF = 21   # Packet Tracer device icons are about 42 px square in the physical view


def _half(node):
    return ICON_HALF, ICON_HALF


def _center(node):
    """Packet Tracer stores an icon's top-left corner; positions in the JSON are icon centres."""
    hw, hh = _half(node)
    return [float(node.findtext('X')) + hw, float(node.findtext('Y')) + hh]


def _all_macs(root):
    return set(m.upper() for m in re.findall(r'\b[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\b',
                                              ET.tostring(root, encoding='unicode')))


def _ll(mac):
    """IPv6 link-local (EUI-64) as Packet Tracer writes it, e.g. 0004.9A10.5808 -> FE80::204:9AFF:FE10:5808."""
    b = bytes.fromhex(mac.replace('.', ''))
    e = bytes([b[0] ^ 2]) + b[1:3] + b'\xff\xfe' + b[3:]
    groups = ['%X' % int.from_bytes(e[i:i + 2], 'big') for i in range(0, 8, 2)]
    return 'FE80::' + ':'.join(groups)


def _new_mac(used):
    while True:
        m = '0060.%02X%02X.%02X%02X' % tuple(rnd.randrange(256) for _ in range(4))
        if m not in used:
            used.add(m)
            return m


def _int_id():
    return str(rnd.randrange(10 ** 8, 2 * 10 ** 9))


def hostname(name):
    return re.sub(r'[^A-Za-z0-9-]+', '-', re.sub(r'\s*\(.*?\)', '', name)).strip('-')


def clone_device(pt, tpl_name, new_name, used_macs, src=None):
    src = src or pt
    tpl = src.by_name()[tpl_name]
    s = ET.tostring(tpl, encoding='unicode')
    for old in set(re.findall(r'\b[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\b', s)):
        new = _new_mac(used_macs)
        s = s.replace(old, new).replace(old.lower(), new.lower()).replace(_ll(old.upper()), _ll(new))
    d = ET.fromstring(s)
    e = d.find('ENGINE')
    e.find('NAME').text = new_name
    if e.find('SYS_NAME') is not None:
        e.find('SYS_NAME').text = new_name
    _sub(e, 'SAVE_REF_ID', 'save-ref-id:%d' % rnd.randrange(10 ** 17, 10 ** 19))   # older templates may lack it
    if e.find('SERIALNUMBER') is not None:
        e.find('SERIALNUMBER').text = 'PTT%04dQ%s' % (rnd.randrange(10000), ''.join(rnd.choice('0123456789ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(3)))
    old_host = re.sub(r'[^A-Za-z0-9-]', '-', tpl_name)
    for cfg in ('RUNNINGCONFIG', 'STARTUPCONFIG'):
        c = e.find(cfg)
        if c is not None:
            for line in c:
                if line.text and line.text.startswith('hostname '):
                    line.text = 'hostname ' + hostname(new_name)
    lg = d.find('WORKSPACE/LOGICAL')
    lg.find('MEM_ADDR').text = _int_id()
    lg.find('DEV_ADDR').text = _int_id()
    pt.devices.append(d)
    # physical node: copy the template's node, give it a fresh UUID
    tnode, _ = src.node(tpl_name)
    n = copy.deepcopy(tnode)
    n.find('NAME').text = new_name
    n.find('UUID_STR').text = '{%s}' % uuid.uuid4()
    return d, n, old_host


def place_physical(pt, dev, node, parent_name, px, py):
    """Put a device's physical node under parent_name at (px, py) and update the device's own records of it."""
    old = pt.node(dev.find('ENGINE').findtext('NAME'))
    if old is not None:
        par = pt.node_by_uuid(old[1][-1])
        par.find('CHILDREN').remove(old[0])
    parent, ppath = pt.node(parent_name)
    parent.find('CHILDREN').append(node)
    hw, hh = _half(node)
    node.find('X').text = str(int(round(px - hw)))
    node.find('Y').text = str(int(round(py - hh)))
    path = ppath + [parent.findtext('UUID_STR')]
    ws = dev.find('WORKSPACE')
    ws.find('PHYSICAL').text = ','.join(path + [node.findtext('UUID_STR')])
    cp = ws.find('PHYSICAL_CPUR')
    if cp is not None:
        def span(dim, scale, default):
            try:
                v = float(parent.findtext(dim)) / float(parent.findtext(scale))
            except (TypeError, ValueError, ZeroDivisionError):
                v = 0
            return v or default
        w, h = span('W', 'SX', IMG_W), span('H', 'SY', IMG_H)
        cp.find('X').text = node.findtext('X')
        cp.find('Y').text = node.findtext('Y')
        cp.find('X_PN').text = '%g' % (px / w)
        cp.find('Y_PN').text = '%g' % (py / h)
        cp.find('PARENT_PATH').text = ','.join(path)


def make_link(pt, a, a_port, b, b_port, cable):
    names = pt.by_name()
    tpl = next(l for l in pt.links if l.find('CABLE').findall('TYPE')[-1].text == cable)
    l = copy.deepcopy(tpl)
    c = l.find('CABLE')
    c.find('FROM').text = names[a].find('ENGINE').findtext('SAVE_REF_ID')
    c.find('TO').text = names[b].find('ENGINE').findtext('SAVE_REF_ID')
    ports = c.findall('PORT')
    ports[0].text, ports[1].text = a_port, b_port
    c.find('FROM_DEVICE_MEM_ADDR').text = names[a].findtext('WORKSPACE/LOGICAL/MEM_ADDR')
    c.find('TO_DEVICE_MEM_ADDR').text = names[b].findtext('WORKSPACE/LOGICAL/MEM_ADDR')
    c.find('FROM_PORT_MEM_ADDR').text = _int_id()
    c.find('TO_PORT_MEM_ADDR').text = _int_id()
    pt.links.append(l)


# ------------------------------------------------------------------ floor plans
COL = {'lecture': '#e9eef6', 'project': '#e8f2ea', 'office': '#fcdcdc', 'startup': '#f4eee0', 'hall': '#f8f6ec',
       'core': '#dedede', 'room': '#e9eef6', 'terrace': '#e2d6c4', 'void': '#d5e3ec', 'garden': '#dfeadb'}


def render_floor(building, f, network):
    from PIL import Image, ImageDraw, ImageFont
    fdir = 'C:/Windows/Fonts/'
    try:
        F = lambda s, b=False: ImageFont.truetype(fdir + ('arialbd.ttf' if b else 'arial.ttf'), s)
        F(10)
    except OSError:
        F = lambda s, b=False: ImageFont.load_default()
    im = Image.new('RGB', (IMG_W, IMG_H), 'white')
    d = ImageDraw.Draw(im)
    P = lambda x, z: (OX + PX * x, OY + PX * z)
    size = building['size']
    d.rectangle([P(0, 0), P(size, size)], fill='#f5f5f5' if f < 3 else '#ffffff')
    if f == 3:
        for rr in building.get('roof3', []):
            d.rectangle([P(rr[0], rr[1]), P(rr[0] + rr[2], rr[1] + rr[3])], fill='#f5f5f5')
        d.text(P(7.5, 26), '(2F roof below - no access)', fill='#9a9a9a', font=F(14), anchor='mm')
    if f == 1:
        c = building['courtyard']
        d.rectangle([P(c['x'], c['z']), P(c['x'] + c['w'], c['z'] + c['d'])], fill='#cfdecb')
        cx, cz = P(c['x'] + c['w'] / 2, c['z'] + c['d'] / 2)
        d.text((cx, cz), 'Courtyard', fill='#5c7a5c', font=F(22), anchor='mm')
    for v in building['voids'].get(str(f), []):
        d.rectangle([P(v[0], v[1]), P(v[0] + v[2], v[1] + v[3])], fill=COL['void'])
    for o in building.get('outdoor', {}).get(str(f), []):
        d.rectangle([P(o[0], o[1]), P(o[0] + o[2], o[1] + o[3])], fill=COL['terrace'])
    rooms = [r for r in building['rooms'] if r['f'] == f]
    protected = {r['n'] for r in protected_rooms(building)}
    for r in sorted(rooms, key=lambda r: -r['w'] * r['d']):
        col = '#fcdcdc' if r['n'] in protected else ('#e9eef6' if r['k'] == 'office' else COL.get(r['k'], '#e9eef6'))
        if r['k'] == 'void':
            col = COL['void']
        d.rectangle([P(r['x'], r['z']), P(r['x'] + r['w'], r['z'] + r['d'])], fill=col)
    for s in building['stairs']:
        if s['f'] == f:
            d.rectangle([P(s['x'], s['z']), P(s['x'] + s['w'], s['z'] + s['d'])], fill='#dedede')
    for w in building['walls'].get(str(f), []):
        style = {'w': ('#3a3a3a', 4), 'g': ('#3f84d0', 3)}.get(w[4], ('#8a8a8a', 2))
        d.line([P(w[0], w[1]), P(w[2], w[3])], fill=style[0], width=style[1])
    for r in rooms:
        if r['k'] == 'void' and r['w'] * r['d'] < 20:
            continue
        name = r['n']
        bold = r['n'] in protected
        if bold:
            name = room_tag(name) if 'Prof. office' in name else ('220 Dean' if name.startswith('220') else name)
        x, z = P(r['x'] + r['w'] / 2, r['z'])
        size_ = 15 if bold else 13
        while size_ > 9 and d.textlength(name, font=F(size_, bold)) > PX * r['w'] - 4:
            size_ -= 1
        while d.textlength(name, font=F(size_, bold)) > PX * r['w'] - 4 and len(name) > 4:
            name = name[:-2].rstrip() + '…' if not name.endswith('…') else name[:-2].rstrip() + '…'
        d.text((x, z + 8), name, fill='#333333', font=F(size_, bold), anchor='mt')
    d.text((OX, 28), 'W19 Endicott - %dF' % f, fill='#222222', font=F(30, True), anchor='lm')
    d.polygon([(1310, 18), (1300, 42), (1320, 42)], fill='#222222')
    d.text((1325, 31), 'N', fill='#222222', font=F(16, True), anchor='lm')
    d.line([(OX, OY + PX * size + 7), (OX + PX * 10, OY + PX * size + 7)], fill='#222222', width=3)
    d.text((OX + PX * 10 + 8, OY + PX * size + 7), '10 m', fill='#222222', font=F(13), anchor='lm')
    d.rectangle([(1369, OY), (IMG_W - 2, OY + PX * size)], fill='#fdf6e2', outline='#c8a85a', width=3)
    d.text((1560, 108), '%dF devices' % f, fill='#7a5a12', font=F(18, True), anchor='mm')
    d.text((1560, 140), 'photographed on site,', fill='#7a5a12', font=F(14), anchor='mm')
    d.text((1560, 157), 'position not recorded yet', fill='#7a5a12', font=F(14), anchor='mm')
    if f == 3:
        d.text((1560, 1330), 'Roof garden = fire zone R', fill='#7a5a12', font=F(14, True), anchor='mm')
        d.text((1560, 1350), '(flame/heat detectors + sirens)', fill='#7a5a12', font=F(14), anchor='mm')
    if f == 2:
        d.text((1560, 1330), 'Pink = protected room', fill='#7a5a12', font=F(14, True), anchor='mm')
        d.text((1560, 1350), '(detector + siren, VLAN 40)', fill='#7a5a12', font=F(14), anchor='mm')
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


BUILDING = 'W19 Endicott'
FLOOR_X0, FLOOR_DX, FLOOR_Y = 40, 790, 170     # floor containers side by side in the building view


def render_building():
    from PIL import Image, ImageDraw, ImageFont
    try:
        F = lambda s, b=False: ImageFont.truetype('C:/Windows/Fonts/' + ('arialbd.ttf' if b else 'arial.ttf'), s)
        F(10)
    except OSError:
        F = lambda s, b=False: ImageFont.load_default()
    w = FLOOR_X0 + FLOOR_DX * len(FLOORS) + 20
    im = Image.new('RGB', (w, 1000), '#eef1f6')
    d = ImageDraw.Draw(im)
    d.text((40, 54), 'W19 Endicott (Start-up Hall)', fill='#222222', font=F(40, True), anchor='lm')
    d.text((40, 94), 'Team Flame Guard - devices placed from the site survey and the 3D model. Open %s to see each floor.'
           % ' / '.join('%dF' % f for f in FLOORS), fill='#555555', font=F(20), anchor='lm')
    for f in FLOORS:
        d.text((FLOOR_X0 + FLOOR_DX * (f - 1), 142), '%dF' % f, fill='#222222', font=F(30, True), anchor='lm')
    for i, line in enumerate(['Main Wiring Closet - NOT surveyed yet.', 'Router, core, WLC, servers and closet switches',
                              'are assumed to be here (location unknown).']):
        d.text((920, 812 + 23 * i), line, fill='#555555', font=F(20), anchor='lm')
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return buf.getvalue(), w


def layout_building(pt):
    """Widen the building view to fit every floor and put the floors side by side."""
    png, w = render_building()
    set_floor_image(pt, BUILDING, png)
    b = pt.node(BUILDING)[0]
    sx = float(b.findtext('SX') or 0.1)
    for tag in ('W', 'INIT_WIDTH'):
        if b.find(tag) is not None:
            b.find(tag).text = '%g' % (w * sx)
    for f in FLOORS:
        n = pt.node('%dF' % f)[0]
        n.find('X').text = str(FLOOR_X0 + FLOOR_DX * (f - 1))
        n.find('Y').text = str(FLOOR_Y)


def ensure_floor(pt, name, like='2F'):
    """Create an empty floor container (copy of the 2F one, without its devices) if it is missing."""
    if pt.node(name):
        return
    tpl, path = pt.node(like)
    n = copy.deepcopy(tpl)
    for c in list(n.find('CHILDREN')):
        n.find('CHILDREN').remove(c)
    n.find('NAME').text = name
    n.find('UUID_STR').text = '{%s}' % uuid.uuid4()
    n.find('X').text = str(int(tpl.findtext('X')) + 790 * (int(name[0]) - int(like[0])))
    pt.node_by_uuid(path[-1]).find('CHILDREN').append(n)


def set_floor_image(pt, container, png):
    key = base64.b64encode(hashlib.sha256(png).digest()).decode()
    node, _ = pt.node(container)
    old = node.find('PATH').text
    bank = pt.root.find('PIXMAPBANK')
    still_used = sum(1 for n in pt.phys.iter('NODE') if n.find('PATH') is not None and n.find('PATH').text == old) > 1
    for im in list(bank):
        if im.findtext('IMAGE_PATH') == old and not still_used:
            bank.remove(im)
    if not any(im.findtext('IMAGE_PATH') == key for im in bank):
        im = ET.SubElement(bank, 'IMAGE')
        ET.SubElement(im, 'IMAGE_PATH').text = key
        ET.SubElement(im, 'IMAGE_CONTENT').text = base64.b64encode(png).decode()
    node.find('PATH').text = key


# ------------------------------------------------------------------ commands
def load_net():
    return json.loads(NET.read_text(encoding='utf8'))


def m2px(x, z):
    return OX + PX * x, OY + PX * z


def px2m(px, py):
    return round((px - OX) / PX, 2), round((py - OY) / PX, 2)


def expected_parent(dv):
    return dv.get('pt_parent') or ('%dF' % dv['floor'])


def unplaced_px(dv, i):
    return 1400 + (i % 3) * 110, 220 + (i // 3) * 110


def variants(net):
    return net.get('variants') or {'main': {'pt_file': net['pt_file']}}


def in_variant(item, vname, v):
    only = item.get('only')
    if only and only != vname and not (isinstance(only, list) and vname in only):
        return False
    if v.get('zones') is not None and 'kind' in item:           # a cut-down file: these fire zones + named devices only
        if not (item.get('zone') in v['zones'] or item['name'] in v.get('names', [])):
            return False
    st = v.get('statuses')
    return 'status' not in item or not st or item['status'] in st


def variant_view(net, vname):
    """The devices and links that belong in one Packet Tracer file."""
    v = variants(net)[vname]
    devs = [d for d in net['devices'] if in_variant(d, vname, v)]
    names = {d['name'] for d in devs}
    links = [l for l in net['links'] if (not l.get('only') or l['only'] == vname or vname in l['only']) and l['a'] in names and l['b'] in names]
    return v, devs, links


def check(verbose=True):
    net = load_net()
    html, layout, building = load_3d()
    issues = []
    add = issues.append
    devs = {d['name']: d for d in net['devices']}

    # 1. every protected room has a detector + siren
    for r in protected_rooms(building):
        tag = room_tag(r['n'])
        for k in ('Smoke', 'Siren'):
            nm = '%s %s' % (k, tag)
            if nm not in devs:
                add('JSON   missing %s for room "%s"' % (nm, r['n']))
            elif room_at(building, 2, devs[nm]['x'], devs[nm]['z']) != r['n']:
                add('JSON   %s is not inside room "%s"' % (nm, r['n']))
    for r in building['rooms']:
        if r['n'].startswith(OUTDOOR_PROTECTED):
            inside = [d for d in net['devices'] if d.get('floor') == r['f'] and d.get('x') is not None
                      and room_at(building, r['f'], d['x'], d['z']) == r['n']]
            for k in ('heat', 'siren'):
                if not any(d['kind'] == k for d in inside):
                    add('JSON   outdoor area "%s" has no %s' % (r['n'], 'flame/heat detector' if k == 'heat' else 'siren'))
    # 2. JSON vs 3D
    by_id = {o['id']: o for o in layout['devices']}
    linked = set()
    for d in net['devices']:
        if not in_3d(d):
            continue
        o = by_id.get(d.get('layout_id'))
        if o is None:
            add('3D     no 3D item for %s (layout_id %s)' % (d['name'], d.get('layout_id')))
            continue
        linked.add(o['id'])
        placed = d.get('where') != 'unplaced'
        if o['t'] != KIND_3D[d['kind']]:
            add('3D     %s: type %s in 3D, %s in JSON' % (d['name'], o['t'], d['kind']))
        if o.get('status') != d['status']:
            add('3D     %s: status "%s" in 3D, "%s" in JSON' % (d['name'], o.get('status'), d['status']))
        if bool(o.get('placed', True)) != placed:
            add('3D     %s: placed=%s in 3D, %s in JSON' % (d['name'], o.get('placed', True), placed))
        elif placed and (o.get('f') != d['floor'] or abs(o['x'] - d['x']) > POS_TOL or abs(o['z'] - d['z']) > POS_TOL):
            add('3D     %s: at %sF (%.2f, %.2f) in 3D, %sF (%.2f, %.2f) in JSON  -> run "pull" if the 3D one is right'
                % (d['name'], o.get('f'), o['x'], o['z'], d['floor'], d['x'], d['z']))
    for o in layout['devices']:
        if o['t'] in ('ap', 'hub', 'access', 'core', 'router', 'wlc', 'server', 'siren') and o['id'] not in linked:
            add('3D     3D-only %s "%s" (%s, %s) - add it to the JSON or delete it in the 3D editor'
                % (o['t'], o.get('label') or o.get('notes', '')[:50], o['id'], 'placed' if o.get('placed', True) else 'not placed'))
        if o['t'] == 'smoke' and o.get('placed', True) and o['id'] not in linked:
            add('3D     smoke detector %s in the 3D model is not in the JSON (as-is file)' % o['id'])
    single = {x.get('layout_id') for x in net['devices'] if in_3d(x)}
    for d in net['devices']:
        if d['kind'] == 'pc' and d.get('rooms'):
            n3 = sum(o.get('count', 1) for o in layout['devices'] if o['t'] in ('pc', 'pcm') and o.get('placed', True)
                     and o['id'] not in single and room_at(building, o['f'], o['x'], o['z']) in d['rooms'])
            if n3 != d.get('represents', 1):
                where = ', '.join(d['rooms']) if len(d['rooms']) <= 3 else '%d rooms' % len(d['rooms'])
                add('3D     %s stands for %s PCs, the 3D model has %d in %s' % (d['name'], d.get('represents'), n3, where))
    # 3. JSON vs each Packet Tracer file
    for vname in variants(net):
        v, vdevs, vlinks = variant_view(net, vname)
        path = ROOT / v['pt_file']
        tag = 'PT %-8s' % vname
        if not path.exists():
            add('%s file %s not built yet' % (tag, v['pt_file']))
            continue
        pt = PT(path)
        ptd = pt.by_name()
        vnames = {d['name'] for d in vdevs}
        for d in vdevs:
            if d['name'] not in ptd:
                add('%s missing device %s' % (tag, d['name']))
                continue
            info = pt.device_info(ptd[d['name']])
            if info['model'] != d['pt_model']:
                add('%s %s: model %s in PT, %s in JSON' % (tag, d['name'], info['model'], d['pt_model']))
            if info['parent'] != expected_parent(d):
                add('%s %s: inside "%s" in PT, should be "%s"' % (tag, d['name'], info['parent'], expected_parent(d)))
            elif d.get('where') not in ('closet', 'unplaced') and info['px']:
                x, z = px2m(*info['px'])
                if abs(x - d['x']) > POS_TOL or abs(z - d['z']) > POS_TOL:
                    add('%s %s: at (%.2f, %.2f) m in PT, (%.2f, %.2f) m in JSON' % (tag, d['name'], x, z, d['x'], d['z']))
        for n in ptd:
            if n not in vnames:
                add('%s PT-only device %s' % (tag, n))
        key = lambda l: tuple(sorted([(l['a'], l['a_port']), (l['b'], l['b_port'])]))
        ptl = {key(l): l for l in pt.link_list()}
        jl = {key(l): l for l in vlinks}
        for k, l in jl.items():
            if k not in ptl:
                add('%s missing link %s %s <-> %s %s' % (tag, l['a'], l['a_port'], l['b'], l['b_port']))
        for k, l in ptl.items():
            if k not in jl:
                add('%s PT-only link %s %s <-> %s %s' % (tag, l['a'], l['a_port'], l['b'], l['b_port']))
        seen = set()
        for l in vlinks:
            for e in ((l['a'], l['a_port']), (l['b'], l['b_port'])):
                if e in seen:
                    add('%s port %s %s used by two links' % ((tag,) + e))
                seen.add(e)
    if verbose:
        print('\n'.join(issues) if issues else 'All in sync: JSON, 3D model and Packet Tracer agree.')
        print('\n%d issue(s).' % len(issues))
    return issues


def pull():
    net = load_net()
    _, layout, _ = load_3d()
    by_id = {o['id']: o for o in layout['devices']}
    moved = 0
    for d in net['devices']:
        o = by_id.get(d.get('layout_id'))
        if o and o.get('placed', True) and in_3d(d):
            if d.get('where') == 'unplaced' or abs(o['x'] - d['x']) > POS_TOL or abs(o['z'] - d['z']) > POS_TOL or o['f'] != d['floor']:
                d.update(floor=o['f'], x=round(o['x'], 2), z=round(o['z'], 2))
                d.pop('where', None)
                moved += 1
    NET.write_text(json.dumps(net, indent=1, ensure_ascii=False) + '\n', encoding='utf8')
    print('pulled %d position(s) from the 3D model into %s' % (moved, NET.name))


def _sub(parent, tag, text=None):
    el = parent.find(tag)
    if el is None:
        el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def _first_eth(e):
    for port in e.iter('PORT'):
        if port.findtext('TYPE', '').startswith(('eCopperFastEthernet', 'eCopperGigabitEthernet')):
            return port
    return None


def apply_config(dev, cfg, pt=None):
    """cfg keys: ios [lines] + vlans [(id, name)] for routers/switches; dhcp (bool) or ip {ip, mask, gw, dns} for end devices;
    iot_client {server, user, password}; dhcp_pools / dns_records / iot_server for servers; script_patch [[old, new]]."""
    e = dev.find('ENGINE')
    if cfg.get('vlans') and e.find('VLANS') is not None:
        vl = e.find('VLANS')
        have = {v.get('number') for v in vl}
        for vid, name in cfg['vlans']:
            if str(vid) not in have:
                ET.SubElement(vl, 'VLAN', {'name': name, 'number': str(vid), 'rspan': '0'})
    if cfg.get('ip'):
        c = cfg['ip']
        port = _first_eth(e)
        _sub(port, 'IP', c['ip'])
        _sub(port, 'SUBNET', c['mask'])
        _sub(port, 'PORT_GATEWAY', c.get('gw', ''))
        _sub(port, 'PORT_DNS', c.get('dns', ''))
        _sub(port, 'PORT_DHCP_ENABLE', 'false')
        _sub(e, 'GATEWAY', c.get('gw', ''))
        if e.find('DNS_CLIENT') is not None:
            _sub(e.find('DNS_CLIENT'), 'SERVER_IP', c.get('dns', ''))
    if cfg.get('iot_client'):
        c = cfg['iot_client']
        ic = _sub(e, 'IOE_CLIENT')
        _sub(ic, 'CLIENT_MODE', 'REMOTE_SERVER')
        _sub(ic, 'SERVER_ADDRESS', c['server'])
        _sub(ic, 'USERNAME', c['user'])
        _sub(ic, 'PASSWORD', c['password'])
    if cfg.get('dhcp_pools'):
        srv = e.find('DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER')
        srv.find('ENABLED').text = '1'
        pools = srv.find('POOLS')
        tpl = copy.deepcopy(pools.find('POOL'))
        for p in list(pools):
            pools.remove(p)
        for p in cfg['dhcp_pools']:
            x = copy.deepcopy(tpl)
            for tag, val in (('NAME', p['name']), ('NETWORK', p['network']), ('MASK', p['mask']), ('DEFAULT_ROUTER', p['gw']),
                             ('START_IP', p['start']), ('DNS_SERVER', p['dns']), ('MAX_USERS', str(p['max'])),
                             ('WLC_ADDRESS', p.get('wlc', '0.0.0.0'))):
                _sub(x, tag, val)
            end = int.from_bytes(bytes(int(o) for o in p['start'].split('.')), 'big') + p['max'] - 1
            _sub(x, 'END_IP', '.'.join(str((end >> s) & 255) for s in (24, 16, 8, 0)))
            pools.append(x)
    if cfg.get('dns_records') and e.find('DNS_SERVER') is not None:
        ds = e.find('DNS_SERVER')
        ds.find('ENABLED').text = '1'
        db = _sub(ds, 'NAMESERVER-DATABASE')
        for r in list(db):
            db.remove(r)
        for host, ip in cfg['dns_records']:
            rr = ET.SubElement(db, 'RESOURCE-RECORD')
            ET.SubElement(rr, 'TYPE').text = 'A-REC'
            ET.SubElement(rr, 'NAME').text = host
            ET.SubElement(rr, 'TTL').text = '86400'
            ET.SubElement(rr, 'IPADDRESS').text = ip
    if cfg.get('iot_server') and pt is not None:
        c = cfg['iot_server']
        names = pt.by_name()
        serial = lambda n: names[n].find('ENGINE').findtext('SERIALNUMBER')
        _sub(e, 'REGISTRATION_SEVER', 'true')
        um = _sub(e, 'IOE_USER_MANAGER')
        for x in list(um):
            um.remove(x)
        u = ET.SubElement(ET.SubElement(um, 'USERS'), 'USER')
        ET.SubElement(u, 'NAME').text = c['user']
        ET.SubElement(u, 'PASSWORD').text = c['password']
        ds = ET.SubElement(u, 'DEVICES')
        for n in [n for n in c['register'] if n in names]:
            x = ET.SubElement(ds, 'IOE_DEVICE')
            ET.SubElement(x, 'NAME')
            ET.SubElement(x, 'SERIAL').text = serial(n)
            ET.SubElement(x, 'ALIAS').text = n
            ET.SubElement(x, 'TYPE').text = names[n].find('ENGINE/TYPE').get('model')
        ET.SubElement(u, 'IOE_CONDITIONS')
        rs = ET.SubElement(u, 'IOE_RULES')
        for r in c['rules']:
            det, state, val = r['if']
            r = dict(r, then=[a for a in r['then'] if a[0] in names])
            if det not in names or not r['then']:
                continue
            rule = {'actions': [{'serialNum': serial(s), 'stateName': st, 'stateValue': v, 'type': 'deviceState'} for s, st, v in r['then']],
                    'condition': {'conditions': [{'serialNum': serial(det), 'stateName': state, 'type': 'deviceBoolState', 'value': val}],
                                  'operator': 'and', 'type': 'logicalGroup'},
                    'enabled': True, 'lastError': '', 'name': r['name']}
            ET.SubElement(ET.SubElement(rs, 'IOE_RULE'), 'JSON').text = json.dumps(rule, separators=(', ', ' : '))
    if cfg.get('script_patch'):
        for t in e.iter('TEXT'):
            if t.text:
                for old, new in cfg['script_patch']:
                    t.text = t.text.replace(old, new)
    if cfg.get('ios'):
        for tag in ('RUNNINGCONFIG', 'STARTUPCONFIG'):
            c = e.find(tag)
            if c is None:
                continue
            for line in list(c):
                c.remove(line)
            for text in cfg['ios']:
                ET.SubElement(c, 'LINE').text = text
    if 'dhcp' in cfg:
        for port in e.iter('PORT'):
            flag = port.find('PORT_DHCP_ENABLE')
            if flag is not None and port.findtext('TYPE', '').startswith(('eCopperFastEthernet', 'eCopperGigabitEthernet')):
                flag.text = 'true' if cfg['dhcp'] else 'false'


def build_pkt(net, vname, building):
    v, vdevs, vlinks = variant_view(net, vname)
    out = ROOT / v['pt_file']
    src = PT(ROOT / v.get('template_file', v['pt_file']))     # template file: has one of every device model
    pt = PT(out) if out.exists() else PT(ROOT / v.get('template_file', v['pt_file']))
    used = _all_macs(pt.root) | _all_macs(src.root)
    devs = {d['name']: d for d in vdevs}

    for d in vdevs:                                             # renames
        old = d.get('was')
        names = pt.by_name()
        if old and old in names and d['name'] not in names:
            e = names[old].find('ENGINE')
            e.find('NAME').text = d['name']
            if e.find('SYS_NAME') is not None:
                e.find('SYS_NAME').text = d['name']
            for cfg in ('RUNNINGCONFIG', 'STARTUPCONFIG'):
                for line in (e.find(cfg) if e.find(cfg) is not None else []):
                    if line.text and line.text.startswith('hostname '):
                        line.text = 'hostname ' + hostname(d['name'])
            pt.node(old)[0].find('NAME').text = d['name']
    for n, dv in list(pt.by_name().items()):                    # remove devices not in this file
        if n not in devs:
            ref = dv.find('ENGINE').findtext('SAVE_REF_ID')
            for l in list(pt.links):
                c = l.find('CABLE')
                if ref in (c.findtext('FROM'), c.findtext('TO')):
                    pt.links.remove(l)
            node = pt.node(n)
            if node:
                pt.node_by_uuid(node[1][-1]).find('CHILDREN').remove(node[0])
            pt.devices.remove(dv)
    for f in FLOORS:
        ensure_floor(pt, '%dF' % f)
    unplaced_i = {}
    for d in vdevs:                                             # add / move devices
        names = pt.by_name()
        if d['name'] in names:
            dev = names[d['name']]
            node = pt.node(d['name'])[0]
        else:
            tsrc = PT(d['pt_template_file']) if d.get('pt_template_file') else src
            snames = tsrc.by_name()
            tpl = d.get('pt_template')
            if tpl and tpl not in snames:
                tpl = next((x['name'] for x in net['devices'] if x.get('was') == tpl), None)
            if not tpl or tpl not in snames:
                tpl = next(n for n, x in snames.items() if x.find('ENGINE/TYPE').get('model') == d['pt_model'])
            dev, node, _ = clone_device(pt, tpl, d['name'], used, tsrc)
        parent = expected_parent(d)
        if d.get('where') == 'closet':
            hw, hh = _half(node)
            px, py = d.get('pt_px', [float(node.findtext('X')), float(node.findtext('Y'))])
            px, py = px + hw, py + hh
        elif d.get('where') == 'unplaced':
            i = unplaced_i.setdefault(parent, [0])
            px, py = unplaced_px(d, i[0])
            i[0] += 1
        else:
            px, py = m2px(d['x'], d['z'])
        place_physical(pt, dev, node, parent, px, py)
        lg = (d.get('logical_by_file') or {}).get(vname) or d.get('logical')
        if lg:
            dev.find('WORKSPACE/LOGICAL/X').text = str(lg[0])
            dev.find('WORKSPACE/LOGICAL/Y').text = str(lg[1])
        cfg = (d.get('pt_config') or {}).get(vname)
        if cfg:
            apply_config(dev, {k: v for k, v in cfg.items() if k != 'iot_server'})
    seen = set()                                                # duplicate serial numbers break IoT registration
    for dv in pt.devices:
        e = dv.find('ENGINE')
        sn = e.find('SERIALNUMBER')
        if sn is None:
            continue
        while sn.text in seen:
            pre = sn.text[:3] if sn.text[:3].isalpha() else 'PTT'
            sn.text = '%s%04dQ%s' % (pre, rnd.randrange(10000), ''.join(rnd.choice('0123456789ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(3)))
        seen.add(sn.text)
    names_now = pt.by_name()
    for d in vdevs:                                             # IoT rules need every device's serial number
        cfg = (d.get('pt_config') or {}).get(vname) or {}
        if cfg.get('iot_server'):
            apply_config(names_now[d['name']], {'iot_server': cfg['iot_server']}, pt)
    key = lambda a, ap, b, bp: tuple(sorted([(a, ap), (b, bp)]))
    want = {key(l['a'], l['a_port'], l['b'], l['b_port']): l for l in vlinks}
    names = pt.ref_names()
    have = set()
    for l in list(pt.links):
        c = l.find('CABLE')
        p = [x.text for x in c.findall('PORT')]
        k = key(names.get(c.findtext('FROM')), p[0], names.get(c.findtext('TO')), p[1])
        if k in want and k not in have:
            have.add(k)
        else:
            pt.links.remove(l)
    for k, l in want.items():
        if k not in have:
            make_link_from(pt, src, l)
    for note in pt.root.iter('NOTE'):                          # logical-view notes: {"first words": "new text"}
        for start, text in (net.get('pt_notes') or {}).get(vname, {}).items():
            if (note.findtext('TEXT') or '').startswith(start):
                note.find('TEXT').text = text
    for f in FLOORS:
        set_floor_image(pt, '%dF' % f, render_floor(building, f, net))
    layout_building(pt)
    pt.save(out)
    return out.name


def make_link_from(pt, src, l):
    """make_link, but the cable template may come from the template file."""
    tpl_links = [x for x in list(pt.links) + list(src.links) if x.find('CABLE').findall('TYPE')[-1].text == l['cable']]
    names = pt.by_name()
    lk = copy.deepcopy(tpl_links[0])
    c = lk.find('CABLE')
    c.find('FROM').text = names[l['a']].find('ENGINE').findtext('SAVE_REF_ID')
    c.find('TO').text = names[l['b']].find('ENGINE').findtext('SAVE_REF_ID')
    ports = c.findall('PORT')
    ports[0].text, ports[1].text = l['a_port'], l['b_port']
    c.find('FROM_DEVICE_MEM_ADDR').text = names[l['a']].findtext('WORKSPACE/LOGICAL/MEM_ADDR')
    c.find('TO_DEVICE_MEM_ADDR').text = names[l['b']].findtext('WORKSPACE/LOGICAL/MEM_ADDR')
    c.find('FROM_PORT_MEM_ADDR').text = _int_id()
    c.find('TO_PORT_MEM_ADDR').text = _int_id()
    pt.links.append(lk)


def build():
    net = load_net()
    html, layout, building = load_3d()
    only = sys.argv[2] if len(sys.argv) > 2 else None
    built = [build_pkt(net, vname, building) for vname in variants(net) if not only or vname == only]

    by_id = {o['id']: o for o in layout['devices']}
    for d in net['devices']:
        if not in_3d(d):
            continue
        o = by_id.get(d.get('layout_id'))
        if o is None:
            o = {'id': d.get('layout_id') or 'net-' + re.sub(r'[^a-z0-9]+', '-', d['name'].lower()), 't': KIND_3D[d['kind']],
                 'label': d['name'], 'count': 1, 'notes': d.get('notes', ''), 'photo': ''}
            if 'rot' in d:
                o['rot'] = d['rot']
            d['layout_id'] = o['id']
            layout['devices'].append(o)
            by_id[o['id']] = o
        o['status'] = d['status']
        if d.get('where') == 'unplaced':
            o['placed'] = False
        else:
            o.update(placed=True, f=d['floor'], x=d['x'], z=d['z'])
    save_3d(html, layout)
    LAYOUT_JSON.write_text(json.dumps({'building': 'W19 Endicott', 'note': 'devices/links = editable layout; building = traced floor plans (metres, 54 x 54 m footprint)',
                                       'layout': layout, 'building_model': building}, indent=1, ensure_ascii=False) + '\n', encoding='utf8')
    NET.write_text(json.dumps(net, indent=1, ensure_ascii=False) + '\n', encoding='utf8')
    print('built %s, index.html and %s' % (', '.join(built), LAYOUT_JSON.name))
    check()


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    {'check': check, 'pull': pull, 'build': build}[cmd]()
