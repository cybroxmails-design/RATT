"""RATT Non-Execution & Anti-Malware Security Protocol (Phases 1 & 2).

Enforces strict security guardrails across all clipboard slot operations (Text,
Unformatted Links, Images, Diagrams, and File System CF_HDROP routing):
  1. Zero-Execution Guarantee: Files and links are processed strictly as inert
     data structures (never passed to ShellExecute, os.startfile, or shell=True).
  2. Executable & Malware File Quarantine: Blocks high-risk executable, script,
     shortcut, disk-image, and macro-enabled file extensions, double-extension
     spoofing, NTFS Alternate Data Streams (ADS), BiDi RTLO spoofing, and remote
     UNC/SMB paths.
  3. Unformatted Link & Protocol Sanitization: Strips all HTML/RTF formatting,
     blocks executable URI schemes (javascript:, vbscript:, data:, file://,
     ms-msdt:, powershell:, etc.), and removes control/newline characters from
     links to prevent paste-jacking.
  4. Image & SVG Diagram Sanitization: Strips <script>, <foreignObject>, and
     inline event handlers from SVG diagrams and validates binary image headers.
"""
import html
import os
import re
import struct
from typing import List, Optional, Tuple

# High-risk executable, script, shortcut, disk image, and macro extensions
BLOCKED_EXTENSIONS = frozenset({
    # Native binaries & system modules
    ".exe", ".dll", ".sys", ".drv", ".ocx", ".cpl", ".scr", ".com", ".pif",
    # Installers & packages
    ".msi", ".msp", ".mst", ".gadget", ".application", ".appref-ms", ".appx", ".msix",
    # Scripts & command interpreters
    ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
    ".ps1", ".psm1", ".psd1", ".ps1xml", ".psc1", ".pssc",
    ".hta", ".sct", ".wsc", ".shb", ".shs", ".msc", ".inf", ".reg",
    ".jar", ".jnlp", ".py", ".pyc", ".pyw", ".rb", ".pl", ".sh", ".bash",
    # Shortcuts & shell triggers
    ".lnk", ".url", ".scf", ".library-ms", ".search-ms", ".settingcontent-ms",
    ".desklink", ".mapimail", ".mydocs", ".zfsendtotarget",
    # Disk images & compiled help (commonly used for Mark-of-the-Web bypass)
    ".iso", ".img", ".vhd", ".vhdx", ".chm", ".hlp", ".xll", ".wll",
    # Macro-enabled Office execution vectors
    ".docm", ".dotm", ".xlsm", ".xltm", ".xlam", ".pptm", ".potm", ".ppam", ".sldm",
})

# Dangerous URI protocols that can trigger code or handler execution
BLOCKED_URI_SCHEMES = (
    "javascript:",
    "vbscript:",
    "data:",
    "file:",
    "ms-msdt:",
    "ms-officecmd:",
    "ms-word:",
    "ms-excel:",
    "ms-powerpoint:",
    "ms-visio:",
    "ms-access:",
    "ms-cxh:",
    "ms-settings:",
    "ms-appinstaller:",
    "search-ms:",
    "search:",
    "mk:",
    "res:",
    "mhtml:",
    "hta:",
    "shell:",
    "cmd:",
    "powershell:",
    "wscript:",
    "cscript:",
    "jar:",
    "jnlp:",
    "about:",
    "blob:",
)

# Reserved Windows device names
_RESERVED_DEVICES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
})

# Invisible / BiDi spoofing characters (including RTLO \u202e used to fake extensions)
_SPOOF_CHARS_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_DETECT_RE = re.compile(
    r"^\s*(?:https?://|ftp://|mailto:|www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,})\S*\s*$",
    re.IGNORECASE,
)
_ANY_SCHEME_RE = re.compile(r"(?:^|[\s\"'(<])([a-zA-Z][a-zA-Z0-9+.-]{1,24}:)", re.IGNORECASE)


def contains_bidi_spoofing(text: str) -> bool:
    """Return True if text contains Unicode BiDi override characters (e.g. RTLO U+202E)."""
    return bool(re.search(r"[\u202a-\u202e\u2066-\u2069]", text))


