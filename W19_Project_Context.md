# Team Flame Guard – W19 Network Upgrade Project: Full Context

This file sums up the whole project so far: the assignment, the team, the Notion workspace, the weekly reports, the W19 site survey, and the 3D walkthrough editor. Paste it into a new chat (or share it with a teammate) to continue the work without losing context.

Last updated: 5 Nov 2026.

---

## 1. The assignment

| Item | Detail |
|---|---|
| Course | Computer Networks (PBL class) |
| Professor | Prof. Edward Youngil Kim |
| Class time / room | Wednesdays 13:00–16:00, S2-401 |
| Project title | "Save the Professor's Life When Fires" |
| Building | W19 – Endicott Building (Start-up Hall) |

**Problem statement:** the wired and wireless network of the Endicott building (W19) has slowed down severely. The team must investigate the current network, design a new one with Cisco's latest products, and add fire detection, alarms and sirens to protect the professors.

**The five project parts**

1. Investigate the current W19 network configuration and office layout.
2. Improve and upgrade the W19 network with the latest Cisco products, simulated in Cisco Packet Tracer.
3. Add a fire detector, alarm and siren to each professor's office.
4. Estimate the total cost of the upgrade.
5. Present and demonstrate the upgraded network.

**Schedule (course weeks)**

| Course week | Date | Milestone |
|---|---|---|
| Week 9 | 28 Oct | Motivation – PBL introduction, team formed, ground rules signed |
| Week 10 | 4 Nov | Investigate W19 network configuration and office layout |
| Week 11 | 11 Nov | **Proposal presentation** (15 min incl. Q&A, max 15 slides) |
| Week 12 | 18 Nov | Plan and design the network – build the initial network |
| Week 13 | 25 Nov | **Progress presentation** |
| Week 14 | 2 Dec | Upgrade and improve the W19 network |
| Week 15 | 9 Dec | **Completion presentation and demonstration** |

**Deliverables:** team name and signed ground rules; team roles (R&R); proposal, progress and completion presentation files; the Packet Tracer file (.pkt); the Notion cooperation-history link; individual contribution journal and peer evaluation.

**Grading (40 points):** proposal 10, completion presentation 20, individual contribution and peer evaluation 10.

**Proposal outline (from the course slides):** cover page (course, title, team, roles), project summary, background and problem description, things to investigate, project constraints, project goals, project schedule, references.

**Reference material supplied with the course:** Cisco Packet Tracer and the NetAcad "Getting Started with Cisco Packet Tracer" course, the paper *Boosting Campus Network Design Using Cisco Packet Tracer* (Shemsi, 2017), the Cisco Campus LAN and WLAN Solution Design Guide, and the Cisco Catalyst 8300 Software Configuration Guide (IOS XE 17).

---

## 2. The team

**Team name:** Flame Guard.

**Members:** Pushkal (Vashist Pushkal), Emon, Sadat, Islam, Hassan. Roles were divided at the start, but who holds which role is not written down here.

**Signed ground rules (as signed on 28 Oct)**

1. Report in advance if absent
2. Do not be late to class
3. Do weekly tasks in time
4. If you don't know – ask your teammates
5. In case of disagreement, a majority vote will be used to resolve it
7. Check a group chat at least once a day
8. Update your progress status in Google Docs
9. Miss 2 meetings = buy coffee for the whole team
10. Divide work equally
11. If you do not have time for the meeting – tell in advance

The signed sheet skips number 6, and rule 8 says Google Docs although the course requires Notion. A themed "more creative" rewrite was also drafted (e.g. "No silent alarms", "Majority holds the extinguisher", "Two no-shows, one coffee run"); it would need to be signed again if used.

---

## 3. Notion workspace and weekly reports

