"""Assemble / parse structured RFP form controls into stored text fields."""
import re


DEVICE_TYPES = ("Laptop", "Tablet", "Phone", "Workstation")

OS_OPTIONS = ("Windows", "macOS", "Linux", "Android", "iOS", "ChromeOS")

RESOLUTION_OPTIONS = (
    "1280×720",
    "1920×1080",
    "2560×1440",
    "3840×2160",
)

# Ordered low → high for graphics output / support range
GPU_RESOLUTION_OPTIONS = RESOLUTION_OPTIONS


def _resolution_rank(label):
    try:
        return GPU_RESOLUTION_OPTIONS.index(label)
    except ValueError:
        return -1

RAM_FORM_FACTORS = ("SODIMM", "DIMM", "LPDDR", "Unified memory")

DRIVE_INTERFACES = ("SATA", "PCIe Gen3", "PCIe Gen4", "PCIe Gen5", "UFS")

PERIPHERAL_OPTIONS = (
    "Mouse",
    "Keyboard",
    "Touchpad",
    "Headset",
    "Speakers",
    "Webcam",
    "Gamepad",
    "Drawing tablet",
    "USB hub",
    "Adapters",
)

FEATURE_OPTIONS = (
    "Touch screen",
    "Wi‑Fi 5",
    "Wi‑Fi 6",
    "Wi‑Fi 6E",
    "Bluetooth",
    "Integrated speakers",
    "Integrated webcam",
    "Fingerprint reader",
    "LTE / 5G",
    "Backlit keyboard",
)

IO_OPTIONS = (
    "USB‑A 3.x",
    "USB‑C",
    "USB4",
    "Thunderbolt",
    "OCuLink",
    "HDMI",
    "DisplayPort",
    "Ethernet",
    "SD card reader",
    "Audio jack",
    "Optical drive",
)


def _join_chips(values):
    cleaned = [v.strip() for v in values if v and str(v).strip()]
    # preserve order, drop dupes
    seen = set()
    out = []
    for v in cleaned:
        key = v.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return ", ".join(out)


def _split_chips(text):
    if not text:
        return []
    parts = re.split(r"\s*[,;/]\s*", text.strip())
    return [p for p in parts if p]


