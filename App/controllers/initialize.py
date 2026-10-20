from App.controllers.studentGroup import add_studentGroup
from App.database import db
from .lot import create_lot, edit_lotRFP_details
from .labType import create_lab_type
from .student import create_student
from .admin import create_admin
from .group import create_group, approve_group
from .lotGroup import add_lotGroup
from .rfp import create_rfp, submit_rfp
from .bid import create_bid
from .evaluation import create_evaluation, edit_evaluation, select_evaluation
from .settings import get_or_create_settings
from .academic_year import DEFAULT_ACADEMIC_YEAR
from App.models import *


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

TYPE_SPECS = {
    "gis": dict(
        deviceType="GIS Workstation",
        cpu="Intel Core i9-13900K",
        ram="64GB DDR5",
        resolution="27-inch 4K IPS",
        os="Windows 11 Pro",
        drive="2TB NVMe SSD",
        gpu="NVIDIA RTX 4080",
        peripherals="4x USB-A, 2x USB-C, HDMI 2.1, DisplayPort 1.4",
        features="Mechanical Keyboard, Ergonomic Mouse, Drawing Tablet",
        io="Webcam, WiFi 6E, Bluetooth 5.2",
    ),
    "design": dict(
        deviceType="Design Desktop",
        cpu="Intel Core i9-13900K",
        ram="64GB DDR5",
        resolution="Dual 32-inch 4K OLED",
        os="Windows 11 Pro",
        drive="2TB NVMe SSD + 2TB HDD",
        gpu="NVIDIA RTX 4090",
        peripherals="4x USB-A, 4x USB-C, 2x Thunderbolt 4, SD Card Reader",
        features="Wireless Ergonomic Keyboard, Precision Mouse, Wacom Tablet",
        io="Pantone-Calibrated Display, WiFi 6E, Bluetooth 5.2",
    ),
    "gov": dict(
        deviceType="Office Desktop",
        cpu="Intel Core i5-13400",
        ram="16GB DDR4",
        resolution="24-inch FHD",
        os="Windows 11 Pro",
        drive="512GB NVMe SSD",
        gpu="Intel UHD Graphics 730",
        peripherals="4x USB-A, 1x USB-C, HDMI 1.4",
        features="Standard Keyboard, Optical Mouse",
        io="Webcam, WiFi 5, Bluetooth 4.2",
    ),
    "mobile": dict(
        deviceType="Laptop",
        cpu="AMD Ryzen 7 7745HX",
        ram="32GB DDR5",
        resolution="15.6-inch FHD 144Hz",
        os="Windows 11 Pro / Ubuntu 22.04 Dual Boot",
        drive="1TB NVMe SSD",
        gpu="NVIDIA RTX 3060",
        peripherals="3x USB-A, 2x USB-C, HDMI 2.0, SD Card Reader",
        features="Wireless Keyboard, Wireless Mouse, USB Hub",
        io="Fingerprint Reader, WiFi 6, Bluetooth 5.0",
    ),
    "cyber": dict(
        deviceType="Public Access PC",
        cpu="Intel Core i5-13400",
        ram="16GB DDR4",
        resolution="24-inch FHD",
        os="Windows 11 Home",
        drive="512GB NVMe SSD",
        gpu="Intel UHD Graphics 730",
        peripherals="4x USB-A, 1x USB-C, HDMI 1.4",
        features="Standard Keyboard, Optical Mouse",
        io="Webcam, WiFi 5, Bluetooth 4.2",
    ),
}