- **Main Notion page:** Flame Guard – W19 Network Upgrade & Fire Alarm (Computer Networks PBL) – https://app.notion.com/p/40d1b981963c81f59d9bcbe5f6b45024. It holds course info, key links, the roles table, scope, milestones, deliverables checklist, proposal outline and ground rules. Nothing on it mentions Claude or AI. Notion still shows Pushkal's account as the creator.
- **Team Google Slides deck:** https://docs.google.com/presentation/d/1X1kVvwibE0ULXPAQmRIuFpoeVJjYWeNVdYRDVKANrHU/edit?usp=sharing (linked on the main page and in every weekly report).
- **Weekly Reports database** (inside the main page): one page per course week, titled in the team's own format, *Team "Flame Guard" – Week 9* through *Week 15*. Each page has a "Submission Date" line and a simple two-column table, Current Week Status | Next Week Plan, using the professor's style: "- Task" then ". sub-task (progress) – date", with "- issue:" lines. A blank template page is also there.
- **Submission dates:** Week 9 – 2026.10.28, Week 10 – 2026.11.04, Week 11 – 2026.11.11, Week 12 – 2026.11.18, Week 13 – 2026.11.25, Week 14 – 2026.12.02, Week 15 – 2026.12.09.
- **Weekly report PDFs:** fillable PDFs were made in the exact style of the team's Week 9 report (A4 landscape, title, black header bars, grey panels, editable bold "task" boxes and regular "sub-item" boxes, editable submission date). Week 9 contains the team's original content and Weeks 10–15 are blank. They must be dragged onto the Notion pages by hand. Notion can only preview PDFs, so editing means downloading, filling in Chrome/Edge/Acrobat, and re-uploading. A Google Slides template was suggested as an easier editable option.
- **Week 9 report (original content):** signed the team ground rules paper; investigated W19 network configuration (took images of fire detectors and related equipment – 56 images collected); divided responsibilities among team members. Next week plan: continue investigation (W19 network configuration; fire detectors and related equipment); start the project proposal. The professor said this report was not detailed enough.

---

## 4. W19 site survey – what we know

### Building basics (from the 1F directory sign and the 2F emergency exit map)

- Three floors. 1F: Start-up Hall (double height), lecture rooms 101–111, 112 Start-up Center, courtyard in the middle. 2F: Innovation Eco System, start-up education, idea room, department, professors' offices, President and Vice Dean offices. 3F: Start-up Playground and roof garden (not surveyed).
- **1F rooms:** 101 Online lecture room; WC (W/M); 102 Lecture; 103 Project; 104 Lecture; 105 Lecture; 106 Project; 107 Project; 108 Lecture; 109 Lecture; 110 Project; 111 Lecture; 112 Start-up Center; elevator and WC block in the south-west; west entrance into the Start-up Hall; a courtyard entrance from the hall.

### 2F layout as confirmed on site by Pushkal

- **North side:** two rows of rooms (202–213) with a corridor between them; toilets at the west end next to an empty lobby area. A wall sign says "Offices 202–217".
- **East side, from the north end:** 214, 215, 216, 217, then 218 directly next to the east stairwell. 218 lines up with 217.
- **East stairwell:** from the east terrace a small door opens straight onto a wide stairwell going down to 1F (door width = stair width). 218 is on one side of it and the TA / International Administrative Center office on the other. The TA office has a door from the glass corridor and another door at its far end into the south corridor.
- **South-east, after the TA office:** the Conference Room (one large room, door and frosted panel), then **220 – Dean of ECIS, John H. Yun**. There is **no 219 office**.
- **Professors' offices (south side):** walking west from the east end, left/right pairs are 221/222, 223/224, 225/226, 227/228, 229/230, 231/232.
- **Professors' offices (north and east sides):** the rooms opposite the south offices, 202–213 (two rows), plus 214–217 on the east side, matching the "Offices 202–217" sign. Confirmed on site (20 Nov 2026): 202 is first outside 201, 203 is directly opposite it, and the numbers continue in opposite pairs (204/205 … 212/213) along the corridor.
- **Office count:** 30 rooms in all: 28 professors' offices (202–217 and 221–232), the Dean's office (220) and the Conference Room. Every one of them gets a detector, alarm and siren.
- **201 – AI Research Institute (WAVE, AI & Bigdata Dept.):** frosted glass front with the door at the corner; workstation rows for five labs (1 AI security, 2 Intelligent MSiP, 3 Advanced AI, 4 AX, 5 AI for Industrial App.) and a meeting room with a long table. Next to 201 there is an opening down into the Start-up Hall with a mesh railing (no stairs in it).
- **West side:** a corridor along the courtyard windows. The Start-up Hall below is open to 2F, with mesh railings along the edge. A stair runs up from the hall to 2F along the windows at the north end, with a single railing at its top.
- **South-west stairs:** a stair from the hall up to 2F, with a second flight to 3F stacked directly above it (same width, same direction). The 3F flight starts from a small 2F landing at the far end.
- **North-west stairs to 3F:** a narrow stairwell between the west windows and 201's side wall, signed "Startup Playground / Roof Garden".
- **Courtyard and terrace:** the courtyard is paved in grey tiles with some wooden squares. Two open steel stairs go from the courtyard up to an open wooden-deck terrace on the east side, with a solid metal parapet along the courtyard edge.