def validate_file_list(paths: List[str]) -> Tuple[bool, List[str], str]:
    """Validate a list of file paths for safe, inert CF_HDROP routing.

    Returns (allowed: bool, canonical_paths: List[str], error_message: str).
    Blocks executables, scripts, shortcuts, macros, double-extension tricks,
    NTFS Alternate Data Streams, UNC network paths, and BiDi spoofing.
    """
    if not paths:
        return False, [], "No files selected."

    safe_paths: List[str] = []
    for raw_path in paths:
        if not raw_path or not isinstance(raw_path, str):
            return False, [], "Security Block: Invalid file path descriptor."

        # 1. Block Unicode BiDi / RTLO extension spoofing
        if contains_bidi_spoofing(raw_path) or "\x00" in raw_path:
            return False, [], "Security Block: File name contains spoofing or null characters."

        cleaned = raw_path.strip()

        # 2. Block UNC network shares (\\server\share) and device namespaces (\\.\, \\?\)
        if cleaned.startswith("\\\\") or cleaned.startswith("//"):
            return False, [], "Security Block: Remote network (UNC/SMB) and device paths are prohibited."

        # 3. Block NTFS Alternate Data Streams (e.g. C:\dir\doc.pdf:evil.exe)
        drive, tail = os.path.splitdrive(cleaned)
        if not drive or ":" in tail:
            return False, [], "Security Block: NTFS Alternate Data Streams (ADS) are prohibited."

        norm_path = os.path.abspath(os.path.normpath(cleaned))
        basename = os.path.basename(norm_path).rstrip(". ")
        if not basename:
            return False, [], "Security Block: Invalid file name."

        # 4. Block Windows reserved device names
        stem = basename.split(".")[0].upper()
        if stem in _RESERVED_DEVICES:
            return False, [], f"Security Block: Reserved device name '{basename}' is prohibited."

        # 5. Inspect final extension AND all intermediate extensions (double-extension guard: e.g. report.pdf.exe)
        parts = basename.lower().split(".")
        if len(parts) > 1:
            for ext_part in parts[1:]:
                dot_ext = "." + ext_part
                if dot_ext in BLOCKED_EXTENSIONS:
                    return (
                        False,
                        [],
                        f"Security Block: '{basename}' has a restricted executable/script extension ({dot_ext}).",
                    )

        # 6. Verify path exists on local disk and check resolved symlink/reparse target
        if not os.path.exists(norm_path):
            return False, [], f"File not found: '{basename}'."

        try:
            real_path = os.path.realpath(norm_path)
            if real_path.startswith("\\\\") and not real_path.startswith("\\\\?\\"):
                return False, [], f"Security Block: '{basename}' resolves to a remote network share."
            real_base = os.path.basename(real_path).rstrip(". ").lower()
            _, real_ext = os.path.splitext(real_base)
            if real_ext in BLOCKED_EXTENSIONS:
                return (
                    False,
                    [],
                    f"Security Block: '{basename}' links to a restricted executable ({real_ext}).",
                )
        except Exception:
            return False, [], f"Security Block: Could not verify target of '{basename}'."

        safe_paths.append(norm_path)

    return True, safe_paths, ""


def extract_fragment_html(raw_html: str) -> str:
    """Extract only the user-selected fragment from CF_HTML, discarding document <head> metadata."""
    if not raw_html:
        return ""
    start_match = re.search(r"<!--StartFragment-->", raw_html, re.IGNORECASE)
    end_match = re.search(r"<!--EndFragment-->", raw_html, re.IGNORECASE)
    if start_match and end_match and start_match.end() <= end_match.start():
        return raw_html[start_match.end():end_match.start()]
    # If no fragment markers, strip out the <head>...</head> section where Office puts metadata links
    return re.sub(r"<head\b[^>]*>.*?</head>", "", raw_html, flags=re.IGNORECASE | re.DOTALL)


def extract_href_from_cf_html(cf_html: str) -> Optional[str]:
    """If CF_HTML contains a single hyperlink, extract its raw href URL for unformatted pasting."""
    if not cf_html:
        return None
    fragment = extract_fragment_html(cf_html)
    matches = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', fragment, flags=re.IGNORECASE)
    if len(matches) == 1:
        return html.unescape(matches[0].strip())
    return None