def initialize():
    db.drop_all()
    db.create_all()

    get_or_create_settings()
    seed_year = DEFAULT_ACADEMIC_YEAR
    create_admin("bob", "bobpass")

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

    # 20 lots = every size × type; track lot id by (size, type_key)
    lot_ids = {}
    for size in SIZES:
        for key in TYPE_KEYS:
            lab = types[key]
            lot = create_lot(
                lab.name,
                size,
                BUDGETS[size][key],
                labTypeId=lab.id,
                academic_year=seed_year,
                numMachines=MACHINES[size][key],
            )
            lot_ids[(size, key)] = lot.id
            edit_lotRFP_details(lot.id, **TYPE_SPECS[key])

    students = [
        ("Aiden Joseph", "20240001", "aidenpass", "aiden@lab.local"),
        ("Kareem Ali", "20240002", "kareempass", "kareem@lab.local"),
        ("Joshua Peters", "20240003", "joshuapass", "joshua@lab.local"),
        ("Daniel Roberts", "20240004", "danielpass", "daniel@lab.local"),
        ("Samantha Clarke", "20240005", "samanthapass", "samantha@lab.local"),
        ("Aaliyah Mohammed", "20240006", "aaliyahpass", "aaliyah@lab.local"),
        ("Leah Charles", "20240007", "leahpass", "leah@lab.local"),
        ("Naomi Thomas", "20240008", "naomipass", "naomi@lab.local"),
        ("Ryan Williams", "20240009", "ryanpass", "ryan@lab.local"),
        ("Darius Edwards", "20240010", "dariuspass", "darius@lab.local"),
        ("Marcus Browne", "20240011", "marcuspass", "marcus@lab.local"),
        ("Andre Lewis", "20240012", "andrepass", "andre@lab.local"),
        ("Keisha Grant", "20240013", "keishapass", "keisha@lab.local"),
        ("Tricia Ramnarine", "20240014", "triciapass", "tricia@lab.local"),
        ("Anil Singh", "20240015", "anilpass", "anil@lab.local"),
        ("Ravi Persad", "20240016", "ravipass", "ravi@lab.local"),
        ("Janelle Baptiste", "20240017", "janellepass", "janelle@lab.local"),
        ("Shawn Mitchell", "20240018", "shawnpass", "shawn@lab.local"),
        ("Kevin Hernandez", "20240019", "kevinpass", "kevin@lab.local"),
        ("Ashley Gomez", "20240020", "ashleypass", "ashley@lab.local"),
        ("Joey Patterson", "20240021", "joeypass", "joey@lab.local"),
        ("Michelle James", "20240022", "michellepass", "michelle@lab.local"),
        ("Tyrell George", "20240023", "tyrellpass", "tyrell@lab.local"),
        ("Nadia Richards", "20240024", "nadiapass", "nadia@lab.local"),
        ("Jerome Phillips", "20240025", "jeromepass", "jerome@lab.local"),
        ("Vanessa Edwards", "20240026", "vanessapass", "vanessa@lab.local"),
        ("Christopher Lewis", "20240027", "christopherpass", "christopher@lab.local"),
        ("Melissa Clarke", "20240028", "melissapass", "melissa@lab.local"),
        ("Devon Peters", "20240029", "devonpass", "devon@lab.local"),
        ("Sherisse Joseph", "20240030", "sherissepass", "sherisse@lab.local"),
        ("Darren Mitchell", "20240031", "darrenpass", "darren@lab.local"),
    ]
    for name, username, password, email in students:
        create_student(name, username, password, email=email)

    group_defs = [
        ("G1", "NexoraTech", ["20240001", "20240002", "20240003"]),
        ("G2", "QuantumSoft", ["20240004", "20240005", "20240006"]),
        ("G3", "ByteForge", ["20240007", "20240008", "20240009"]),
        ("G4", "CyberNova", ["20240010", "20240011", "20240012"]),
        ("G5", "InnovateTech", ["20240013", "20240014", "20240015"]),
        ("G6", "CloudSystems", ["20240016", "20240017", "20240018"]),
        ("G7", "PixelForge", ["20240019", "20240020", "20240021"]),
        ("G8", "DataNest", ["20240022", "20240023", "20240024"]),
        ("G9", "OrbitLabs", ["20240025", "20240026", "20240027"]),
        ("G10", "NovaBridge", ["20240028", "20240029", "20240030"]),
    ]

    groups_by_label = {}
    for label, group_name, usernames in group_defs:
        group = create_group(group_name, academic_year=seed_year)
        for username in usernames:
            student = db.session.scalars(
                db.select(Student).where(Student.username == username)
            ).first()
            add_studentGroup(student.id, group.id)
        groups_by_label[label] = group

    # Two exclusive lots per group from the assignment sheet
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

    create_rfp(g1.id, g1_lots[0], status="submitted")
    create_rfp(g1.id, g1_lots[1], status="submitted")
    create_rfp(g2.id, g2_lots[0], status="submitted")
    create_rfp(g2.id, g2_lots[1], status="draft")
    submit_rfp(g3.id, lots_by_group["G3"][0])

    # Three vendor bids on G1 Small GIS — used to test compare-modal cycling.
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
    # Three vendor bids on G2 Small Design.
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