### Equipment found (photos and notes)

- **Wi-Fi:** Cisco access points labelled WSU_W19_2F_33D8, WSU_W19_2F_4008, WSU_W19_2F_2C00, WSU_W19_2F_4280 (the only AP in the middle of the east/north corridor route) and WSU_W19_2F_2860 (in the empty area in front of the toilets). Exact model numbers are still unknown.
- **Ceiling hubs (Umbrix brand):** 02F_HUB_A / WSU_1902_A and 02F_HUB_B / WSU_1902_B. Hub B sits next to AP 4280.
- **Security:** motion sensors – 2 at the start of the corridor by 218, 1 in the middle by AP 4280, 2 at the end before the toilets; dome CCTV cameras, including one at the far end of the corridor.
- **Fire safety:** round smoke detectors throughout (4 in the corridor before the west stairs), hydrant cabinets with fire bell, call point and lamp, fire extinguishers, exit signs, evacuation maps, and red sprinkler pipes in the mesh ceilings.
- **AV:** wall and ceiling speakers, projectors, a lecture-capture camera, and a lectern cabinet with a PC and audio amplifier.
- **PCs on 2F:** professors' offices 221/1, 222/2, 223/1, 224/1, 225/1, 226/1, 227/1, 228/2, 229/1, 230/2, 231/1, 232/2; rooms 215, 216 and 217 have 6 PCs each with desks; the TA office has 7 PCs on its tables plus 12 desks with PCs in three groups of 4; 201 has 24 workstations.

### Still missing / to verify

- The network closet (core/distribution switches, router, patch panels, campus uplink) – the most important gap.
- AP and hub model numbers (photograph the back labels) and the cable category printed on the ceiling cables.
- Speed tests (Wi-Fi and wired, busy vs quiet times) to back up the "network is slow" problem statement.
- Inside every professor's office: which already have a detector, alarm or siren.
- Location and type of the fire alarm control panel.
- 3F layout.
- Wall network ports per room.
- The 1F sketch legend letters (W assumed Wi-Fi AP, S smoke detector, F extinguisher, C computers; M unknown).
- Room number check: the Conference Room notice says the International Administrative Center is "W19 Room 218", while the model treats 218 as the room on the other side of the stairs.

---

## 5. The 3D tools

| Tool | Link | Status |
|---|---|---|
| First 3D layout editor | https://claude.ai/artifact/JrE3F3x1S7UUQjXTnqL1T2 | Older; rough layout; kept for reference |
| **W19 walkthrough editor (main)** | https://claude.ai/artifact/X67q7aVNSoDwzzyfQGN37F | Current – all survey updates are here |

**What the walkthrough editor does**

- **Overview mode:** 3D building with floors 1F/2F/3F, top view, device lists, filters by category (Network, Fire safety, Security, AV & computers, Furniture, Other), undo, export/import JSON, and a "To place" tray for photographed devices whose location was not recorded.
- **Walk mode:** first and third person (V key or button), W A S D or an on-screen stick, real stair walking between floors, and a minimap (tap to jump). Tap a ceiling, wall or floor to place a device at that height; "Move (tap a new spot)" moves one.
- **Devices and furniture:** realistic models for APs, hubs, switches, routers, controllers, racks, servers, smoke and heat detectors, alarms, sirens, sprinklers, hydrant cabinets, extinguishers, fire panels, IoT gateways, CCTV, motion sensors, PCs (with desk or on a table), projectors and speakers; furniture such as tables, desks, chairs, sofas, round tables, bookshelves, filing cabinets, whiteboards and plants. Everything has a rotation control (R key).
- **Each item stores:** type, label, floor, position, height, rotation, quantity, status (Existing checked / Existing not yet checked / Proposed / To remove), notes, photo reference, and cable links (Ethernet, fibre, wireless, fire-alarm wiring).
- **Saving:** "Save layout" saves to the shared artifact for the team. Each browser also keeps an unsaved draft and offers Restore or Discard on the next visit.

