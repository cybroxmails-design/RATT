"""RATT Translation Module.

Translates clipboard slot content across supported languages for Premium and
Enterprise subscribers.
"""
from typing import Optional, List, Tuple


# Supported languages (ISO 639-1 codes)
SUPPORTED_LANGUAGES: List[Tuple[str, str]] = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("ru", "Russian"),
    ("zh", "Chinese (Simplified)"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("bn", "Bengali"),
    ("tr", "Turkish"),
    ("nl", "Dutch"),
    ("sv", "Swedish"),
    ("pl", "Polish"),
    ("uk", "Ukrainian"),
    ("vi", "Vietnamese"),
    ("th", "Thai"),
    ("id", "Indonesian"),
    ("ms", "Malay"),
    ("fil", "Filipino"),
    ("sw", "Swahili"),
    ("he", "Hebrew"),
    ("el", "Greek"),
    ("cs", "Czech"),
    ("ro", "Romanian"),
    ("hu", "Hungarian"),
    ("da", "Danish"),
    ("fi", "Finnish"),
    ("no", "Norwegian"),
    ("sk", "Slovak"),
    ("bg", "Bulgarian"),
    ("hr", "Croatian"),
    ("lt", "Lithuanian"),
    ("lv", "Latvian"),
    ("et", "Estonian"),
    ("sl", "Slovenian"),
    ("ga", "Irish"),
    ("mt", "Maltese"),
    ("ca", "Catalan"),
    ("eu", "Basque"),
    ("gl", "Galician"),
    ("af", "Afrikaans"),
    ("am", "Amharic"),
    ("my", "Burmese"),
    ("km", "Khmer"),
    ("lo", "Lao"),
    ("ne", "Nepali"),
    ("si", "Sinhala"),
    ("ta", "Tamil"),
    ("te", "Telugu"),
    ("ur", "Urdu"),
    ("fa", "Persian"),
]


def get_language_names() -> List[str]:
    """Get list of supported language names."""
    return [name for _, name in SUPPORTED_LANGUAGES]


def get_language_code(name: str) -> Optional[str]:
    """Get language code from name."""
    for code, lang_name in SUPPORTED_LANGUAGES:
        if lang_name.lower() == name.lower():
            return code
    return None


def get_language_name(code: str) -> Optional[str]:
    """Get language name from code."""
    for lang_code, name in SUPPORTED_LANGUAGES:
        if lang_code == code:
            return name
    return None


class TranslationError(Exception):
    """Raised when text cannot be translated (network down, bad key, ...)."""


# Codes the web endpoint spells differently
_GTX_CODES = {"zh": "zh-CN", "fil": "tl", "he": "iw"}
_public_endpoint_consent = False


class TranslationManager:
    """Translates text. Long text is split into chunks on line boundaries."""

    CHUNK = 3000

    @property
    def is_available(self) -> bool:
        return True

    def ensure_consent(self, parent=None) -> bool:
        """Confirm user consent before sending slot text to the HTTPS translation service."""
        global _public_endpoint_consent
        from ratt import api_config
        key = api_config.get_value("GOOGLE_TRANSLATE_KEY")
        if key or _public_endpoint_consent:
            return True
        from tkinter import messagebox
        ok = messagebox.askyesno(
            "Translation Service Consent",
            "Do you consent to sending the selected slot text over HTTPS to the "
            "translation service?",
            parent=parent,
        )
        if ok:
            _public_endpoint_consent = True
        return bool(ok)

    @staticmethod
    def _chunks(text: str):
        """Split on newlines into pieces of at most CHUNK characters."""
        out, cur = [], ""
        for line in text.splitlines(keepends=True):
            while len(line) > TranslationManager.CHUNK:       # one huge line
                if cur:
                    out.append(cur)
                    cur = ""
                out.append(line[:TranslationManager.CHUNK])
                line = line[TranslationManager.CHUNK:]
            if len(cur) + len(line) > TranslationManager.CHUNK:
                out.append(cur)
                cur = ""
            cur += line
        if cur:
            out.append(cur)
        return out

    def translate(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """Translate `text` to `target_language` (ISO code such as 'fr').
        Raises TranslationError on failure."""
        if not text or not text.strip():
            return text
        from ratt import api_config
        key = api_config.get_value("GOOGLE_TRANSLATE_KEY")
        parts = []
        for chunk in self._chunks(text):
            parts.append(self._cloud(chunk, target_language, source_language, key) if key
                         else self._web(chunk, target_language, source_language))
        return "".join(parts)

    # ---- backends ----

    @staticmethod
    def _validate_lang_code(code: str, allow_auto: bool = False) -> str:
        c = (code or "").strip().lower()
        if allow_auto and c == "auto":
            return "auto"
        valid_codes = {lc for lc, _ in SUPPORTED_LANGUAGES}
        if c not in valid_codes:
            raise TranslationError(f"Unsupported language code: {code!r}")
        return c

    def _web(self, chunk, target, source):
        import json
        import urllib.parse
        import urllib.request
        clean_target = self._validate_lang_code(target, allow_auto=False)
        clean_source = self._validate_lang_code(source, allow_auto=True)
        tl = urllib.parse.quote(_GTX_CODES.get(clean_target, clean_target), safe="")
        sl = "auto" if clean_source == "auto" else urllib.parse.quote(_GTX_CODES.get(clean_source, clean_source), safe="")
        url = ("https://translate.googleapis.com/translate_a/single?client=gtx"
               f"&sl={sl}&tl={tl}&dt=t")
        req = urllib.request.Request(
            url, data=urllib.parse.urlencode({"q": chunk}).encode("utf-8"),
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return "".join(seg[0] for seg in data[0] if seg and seg[0])
        except Exception as e:
            raise TranslationError(f"Translation service unreachable ({e.__class__.__name__}). Check your internet connection.")

    def _cloud(self, chunk, target, source, key):
        import json
        import urllib.request
        import html
        clean_target = self._validate_lang_code(target, allow_auto=False)
        clean_source = self._validate_lang_code(source, allow_auto=True)
        body = {"q": chunk, "target": _GTX_CODES.get(clean_target, clean_target), "format": "text"}
        if clean_source != "auto":
            body["source"] = _GTX_CODES.get(clean_source, clean_source)
        # COM-08: Pass API key in HTTP header rather than URL query string
        req = urllib.request.Request(
            "https://translation.googleapis.com/language/translate/v2",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": key,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return html.unescape(data["data"]["translations"][0]["translatedText"])
        except Exception as e:
            raise TranslationError(f"Google Cloud Translation failed ({e.__class__.__name__}). Check the API key in Settings.")

    def detect_language(self, text: str) -> Optional[str]:
        return None