def _num(val, default):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def assemble_rfp_specs(form):
    """Build RFP text fields from structured POST form data."""
    device = (form.get("deviceType") or "").strip()
    if device not in DEVICE_TYPES:
        device = device or ""

    screen_min = int(_num(form.get("screen_min"), 13))
    screen_max = int(_num(form.get("screen_max"), 16))
    if screen_min > screen_max:
        screen_min, screen_max = screen_max, screen_min
    resolutions = form.getlist("resolution_opt")
    res_txt = " / ".join(resolutions) if resolutions else ""
    if screen_min == screen_max:
        size_txt = f'{screen_min}"'
    else:
        size_txt = f'{screen_min}–{screen_max}"'
    resolution = f"{size_txt} · {res_txt}" if res_txt else size_txt

    os_vals = form.getlist("os_opt")
    os_txt = " / ".join(os_vals)

    cores_min = int(_num(form.get("cores_min"), 4))
    cores_max = int(_num(form.get("cores_max"), 8))
    if cores_min > cores_max:
        cores_min, cores_max = cores_max, cores_min
    ghz_min = round(_num(form.get("ghz_min"), 2.0), 1)
    ghz_max = round(_num(form.get("ghz_max"), 3.2), 1)
    if ghz_min > ghz_max:
        ghz_min, ghz_max = ghz_max, ghz_min
    if cores_min == cores_max:
        core_txt = f"{cores_min} cores"
    else:
        core_txt = f"{cores_min}–{cores_max} cores"
    cpu = f"{core_txt} @ {ghz_min}–{ghz_max} GHz"

    ram_forms = form.getlist("ram_form")
    ram_min = int(_num(form.get("ram_min"), 8))
    ram_max = int(_num(form.get("ram_max"), 16))
    if ram_min > ram_max:
        ram_min, ram_max = ram_max, ram_min
    ram_speed_min = int(_num(form.get("ram_speed_min"), 0))
    ram_speed_max = int(_num(form.get("ram_speed_max"), 0))
    if ram_speed_min and ram_speed_max and ram_speed_min > ram_speed_max:
        ram_speed_min, ram_speed_max = ram_speed_max, ram_speed_min

    type_txt = "/".join(ram_forms) if ram_forms else "RAM"
    if ram_min == ram_max:
        cap_txt = f"{ram_min} GB"
    else:
        cap_txt = f"{ram_min}–{ram_max} GB"
    ram_parts = [type_txt, cap_txt]
    if ram_speed_min and ram_speed_max:
        if ram_speed_min == ram_speed_max:
            ram_parts.append(f"{ram_speed_min} MT/s")
        else:
            ram_parts.append(f"{ram_speed_min}–{ram_speed_max} MT/s")
    elif ram_speed_min or ram_speed_max:
        ram_parts.append(f"{ram_speed_min or ram_speed_max} MT/s")
    ram = " · ".join(ram_parts)

    drive_ifaces = form.getlist("drive_iface")
    drive_min = int(_num(form.get("drive_min"), 256))
    drive_max = int(_num(form.get("drive_max"), 512))
    if drive_min > drive_max:
        drive_min, drive_max = drive_max, drive_min
    dtype = "/".join(drive_ifaces) if drive_ifaces else "Storage"
    if drive_min >= 1024 or drive_max >= 1024:
        def fmt_gb(n):
            return f"{n / 1024:g} TB" if n >= 1024 and n % 1024 == 0 else f"{n} GB"
        cap = f"{fmt_gb(drive_min)}–{fmt_gb(drive_max)}" if drive_min != drive_max else fmt_gb(drive_min)
    else:
        cap = f"{drive_min}–{drive_max} GB" if drive_min != drive_max else f"{drive_min} GB"
    drive = f"{dtype} · {cap}"
    if form.get("drive_secondary"):
        drive += " + secondary storage"

    vram_min = int(_num(form.get("vram_min"), 4))
    vram_max = int(_num(form.get("vram_max"), 8))
    if vram_min > vram_max:
        vram_min, vram_max = vram_max, vram_min
    if vram_min == vram_max:
        vram_txt = f"{vram_min} GB VRAM"
    else:
        vram_txt = f"{vram_min}–{vram_max} GB VRAM"

    gpu_res_min = (form.get("gpu_res_min") or "").strip()
    gpu_res_max = (form.get("gpu_res_max") or "").strip()
    if gpu_res_min not in GPU_RESOLUTION_OPTIONS:
        gpu_res_min = ""
    if gpu_res_max not in GPU_RESOLUTION_OPTIONS:
        gpu_res_max = ""
    if gpu_res_min and gpu_res_max:
        if _resolution_rank(gpu_res_min) > _resolution_rank(gpu_res_max):
            gpu_res_min, gpu_res_max = gpu_res_max, gpu_res_min
        if gpu_res_min == gpu_res_max:
            res_txt = gpu_res_min
        else:
            res_txt = f"{gpu_res_min}–{gpu_res_max}"
    elif gpu_res_min or gpu_res_max:
        res_txt = gpu_res_min or gpu_res_max
    else:
        res_txt = ""

    gpu_parts = [vram_txt]
    if res_txt:
        gpu_parts.append(res_txt)
    gpu = " · ".join(gpu_parts)

    peripherals = _join_chips(form.getlist("peripheral_opt") + form.getlist("peripheral_custom"))
    features = _join_chips(form.getlist("feature_opt") + form.getlist("feature_custom"))
    io = _join_chips(form.getlist("io_opt") + form.getlist("io_custom"))

    return {
        "deviceType": device,
        "resolution": resolution,
        "os": os_txt,
        "cpu": cpu,
        "ram": ram,
        "drive": drive,
        "gpu": gpu,
        "peripherals": peripherals,
        "features": features,
        "io": io,
    }