**Current layout (saved 5 Nov, 08:45 UTC):** 373 items, 26 still in "To place", 1 cable link.

| Item | 1F | 2F |
|---|---|---|
| PCs | 24 | 103 (96 with desks + 7 on tables) |
| Smoke detectors | 7 | 47 |
| Motion sensors | 7 | 16 |
| Fire extinguishers | 4 | 3 |
| Hydrant cabinets | 1 | 1 |
| Projectors | 3 | 1 |
| Wi-Fi access points | – | 5 |
| Ceiling hubs | – | 2 |
| CCTV cameras | – | 5 |
| Speakers | – | 2 |

Plus furniture (85 chairs, 26 tables, 4 round tables, 1 whiteboard).

---

## 6. Files in this export

- **w19-walkthrough-editor.html** – the complete editor as one file. Open it in Chrome or Edge with an internet connection (it loads three.js from a CDN). You can edit and use Export JSON. The "Save layout" button only works on the Claude-hosted page.
- **w19-layout.json** – every device, cable link and the traced building model (walls, rooms, openings, stairs), in metres on a 54 × 54 m footprint. It can be re-imported with "Import JSON" in the editor's View tab, or used for counts and cost estimates.
- **W19_Project_Context.md** – this file.

---

## 7. Suggested next steps

1. Finish the Week 10 report and the Week 11 proposal deck (8 sections, max 15 slides), using the survey facts above.
2. Visit the network closet with the IT office; record switch, router and patch-panel models and the uplink.
3. Run speed tests on 1F and 2F.
4. Check each professor's office for existing fire devices; plan one detector, alarm and siren per office.
5. Build the Packet Tracer topology (core/distribution/access, VLANs for staff, students, Wi-Fi and IoT fire system, wireless controller, IoT fire devices with a registration server).
6. Build the cost estimate from the device counts in w19-layout.json.

---

## 8. Keeping the 3D model and Packet Tracer in sync (added 17 Nov 2026)

- **w19-network.json** is the single source of truth for the network: every device (name, Packet Tracer model, floor, x/z in metres, status, fire zone, VLAN), every link, and the VLAN plan.
- **tools/w19_sync.py** (needs Python 3 + Pillow):
  - `python tools/w19_sync.py check`: lists every difference between the JSON, the 3D model (index.html) and the .pkt.
  - `python tools/w19_sync.py pull`: copies device positions moved in the 3D editor back into the JSON.
  - `python tools/w19_sync.py build`: rewrites W19-network-layout.pkt (devices, links, floor-plan maps) and the 3D model from the JSON.