def sanitize_unformatted_text_and_links(
    raw_text: str, raw_html: Optional[str] = None
) -> Tuple[bool, str, bool, str]:
    """Sanitize copied text or links, stripping all formatting and blocking dangerous URI schemes.

    Returns (allowed: bool, clean_text: str, is_link: bool, error_message: str).
    """
    text = raw_text or ""
    if not text.strip() and raw_html:
        # Extract plain text from HTML fragment without any formatting
        href = extract_href_from_cf_html(raw_html)
        if href:
            text = href
        else:
            text = html.unescape(_HTML_TAG_RE.sub("", raw_html))

    if not text:
        return False, "", False, "Clipboard is empty."

    # 1. Remove zero-width & BiDi spoofing characters and NUL bytes
    text = _SPOOF_CHARS_RE.sub("", text).replace("\x00", "")

    # 2. Check for dangerous URI schemes if the payload is an executable link/protocol
    stripped = text.strip()
    is_link = bool(_URL_DETECT_RE.match(stripped))

    if is_link:
        scheme_m = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*:)", stripped)
        if scheme_m:
            scheme = scheme_m.group(1).lower()
            for blocked in BLOCKED_URI_SCHEMES:
                if scheme == blocked:
                    return (
                        False,
                        "",
                        False,
                        f"Security Block: Unsafe executable link protocol '{scheme}' prevented.",
                    )
        clean_link = re.sub(r"[\r\n\t\x00-\x1f\x7f]", "", stripped)
        return True, clean_link, True, ""

    # Check for dangerous executable URIs (e.g. "javascript:...", "file://...", "ms-msdt://...")
    # Avoid false positives on common English text followed by a colon (e.g. "File: notes", "Search: report")
    for match in re.finditer(r"(?:^|[\s\"'(<])([a-zA-Z][a-zA-Z0-9+.-]{1,24}:(?:/{2,3}|\\{2,3}|[^\s]))", text):
        raw_m = match.group(1)
        scheme = raw_m.split(":", 1)[0].lower() + ":"
        rest = raw_m.split(":", 1)[1]
        # Only block if scheme matches AND is followed by slashes or no space (e.g. javascript:... or file://...)
        if scheme in BLOCKED_URI_SCHEMES and (rest.startswith("//") or rest.startswith("\\\\") or scheme in ("javascript:", "vbscript:", "data:", "hta:")):
            return (
                False,
                "",
                False,
                f"Security Block: Unsafe executable link protocol '{scheme}' prevented.",
            )

    # If the user copied rich HTML without plain text, inspect links in the fragment
    if not (raw_text and raw_text.strip()) and raw_html:
        fragment = extract_fragment_html(raw_html)
        for match in re.finditer(
            r'<(?:a|iframe|object|embed|script)\b[^>]*\b(?:href|src)\s*=\s*["\']?\s*([a-zA-Z][a-zA-Z0-9+.-]*:)',
            fragment,
            re.IGNORECASE,
        ):
            scheme = match.group(1).lower()
            if scheme in BLOCKED_URI_SCHEMES:
                return (
                    False,
                    "",
                    False,
                    f"Security Block: Embedded HTML link uses unsafe protocol '{scheme}'.",
                )

    # 4. If it's a single-line link/URL, strip any embedded CR/LF/control chars (anti-pastejacking)
    if is_link:
        clean_link = re.sub(r"[\r\n\t\x00-\x1f\x7f]", "", stripped)
        return True, clean_link, True, ""

    # 5. For normal plain text, normalize line endings and strip non-printable control chars (except \r, \n, \t)
    clean_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return True, clean_text, False, ""


def sanitize_svg_diagram(svg_bytes: bytes) -> Tuple[bool, bytes, str]:
    """Sanitize SVG vector diagram data by stripping scripts, foreignObjects, and event handlers."""
    try:
        svg_text = svg_bytes.decode("utf-8", errors="replace")
    except Exception:
        return False, b"", "Security Block: Invalid SVG encoding."

    if "<svg" not in svg_text.lower():
        return False, b"", "Security Block: Malformed SVG diagram payload."

    # Remove <script>...</script> and <foreignObject>...</foreignObject>
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", svg_text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<script\b[^>]*/?>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<foreignObject\b[^>]*>.*?</foreignObject>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    # Remove inline event handlers (onload=, onerror=, onclick=, etc.)
    cleaned = re.sub(r"\bon[a-zA-Z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", cleaned, flags=re.IGNORECASE)
    # Neutralize javascript: / data: / vbscript: inside href / xlink:href
    cleaned = re.sub(
        r"((?:xlink:)?href\s*=\s*[\"'])\s*(?:javascript|vbscript|data):[^\"']*([\"'])",
        r"\1#\2",
        cleaned,
        flags=re.IGNORECASE,
    )
    return True, cleaned.encode("utf-8"), ""


def validate_image_binary(fmt: str, data: bytes) -> Tuple[bool, Tuple[int, int], str]:
    """Validate binary image header (PNG or CF_DIB/CF_DIBV5) and return (ok, (width, height), err)."""
    if not data or len(data) < 24:
        return False, (0, 0), "Security Block: Image buffer is truncated or empty."

    if len(data) > 150 * 1024 * 1024:
        return False, (0, 0), "Security Block: Image exceeds 150 MB safety limit."

    if fmt == "PNG":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, (0, 0), "Security Block: Invalid PNG signature."
        try:
            w, h = struct.unpack(">II", data[16:24])
            if not (1 <= w <= 32768 and 1 <= h <= 32768):
                return False, (0, 0), f"Security Block: Invalid PNG dimensions ({w}x{h})."
            return True, (int(w), int(h)), ""
        except Exception:
            return False, (0, 0), "Security Block: Corrupt PNG header."

    if fmt in ("CF_DIB", "CF_DIBV5"):
        try:
            bi_size, w, h = struct.unpack("<Iii", data[:12])
            abs_h = abs(int(h))
            if bi_size < 40 or not (1 <= w <= 32768 and 1 <= abs_h <= 32768):
                return False, (0, 0), "Security Block: Invalid DIB bitmap header."
            return True, (int(w), abs_h), ""
        except Exception:
            return False, (0, 0), "Security Block: Corrupt DIB bitmap header."

    return False, (0, 0), f"Security Block: Unsupported image format '{fmt}'."