def parse_rfp_ui(rfp_form):
    """Best-effort parse of stored text into UI control state (defaults if empty)."""
    ui = {
        "deviceType": rfp_form.get("deviceType") or "",
        "screen_min": 13,
        "screen_max": 16,
        "resolutions": [],
        "os": [],
        "cores_min": 4,
        "cores_max": 8,
        "ghz_min": 2.0,
        "ghz_max": 3.2,
        "ram_forms": [],
        "ram_min": 8,
        "ram_max": 16,
        "ram_speed_min": 3200,
        "ram_speed_max": 5600,
        "drive_ifaces": [],
        "drive_min": 256,
        "drive_max": 512,
        "drive_secondary": False,
        "vram_min": 4,
        "vram_max": 8,
        "gpu_res_min": "",
        "gpu_res_max": "",
        "peripherals": [],
        "features": [],
        "io": [],
        "has_saved": any(rfp_form.get(k) for k in rfp_form),
    }

    if rfp_form.get("deviceType") in DEVICE_TYPES:
        ui["deviceType"] = rfp_form["deviceType"]

    res = rfp_form.get("resolution") or ""
    m = re.search(r'(\d+)\s*[–-]\s*(\d+)\s*"?', res)
    if m:
        ui["screen_min"], ui["screen_max"] = int(m.group(1)), int(m.group(2))
    else:
        m1 = re.search(r'(\d+)\s*"', res)
        if m1:
            ui["screen_min"] = ui["screen_max"] = int(m1.group(1))
    ui["resolutions"] = [r for r in RESOLUTION_OPTIONS if r in res]

    os_text = rfp_form.get("os") or ""
    ui["os"] = [o for o in OS_OPTIONS if o.lower() in os_text.lower()]

    cpu = rfp_form.get("cpu") or ""
    m = re.search(r'(\d+)\s*[–-]\s*(\d+)\s*cores?', cpu, re.I)
    if m:
        ui["cores_min"], ui["cores_max"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r'(\d+)\s*cores?', cpu, re.I)
        if m:
            ui["cores_min"] = ui["cores_max"] = int(m.group(1))
    m = re.search(r'(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*GHz', cpu, re.I)
    if m:
        ui["ghz_min"], ui["ghz_max"] = float(m.group(1)), float(m.group(2))

    ram = rfp_form.get("ram") or ""
    # Match longer form-factor labels first so SODIMM does not also match DIMM
    ui["ram_forms"] = []
    for t in sorted(RAM_FORM_FACTORS, key=len, reverse=True):
        if t == "LPDDR":
            if re.search(r"LPDDR", ram, re.I):
                ui["ram_forms"].append(t)
            continue
        if re.search(rf"\b{re.escape(t)}\b", ram, re.I):
            if t == "DIMM" and "SODIMM" in ui["ram_forms"]:
                continue
            ui["ram_forms"].append(t)
    for legacy in ("LPDDR4", "LPDDR5"):
        if legacy in ram and "LPDDR" not in ui["ram_forms"]:
            ui["ram_forms"].append("LPDDR")
            break
    m = re.search(r'(\d+)\s*[–-]\s*(\d+)\s*GB', ram, re.I)
    if m:
        ui["ram_min"], ui["ram_max"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r'(\d+)\s*GB', ram, re.I)
        if m:
            ui["ram_min"] = ui["ram_max"] = int(m.group(1))
    m = re.search(r'(\d+)\s*[–-]\s*(\d+)\s*MT/s', ram, re.I)
    if m:
        ui["ram_speed_min"], ui["ram_speed_max"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r'(\d+)\s*MT/s', ram, re.I)
        if m:
            ui["ram_speed_min"] = ui["ram_speed_max"] = int(m.group(1))

    drive = rfp_form.get("drive") or ""
    ui["drive_ifaces"] = [t for t in DRIVE_INTERFACES if t in drive]
    ui["drive_secondary"] = "secondary" in drive.lower()
    # normalize TB to GB for slider
    def to_gb(n, unit):
        return int(float(n) * 1024) if unit.upper().startswith("T") else int(float(n))

    m = re.search(
        r'(\d+(?:\.\d+)?)\s*(GB|TB)\s*[–-]\s*(\d+(?:\.\d+)?)\s*(GB|TB)',
        drive,
        re.I,
    )
    if m:
        ui["drive_min"] = to_gb(m.group(1), m.group(2))
        ui["drive_max"] = to_gb(m.group(3), m.group(4))
    else:
        m = re.search(r'(\d+(?:\.\d+)?)\s*(GB|TB)', drive, re.I)
        if m:
            ui["drive_min"] = ui["drive_max"] = to_gb(m.group(1), m.group(2))

    gpu = rfp_form.get("gpu") or ""
    m = re.search(r'(\d+)\s*[–-]\s*(\d+)\s*GB\s*VRAM', gpu, re.I)
    if m:
        ui["vram_min"], ui["vram_max"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r'(\d+)\s*GB\s*VRAM', gpu, re.I)
        if m:
            ui["vram_min"] = ui["vram_max"] = int(m.group(1))
        else:
            m = re.search(r'(\d+)\s*[–-]\s*(\d+)\s*GB', gpu, re.I)
            if m:
                ui["vram_min"], ui["vram_max"] = int(m.group(1)), int(m.group(2))
    found_res = [r for r in GPU_RESOLUTION_OPTIONS if r in gpu]
    if len(found_res) >= 2:
        ranked = sorted(found_res, key=_resolution_rank)
        ui["gpu_res_min"], ui["gpu_res_max"] = ranked[0], ranked[-1]
    elif len(found_res) == 1:
        ui["gpu_res_min"] = ui["gpu_res_max"] = found_res[0]

    ui["peripherals"] = _split_chips(rfp_form.get("peripherals"))
    ui["features"] = _split_chips(rfp_form.get("features"))
    ui["io"] = _split_chips(rfp_form.get("io"))
    return ui