- **tools/pkt_crypto.py** reads and writes the Packet Tracer file format directly, so the .pkt can be generated without clicking.
- **Fire zones:** N = 202–213 (switch 2F-FIRE-N), E = 214–217, 220 Dean, Conference Room (2F-FIRE-E), S = 221–232 (2F-FIRE-S), R = all of 3F on switch 3F-FIRE: roof garden (artificial grass: 3 outdoor flame/heat detectors + 2 sirens; Packet Tracer's Smoke Detector stands in for the flame detector), Start-up Playground (3 smoke + 2 sirens), Sol Venture studio (smoke + siren), 3F lobby (smoke). 3F Wi-Fi (proposed): 3F-ACC with 3 APs in the Playground, 1 in the studio and 2 outdoor APs on the roof garden. As-is: no network devices on 3F. Each protected room has "Smoke <room>" and "Siren <room>" in both the 3D model and Packet Tracer.
- **Two Packet Tracer files come from the same JSON** (`variants` in the JSON):
  - **W19-as-is.pkt**: today's network. Only devices seen on site plus labelled assumptions (WSU-CAMPUS-GW, W19-CLOSET-SW, WSU-WLC), one flat VLAN 1, DHCP 172.19.0.0/22 from the assumed campus gateway, and the 64 existing smoke detectors (not networked).
  - **W19-network-layout.pkt**: upgrade draft (core, WLC, servers, three fire zones). Configs still to be agreed; the final upgraded network will be its own new file.
  - Build one file only: `python tools/w19_sync.py build as-is` (or `draft`).
- **Close Packet Tracer before running build**, and don't save over a built file from an old Packet Tracer window.
- **1F (updated 18 Nov 2026):** every 1F room (101–111, both 112 rooms, Storage, Start-up Hall) has 2 smoke detectors ("Smoke 1F <room> #1/#2"). As-is: stand-alone, no cable. Upgrade: the same detectors cabled to 1F-FIRE-N (101–107) and 1F-FIRE-S (108–112, Storage, Hall) on VLAN 40. PCs: 101 has 22, 112 Start-up center 12, one each in 102, 103, 110, 111, and lectern PCs in 104, 105, 108, 109.

---

## 9. IP plan, fire simulation and progress slides (added 22 Nov 2026)

- **IP addressing plan:** `tools/w19_ipplan.py` writes every device's config into `w19-network.json` (`pt_config.draft`) and the full table into **docs/IP_PLAN.md**. Site block 10.19.0.0/16, third octet = VLAN, gateway .1 on W19-CORE SVIs: 10 Faculty, 20 Labs, 30 Staff Wi-Fi, 32/34/36/38 student Wi-Fi (/23), 40 Fire IoT, 50 Security, 60 Servers, 99 Mgmt, 999 native. R1-CORE 10.19.255.0/30. W19-SRV 10.19.60.10 (DHCP pools + DNS), FIRE-IOT-SRV 10.19.60.20. Fire devices static: Smoke 2xx = 10.19.40.1xx, Siren 2xx = 10.19.40.2xx (Conference .119/.219), 1F .11-.40, 3F .41-.53. ACLs FIRE-IN/FIRE-OUT on Vlan40: fire devices talk only to the alert server.
- **Rebuild:** `python tools/w19_ipplan.py` then `python tools/w19_sync.py build draft` (and `build fire-demo`). Close Packet Tracer first.
- **Packet Tracer fire simulation (scenario S1, office 221):** "FIRE 221 (smoke source)" = a Things > Old Car whose script adds 1.5 % smoke/s. Each detector trips at 40 % and reports to FIRE-IOT-SRV (user/password flameguard); rule "FIRE 2xx" turns on Siren 2xx. Detector scripts are patched to report on alarm change and to re-send the 0 -> 1 edge every 5 s (lost packets otherwise left some sirens silent). The build also fixes duplicate serial numbers (cloned devices shared serials, which broke IoT registration for 222-232).
- **W19-fire-demo.pkt** = fast cut-down copy (core, FIRE-IOT-SRV, the three 2F fire zones) for the live demo; the full W19-network-layout.pkt becomes very slow with ~260 devices. Demo: open, wait ~1 min, Physical > WSU Campus > W19 Endicott > 2F, Alt+click the red car in 221 -> all 30 sirens on 2F sound (PT keeps one smoke value per floor). Verified 22 Nov: all 30 sirens on; ACL counters 2,025 / 1,815 matches.
- **3D fire drill:** index.html has a "Fire drill" button: smoke spreads through the real floor plan (BFS around the courtyard), networked detectors trip at 40 %, HUD shows the alarm path with IPs/ports, sirens pulse, the professor in 221 evacuates, flashover at T+2:30. URL `index.html?fire=221&t=45` (`&cam=top`) jumps to a moment for screenshots. Key numbers: detected T+0:16, Siren 221 +46 ms, professor at the east stairs T+0:40 with 0 % corridor smoke. (Not yet copied into w19-walkthrough-editor.html / the Claude artifact.)
- **Progress slides (Week 13, 25 Nov):** Notion page "Progress Slides Reference (Week 13)" under the main page: 15 slides with screenshots, speaker notes and owners (Hassan 1, 2, 10, 11; Sadat 4-6; Emon 7, 8, 14; Islam 3, 9, 15; Pushkal 12, 13). Images in docs/slides/.
- **Open items:** 3F-ACC uplink and some AP links show down in the full file; WLC/SSID config; QoS on VLAN 40; closet survey; cost estimate.
