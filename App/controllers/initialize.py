from App.controllers.studentGroup import add_studentGroup
from App.database import db
from .lot import create_lot, get_lot
from .labType import create_lab_type
from .student import create_student
from .admin import create_admin
from .group import create_group, approve_group
from .lotGroup import add_lotGroup, assign_exclusive_lots
from .rfp import create_rfp, submit_rfp
from .bid import create_bid
from .evaluation import create_evaluation, edit_evaluation, select_evaluation
from .settings import get_or_create_settings
from App.academic_years import SEED_ARCHIVE_YEAR, SEED_OPEN_YEARS, SEED_CURRENT_YEAR
from .settings import set_active_academic_year
from App.models import *

# Six demo students → two groups of three (same people every year; IDs prefixed by year)
TEST_GROUP_DEFS = (
    ("AlphaLab", (1, 2, 3)),
    ("BetaLab", (4, 5, 6)),
)
# Extra 2025 vendors so RFPs can receive multiple competing bids
SEED_2025_EXTRA_GROUPS = (
    ("GammaLab", (7, 8, 9)),
    ("DeltaLab", (10, 11, 12)),
)


def generate_sample_pdf(vendor_name, lot_name, price, currency="TTD"):
    """Build a minimal valid single-page PDF for seed/demo bid documents."""
    def pdf_escape(text):
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    lines = [
        "PROCUREMENT BID PROPOSAL",
        "",
        f"Vendor: {vendor_name}",
        f"Lot: {lot_name}",
        f"Quoted Price: {currency} {price:,.2f}",
        "",
        "Scope",
        "Supply, configure, and commission lab workstations",
        "to the published RFP specification, including",
        "delivery, basic setup, and 12-month support.",
        "",
        "Highlights",
        "- Spec-compliant hardware and software stack",
        "- On-site installation and user handover",
        "- Warranty and spare-parts coverage included",
        "",
        "Terms",
        "Valid for 30 days from submission. Payment on",
        "acceptance. Sample seed document for demos only.",
    ]

    content_lines = ["BT", "/F1 14 Tf", "50 740 Td", "16 TL"]
    for i, line in enumerate(lines):
        escaped = pdf_escape(line)
        if i == 0:
            content_lines.append("/F1 18 Tf")
            content_lines.append(f"({escaped}) Tj")
            content_lines.append("/F1 12 Tf")
            content_lines.append("T*")
        else:
            content_lines.append(f"({escaped}) '")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
        b"endobj\n"
    )
    objects.append(
        f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("ascii")
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


# Size × type grid from the course assignment sheet.
# Budget blanks filled with a mix of tight (T) and gracious (G) envelopes.
SIZES = ("Small", "Medium", "Large", "Extra Large")
TYPE_KEYS = ("gis", "design", "gov", "mobile", "cyber")

# Machines by size × type
MACHINES = {
    "Small":       {"gis": 20, "design": 5,  "gov": 30,  "mobile": 4,  "cyber": 10},
    "Medium":      {"gis": 30, "design": 10, "gov": 60,  "mobile": 15, "cyber": 15},
    "Large":       {"gis": 35, "design": 15, "gov": 90,  "mobile": 20, "cyber": 20},
    "Extra Large": {"gis": 70, "design": 20, "gov": 120, "mobile": 40, "cyber": 40},
}

# Known sheet values kept; empties filled (T=tight, G=gracious)
BUDGETS = {
    "Small": {
        "gis": 115000.00,   # T ~$5.8k/machine
        "design": 72000.00, # G ~$14.4k/machine
        "gov": 375000.00,   # sheet
        "mobile": 58000.00, # G ~$14.5k/machine
        "cyber": 62000.00,  # T ~$6.2k/machine
    },
    "Medium": {
        "gis": 240000.00,   # sheet
        "design": 75000.00, # T ~$7.5k/machine
        "gov": 720000.00,   # G ~$12k/machine
        "mobile": 90000.00, # T ~$6k/machine
        "cyber": 109500.00, # sheet
    },
    "Large": {
        "gis": 266000.00,    # sheet
        "design": 180000.00, # sheet
        "gov": 495000.00,    # T ~$5.5k/machine
        "mobile": 250000.00, # G ~$12.5k/machine
        "cyber": 144000.00,  # sheet
    },
    "Extra Large": {
        "gis": 490000.00,     # sheet
        "design": 240000.00,  # sheet
        "gov": 1350000.00,    # G ~$11.3k/machine
        "mobile": 240000.00,  # T ~$6k/machine
        "cyber": 308000.00,   # sheet
    },
}

# Group labels from sheet (G1–G10) by size × type
GROUP_ASSIGN = {
    "Small":       {"gis": "G1", "design": "G2", "gov": "G5", "mobile": "G3", "cyber": "G10"},
    "Medium":      {"gis": "G8", "design": "G1", "gov": "G4", "mobile": "G4", "cyber": "G8"},
    "Large":       {"gis": "G7", "design": "G6", "gov": "G3", "mobile": "G9", "cyber": "G6"},
    "Extra Large": {"gis": "G2", "design": "G5", "gov": "G9", "mobile": "G10", "cyber": "G7"},
}

# Seed RFP drafts: ranges only (no brands/models) — matches student form guidance
TYPE_SPECS = {
    "gis": dict(
        deviceType="Workstation",
        cpu="8–16 cores @ 2.5–3.5 GHz",
        ram="DDR5 · 32–64 GB",
        resolution="27–32\" · 3840×2160 or higher",
        os="Windows / Linux",
        drive="SSD · 1–2 TB (optional secondary HDD)",
        gpu="Dedicated · 8–16 GB VRAM",
        peripherals="Keyboard, mouse, drawing tablet",
        features="Wi‑Fi 6, Bluetooth, dual display support",
        io="USB‑C, USB‑A 3.x, HDMI, DisplayPort, Ethernet",
    ),
    "design": dict(
        deviceType="Workstation",
        cpu="8–16 cores @ 2.8–3.8 GHz",
        ram="DDR5 · 32–64 GB",
        resolution="27–32\" · 3840×2160 color-accurate panel",
        os="Windows / macOS / Linux",
        drive="SSD · 1–2 TB + optional secondary storage",
        gpu="Dedicated · 12–24 GB VRAM",
        peripherals="Keyboard, precision mouse, drawing tablet",
        features="Wi‑Fi 6, Bluetooth, SD card reader",
        io="USB‑C / Thunderbolt-class, USB‑A, HDMI, DisplayPort",
    ),
    "gov": dict(
        deviceType="Workstation",
        cpu="4–8 cores @ 2.0–3.2 GHz",
        ram="DDR4/DDR5 · 8–16 GB",
        resolution="23–27\" · 1920×1080 or higher",
        os="Windows",
        drive="SSD · 256–512 GB",
        gpu="Integrated",
        peripherals="Keyboard, mouse",
        features="Wi‑Fi 5/6, Bluetooth, webcam",
        io="USB‑A, USB‑C, HDMI, Ethernet, headphone jack",
    ),
    "mobile": dict(
        deviceType="Laptop",
        cpu="6–8 cores @ 2.2–3.4 GHz",
        ram="DDR4/DDR5 · 16–32 GB",
        resolution="14–16\" · 1920×1080 or higher",
        os="Windows / Linux",
        drive="SSD · 512 GB–1 TB",
        gpu="Integrated or dedicated · 4–8 GB VRAM",
        peripherals="External mouse, USB hub (optional)",
        features="Wi‑Fi 6, Bluetooth, webcam, fingerprint reader",
        io="USB‑C, USB‑A, HDMI, SD reader, headphone jack",
    ),
    "cyber": dict(
        deviceType="Workstation",
        cpu="4–8 cores @ 2.0–3.2 GHz",
        ram="DDR4/DDR5 · 8–16 GB",
        resolution="23–27\" · 1920×1080",
        os="Windows / Linux / Chromium OS",
        drive="SSD · 256–512 GB",
        gpu="Integrated",
        peripherals="Keyboard, mouse, headset",
        features="Wi‑Fi 5/6, Bluetooth, webcam, speakers",
        io="USB‑A, USB‑C, HDMI, headphone jack",
    ),
}


def _seed_lots(types, academic_year):
    """Create the 20 size×type lots for a year. Returns {(size, type_key): lot_id}."""
    lot_ids = {}
    for size in SIZES:
        for key in TYPE_KEYS:
            lab = types[key]
            lot = create_lot(
                lab.name,
                size,
                BUDGETS[size][key],
                labTypeId=lab.id,
                academic_year=academic_year,
                numMachines=MACHINES[size][key],
            )
            lot_ids[(size, key)] = lot.id
    return lot_ids


def initialize():
    db.drop_all()
    db.create_all()

    get_or_create_settings()
    set_active_academic_year(SEED_CURRENT_YEAR)
    archive_year = SEED_ARCHIVE_YEAR
    create_admin("admin", "plattech2026")

    types = {
        "gis": create_lab_type(
            "GIS Lab",
            "The lab should be outfitted with machines that can run enterprise-level Geographic Information Systems Software.",
        ),
        "gov": create_lab_type(
            "Government Office",
            "Windows-based system integrated with windows enterprise software such as Office, SharePoint, and Active Directory.",
        ),
        "cyber": create_lab_type(
            "Cyber Cafe",
            "Web browsing and gaming.",
        ),
        "mobile": create_lab_type(
            "Mobile Lab",
            "Mobile devices for web browsing, creating spreadsheets, presentations, and word processing.",
        ),
        "design": create_lab_type(
            "Design Studio",
            "Lab should be outfitted for content creation and design; graphic design, photo-editing, 4K video editing & animation.",
        ),
    }

    # Year-specific student rosters (same people, IDs prefixed by year)
    student_roster = [
        ("Aiden Joseph", 1, "aidenpass", "aiden"),
        ("Kareem Ali", 2, "kareempass", "kareem"),
        ("Joshua Peters", 3, "joshuapass", "joshua"),
        ("Daniel Roberts", 4, "danielpass", "daniel"),
        ("Samantha Clarke", 5, "samanthapass", "samantha"),
        ("Aaliyah Mohammed", 6, "aaliyahpass", "aaliyah"),
        ("Leah Charles", 7, "leahpass", "leah"),
        ("Naomi Thomas", 8, "naomipass", "naomi"),
        ("Ryan Williams", 9, "ryanpass", "ryan"),
        ("Darius Edwards", 10, "dariuspass", "darius"),
        ("Marcus Browne", 11, "marcuspass", "marcus"),
        ("Andre Lewis", 12, "andrepass", "andre"),
        ("Keisha Grant", 13, "keishapass", "keisha"),
        ("Tricia Ramnarine", 14, "triciapass", "tricia"),
        ("Anil Singh", 15, "anilpass", "anil"),
        ("Ravi Persad", 16, "ravipass", "ravi"),
        ("Janelle Baptiste", 17, "janellepass", "janelle"),
        ("Shawn Mitchell", 18, "shawnpass", "shawn"),
        ("Kevin Hernandez", 19, "kevinpass", "kevin"),
        ("Ashley Gomez", 20, "ashleypass", "ashley"),
        ("Joey Patterson", 21, "joeypass", "joey"),
        ("Michelle James", 22, "michellepass", "michelle"),
        ("Tyrell George", 23, "tyrellpass", "tyrell"),
        ("Nadia Richards", 24, "nadiapass", "nadia"),
        ("Jerome Phillips", 25, "jeromepass", "jerome"),
        ("Vanessa Edwards", 26, "vanessapass", "vanessa"),
        ("Christopher Lewis", 27, "christopherpass", "christopher"),
        ("Melissa Clarke", 28, "melissapass", "melissa"),
        ("Devon Peters", 29, "devonpass", "devon"),
        ("Sherisse Joseph", 30, "sherissepass", "sherisse"),
        ("Darren Mitchell", 31, "darrenpass", "darren"),
    ]

    def _seed_students(year, roster=None):
        roster = roster if roster is not None else student_roster
        for name, seq, password, email_local in roster:
            create_student(
                name,
                f"{year}{seq:04d}",
                password,
                email=f"{email_local}{year}@lab.local",
                academic_year=year,
                account_claimed=True,
            )

    def _seed_test_groups(year, group_defs=None):
        """
        Ensure roster students for group_defs exist, then approved groups of three.
        Returns {group_name: Group}.
        """
        group_defs = group_defs or TEST_GROUP_DEFS
        needed_seqs = {seq for _name, seqs in group_defs for seq in seqs}
        test_roster = [row for row in student_roster if row[1] in needed_seqs]
        for name, seq, password, email_local in test_roster:
            username = f"{year}{seq:04d}"
            existing = db.session.scalars(
                db.select(Student).filter_by(username=username)
            ).first()
            if existing:
                if existing.academic_year != year:
                    existing.academic_year = year
                existing.account_claimed = True
                continue
            create_student(
                name,
                username,
                password,
                email=f"{email_local}{year}@lab.local",
                academic_year=year,
                account_claimed=True,
            )

        groups = {}
        for group_name, seqs in group_defs:
            group = None
            for g in db.session.scalars(
                db.select(Group).filter_by(academic_year=year)
            ).all():
                if group_name in (g.groupName or ""):
                    group = g
                    break
            if not group:
                group = create_group(group_name, academic_year=year)

            for seq in seqs:
                username = f"{year}{seq:04d}"
                student = db.session.scalars(
                    db.select(Student).where(Student.username == username)
                ).first()
                if not student:
                    raise RuntimeError(
                        f"Seed student {username} missing for {year} before grouping"
                    )
                already = db.session.scalars(
                    db.select(StudentGroup).filter_by(
                        studentID=student.id, groupID=group.id
                    )
                ).first()
                if not already:
                    other = db.session.scalars(
                        db.select(StudentGroup)
                        .join(Group, Group.id == StudentGroup.groupID)
                        .filter(
                            StudentGroup.studentID == student.id,
                            Group.academic_year == year,
                            Group.id != group.id,
                        )
                    ).all()
                    for m in other:
                        db.session.delete(m)
                    add_studentGroup(student.id, group.id)

            has_lots = db.session.scalars(
                db.select(LotGroup).filter_by(groupID=group.id)
            ).first()
            if has_lots:
                if group.status != "approved":
                    approve_group(group.id)
            else:
                ok, err = assign_exclusive_lots(group.id, count=2)
                if not ok:
                    approve_group(group.id)
                    print(f"warn: could not auto-assign lots for {group_name} {year}: {err}")
            groups[group_name] = group
        return groups

    def _lot_type_key(lot):
        for key, lab in types.items():
            if lot.labTypeId == lab.id or lot.labType == lab.name:
                return key
        return "gis"

    def _group_lot_ids(group):
        return db.session.scalars(
            db.select(LotGroup.lotID)
            .filter_by(groupID=group.id)
            .order_by(LotGroup.lotID)
        ).all()

    def _seed_2025_rfps_and_bids(groups):
        """
        2025 demo market: RFPs on Alpha/Beta/Gamma/Delta lots, competing bids
        (one per vendor per lot), and evaluations with a selected winner per lot.
        """
        alpha = groups["AlphaLab"]
        beta = groups["BetaLab"]
        gamma = groups["GammaLab"]
        delta = groups["DeltaLab"]

        def lots_of(g):
            ids = _group_lot_ids(g)
            if len(ids) < 2:
                raise RuntimeError(f"{g.groupName} needs 2 lots for 2025 RFP seed")
            return ids[0], ids[1]

        a0, a1 = lots_of(alpha)
        b0, b1 = lots_of(beta)
        g0, g1 = lots_of(gamma)
        d0, d1 = lots_of(delta)

        lot_map = {lid: get_lot(lid) for lid in (a0, a1, b0, b1, g0, g1, d0, d1)}

        # Published RFPs (clients)
        for owner, lot_id in (
            (alpha, a0), (alpha, a1),
            (beta, b0), (beta, b1),
            (gamma, g0),
            (delta, d0),
        ):
            lot = lot_map[lot_id]
            create_rfp(
                owner.id, lot_id, status="submitted",
                **TYPE_SPECS[_lot_type_key(lot)],
            )
        # One draft RFP left on Gamma's second lot
        create_rfp(
            gamma.id, g1, status="draft",
            **TYPE_SPECS[_lot_type_key(lot_map[g1])],
        )

        cover = (
            "<p>We are pleased to submit this proposal for your consideration. "
            "Our team can deliver to the published specification on schedule "
            "with installation and 12-month support included.</p>"
        )

        def bid(lot_id, vendor, client, price, slug):
            lot = lot_map[lot_id]
            return create_bid(
                lot_id,
                vendor.id,
                client.id,
                generate_sample_pdf(vendor.groupName.split(" ", 1)[-1], lot.labType, price),
                f"{slug}.pdf",
                float(price),
                message=cover,
            )

        # Competing bids on Alpha RFPs
        bid_a0_b = bid(a0, beta, alpha, 98000, "2025_beta_on_alpha_1")
        bid_a0_g = bid(a0, gamma, alpha, 101500, "2025_gamma_on_alpha_1")
        bid_a0_d = bid(a0, delta, alpha, 96500, "2025_delta_on_alpha_1")
        bid_a1_b = bid(a1, beta, alpha, 72000, "2025_beta_on_alpha_2")
        bid_a1_g = bid(a1, gamma, alpha, 74500, "2025_gamma_on_alpha_2")

        # Competing bids on Beta RFPs
        bid_b0_a = bid(b0, alpha, beta, 88000, "2025_alpha_on_beta_1")
        bid_b0_g = bid(b0, gamma, beta, 91000, "2025_gamma_on_beta_1")
        bid_b0_d = bid(b0, delta, beta, 89500, "2025_delta_on_beta_1")
        bid_b1_a = bid(b1, alpha, beta, 155000, "2025_alpha_on_beta_2")
        bid_b1_d = bid(b1, delta, beta, 149000, "2025_delta_on_beta_2")

        # Bids on Gamma / Delta RFPs
        bid_g0_a = bid(g0, alpha, gamma, 112000, "2025_alpha_on_gamma_1")
        bid_g0_b = bid(g0, beta, gamma, 108500, "2025_beta_on_gamma_1")
        bid_d0_a = bid(d0, alpha, delta, 64000, "2025_alpha_on_delta_1")
        bid_d0_b = bid(d0, beta, delta, 67500, "2025_beta_on_delta_1")
        bid_d0_g = bid(d0, gamma, delta, 65800, "2025_gamma_on_delta_1")

        full_specs = "deviceType,cpu,ram,resolution,os,drive,gpu,features"
        mid_specs = "deviceType,cpu,ram,resolution,os,drive,gpu"
        lean_specs = "deviceType,cpu,ram,os,drive"

        def evaluate(client, vendor, bid_obj, lot_id, scores, specs_selected):
            sm, pr, pf, bu = scores
            ev = create_evaluation(
                client.id, vendor.id, bid_obj.id, lot_id, sm, pr, pf, bu
            )
            edit_evaluation(ev.id, sm, pr, pf, bu, specsSelected=specs_selected)
            return ev

        # Alpha evaluates all bids on both lots
        ea0_b = evaluate(alpha, beta, bid_a0_b, a0, (4, 3, 4, 3), mid_specs)
        ea0_g = evaluate(alpha, gamma, bid_a0_g, a0, (5, 4, 4, 4), full_specs)
        ea0_d = evaluate(alpha, delta, bid_a0_d, a0, (3, 3, 3, 2), lean_specs)
        select_evaluation(ea0_g.id)

        ea1_b = evaluate(alpha, beta, bid_a1_b, a1, (4, 4, 3, 4), mid_specs)
        ea1_g = evaluate(alpha, gamma, bid_a1_g, a1, (3, 3, 4, 3), mid_specs)
        select_evaluation(ea1_b.id)

        # Beta evaluates all bids on both lots
        eb0_a = evaluate(beta, alpha, bid_b0_a, b0, (4, 4, 5, 4), full_specs)
        eb0_g = evaluate(beta, gamma, bid_b0_g, b0, (3, 4, 3, 3), mid_specs)
        eb0_d = evaluate(beta, delta, bid_b0_d, b0, (4, 3, 4, 4), mid_specs)
        select_evaluation(eb0_a.id)

        eb1_a = evaluate(beta, alpha, bid_b1_a, b1, (5, 4, 4, 3), full_specs)
        eb1_d = evaluate(beta, delta, bid_b1_d, b1, (4, 5, 4, 5), full_specs)
        select_evaluation(eb1_d.id)

        # Gamma evaluates bids on g0 (draft lot g1 has no bids)
        eg0_a = evaluate(gamma, alpha, bid_g0_a, g0, (4, 4, 3, 3), mid_specs)
        eg0_b = evaluate(gamma, beta, bid_g0_b, g0, (5, 4, 5, 4), full_specs)
        select_evaluation(eg0_b.id)

        # Delta evaluates all three bids on d0
        ed0_a = evaluate(delta, alpha, bid_d0_a, d0, (3, 4, 3, 4), lean_specs)
        ed0_b = evaluate(delta, beta, bid_d0_b, d0, (4, 3, 4, 3), mid_specs)
        ed0_g = evaluate(delta, gamma, bid_d0_g, d0, (5, 5, 4, 4), full_specs)
        select_evaluation(ed0_g.id)

    _seed_students(archive_year)
    for open_year in SEED_OPEN_YEARS:
        _seed_students(open_year)

    # ─── 2024 archive: full procurement run ───────────────────────────────────
    lot_ids = _seed_lots(types, archive_year)

    group_defs = [
        ("G1", "NexoraTech", [1, 2, 3]),
        ("G2", "QuantumSoft", [4, 5, 6]),
        ("G3", "ByteForge", [7, 8, 9]),
        ("G4", "CyberNova", [10, 11, 12]),
        ("G5", "InnovateTech", [13, 14, 15]),
        ("G6", "CloudSystems", [16, 17, 18]),
        ("G7", "PixelForge", [19, 20, 21]),
        ("G8", "DataNest", [22, 23, 24]),
        ("G9", "OrbitLabs", [25, 26, 27]),
        ("G10", "NovaBridge", [28, 29, 30]),
    ]

    groups_by_label = {}
    for label, group_name, seqs in group_defs:
        group = create_group(group_name, academic_year=archive_year)
        for seq in seqs:
            username = f"{archive_year}{seq:04d}"
            student = db.session.scalars(
                db.select(Student).where(Student.username == username)
            ).first()
            add_studentGroup(student.id, group.id)
        groups_by_label[label] = group

    lots_by_group = {label: [] for label in groups_by_label}
    for size in SIZES:
        for key in TYPE_KEYS:
            label = GROUP_ASSIGN[size][key]
            lots_by_group[label].append(lot_ids[(size, key)])

    for label, group in groups_by_label.items():
        approve_group(group.id)
        for lot_id in lots_by_group[label]:
            add_lotGroup(lot_id, group.id)

    g1, g2, g3, g4 = (
        groups_by_label["G1"],
        groups_by_label["G2"],
        groups_by_label["G3"],
        groups_by_label["G4"],
    )
    g1_lots = lots_by_group["G1"]  # Small GIS, Medium Design
    g2_lots = lots_by_group["G2"]  # Small Design, XL GIS
    lot_type_key = {lid: key for (size, key), lid in lot_ids.items()}

    create_rfp(g1.id, g1_lots[0], status="submitted", **TYPE_SPECS[lot_type_key[g1_lots[0]]])
    create_rfp(g1.id, g1_lots[1], status="submitted", **TYPE_SPECS[lot_type_key[g1_lots[1]]])
    create_rfp(g2.id, g2_lots[0], status="submitted", **TYPE_SPECS[lot_type_key[g2_lots[0]]])
    create_rfp(g2.id, g2_lots[1], status="draft", **TYPE_SPECS[lot_type_key[g2_lots[1]]])
    submit_rfp(g3.id, lots_by_group["G3"][0], **TYPE_SPECS[lot_type_key[lots_by_group["G3"][0]]])

    bid1 = create_bid(
        g1_lots[0], g2.id, g1.id,
        generate_sample_pdf("QuantumSoft", "GIS Lab", 110000),
        "quantumsoft_gis_bid.pdf", 110000.00,
    )
    bid2 = create_bid(
        g1_lots[0], g3.id, g1.id,
        generate_sample_pdf("ByteForge", "GIS Lab", 118000),
        "byteforge_gis_bid.pdf", 118000.00,
    )
    bid7 = create_bid(
        g1_lots[0], g4.id, g1.id,
        generate_sample_pdf("CyberNova", "GIS Lab", 112500),
        "cybernova_gis_bid.pdf", 112500.00,
    )
    bid3 = create_bid(
        g1_lots[1], g2.id, g1.id,
        generate_sample_pdf("QuantumSoft", "Design Studio", 70000),
        "quantumsoft_design_bid.pdf", 70000.00,
    )
    bid4 = create_bid(
        g2_lots[0], g1.id, g2.id,
        generate_sample_pdf("NexoraTech", "Design Studio", 68000),
        "nexoratech_design_bid.pdf", 68000.00,
    )
    bid5 = create_bid(
        g2_lots[0], g4.id, g2.id,
        generate_sample_pdf("CyberNova", "Design Studio", 71000),
        "cybernova_design_bid.pdf", 71000.00,
    )
    bid8 = create_bid(
        g2_lots[0], g3.id, g2.id,
        generate_sample_pdf("ByteForge", "Design Studio", 69500),
        "byteforge_design_bid.pdf", 69500.00,
    )
    bid6 = create_bid(
        g2_lots[1], g1.id, g2.id,
        generate_sample_pdf("NexoraTech", "GIS Lab XL", 475000),
        "nexoratech_gis_xl_bid.pdf", 475000.00,
    )

    gis_specs = "deviceType,cpu,ram,resolution,os,drive,gpu"
    design_specs = "deviceType,cpu,ram,os,drive,gpu,peripherals"

    eval1 = create_evaluation(g1.id, g2.id, bid1.id, g1_lots[0], 4, 3, 4, 3)
    edit_evaluation(eval1.id, 4, 3, 4, 3, specsSelected=gis_specs)
    eval2 = create_evaluation(g1.id, g3.id, bid2.id, g1_lots[0], 5, 4, 5, 4)
    edit_evaluation(eval2.id, 5, 4, 5, 4, specsSelected=gis_specs + ",features,io")
    eval7 = create_evaluation(g1.id, g4.id, bid7.id, g1_lots[0], 4, 4, 3, 4)
    edit_evaluation(eval7.id, 4, 4, 3, 4, specsSelected="deviceType,cpu,ram,os,drive")

    eval3 = create_evaluation(g1.id, g2.id, bid3.id, g1_lots[1], 4, 3, 3, 4)
    edit_evaluation(eval3.id, 4, 3, 3, 4, specsSelected=design_specs)

    eval4 = create_evaluation(g2.id, g1.id, bid4.id, g2_lots[0], 5, 4, 4, 5)
    edit_evaluation(eval4.id, 5, 4, 4, 5, specsSelected=design_specs + ",features")
    eval5 = create_evaluation(g2.id, g4.id, bid5.id, g2_lots[0], 3, 3, 3, 2)
    edit_evaluation(eval5.id, 3, 3, 3, 2, specsSelected="deviceType,os,drive")
    eval8 = create_evaluation(g2.id, g3.id, bid8.id, g2_lots[0], 4, 4, 4, 4)
    edit_evaluation(eval8.id, 4, 4, 4, 4, specsSelected=design_specs)

    eval6 = create_evaluation(g2.id, g1.id, bid6.id, g2_lots[1], 5, 5, 5, 5)
    edit_evaluation(eval6.id, 5, 5, 5, 5, specsSelected=gis_specs + ",features,io,peripherals")

    select_evaluation(eval2.id)
    select_evaluation(eval4.id)
    select_evaluation(eval6.id)

    # ─── Open years: lots + test groups; 2025 also gets RFPs / bids / evals ────
    for open_year in SEED_OPEN_YEARS:
        _seed_lots(types, open_year)
        if open_year == 2025:
            groups_2025 = _seed_test_groups(
                open_year, TEST_GROUP_DEFS + SEED_2025_EXTRA_GROUPS
            )
            _seed_2025_rfps_and_bids(groups_2025)
        else:
            _seed_test_groups(open_year)
