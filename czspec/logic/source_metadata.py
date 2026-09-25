"""Metadatos de fuente y bitácora persistente para CZSpec.

M1 utiliza este módulo para conservar un contrato único de metadatos entre
formatos ASCII, CLASS .30m y FITS. La resolución de nombres mediante SIMBAD es
opcional: nunca se inventan VLSR ni temperaturas si el catálogo no las aporta.
"""
from __future__ import annotations

from czspec.network import require_online

from dataclasses import dataclass, asdict, field
from pathlib import Path
import json
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np

from czspec.paths import WORKSPACE_DIR

C_KMS = 299792.458
REGISTRY_PATH = WORKSPACE_DIR / "config" / "source_registry.json"

# Bitácora mínima que facilita alias muy frecuentes. El registro editable del
# usuario tiene prioridad y SIMBAD sigue siendo la fuente de nombres canónicos.
BUILTIN_SOURCES = [
    {"canonical_name": "LkHalpha 234", "aliases": ["LKHA234", "LKH234", "LKHα234", "LkHa234"]},
    {"canonical_name": "Cepheus A", "aliases": ["CEPHEUSA", "CEPA", "Cep A"]},
    {"canonical_name": "G31.41+0.31", "aliases": ["G31.41", "G31.41+0.31", "G31"]},
]


@dataclass
class SourceMetadata:
    raw_source_name: str = ""
    canonical_name: str = ""
    aliases: list[str] = field(default_factory=list)
    ra_deg: float | None = None
    dec_deg: float | None = None
    vlsr_kms: float | None = None
    rest_frequency_mhz: float | None = None
    spectral_reference_frame: str = ""
    equinox: float | None = None
    telescope: str = ""
    instrument: str = ""
    bunit: str = ""
    beam_eff: float | None = None
    forward_eff: float | None = None
    excitation_temperatures_k: list[float] = field(default_factory=list)
    kinetic_temperature_k: float | None = None
    rotational_temperature_k: float | None = None
    velocity_reference_channel: float | None = None
    velocity_step_kms: float | None = None
    frequency_step_mhz: float | None = None
    provenance: dict[str, str] = field(default_factory=dict)
    profile_id: str = ""
    profile_name: str = ""
    component: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        # Compatibilidad con claves ya usadas en varios módulos.
        out["source"] = self.canonical_name or self.raw_source_name
        return out


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None




def format_ra_hms(ra_deg: float | None, precision: int = 2) -> str:
    """Formatea ascensión recta decimal en ``hh:mm:ss``."""
    value = _finite_float(ra_deg)
    if value is None:
        return ""
    hours = (value % 360.0) / 15.0
    h = int(hours)
    minutes = (hours - h) * 60.0
    m = int(minutes)
    sec = (minutes - m) * 60.0
    width = 2 + int(precision) + (1 if precision else 0)
    return f"{h:02d}:{m:02d}:{sec:0{width}.{precision}f}"


def format_dec_dms(dec_deg: float | None, precision: int = 2) -> str:
    """Formatea declinación decimal en ``±dd:mm:ss``."""
    value = _finite_float(dec_deg)
    if value is None:
        return ""
    sign = "+" if value >= 0 else "-"
    absolute = abs(value)
    d = int(absolute)
    minutes = (absolute - d) * 60.0
    m = int(minutes)
    sec = (minutes - m) * 60.0
    width = 2 + int(precision) + (1 if precision else 0)
    return f"{sign}{d:02d}:{m:02d}:{sec:0{width}.{precision}f}"


def parse_ra_hms(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if not any(mark in text.lower() for mark in (":", "h", "m", "s")):
            number = float(text)
            return number if math.isfinite(number) else None
    except Exception:
        pass
    clean = text.lower().replace("h", ":").replace("m", ":").replace("s", "")
    parts = [part for part in re.split(r"[:\s]+", clean) if part]
    if len(parts) < 1:
        return None
    try:
        h = float(parts[0]); m = float(parts[1]) if len(parts) > 1 else 0.0; sec = float(parts[2]) if len(parts) > 2 else 0.0
        sign = -1.0 if h < 0 else 1.0
        hours = sign * (abs(h) + abs(m) / 60.0 + abs(sec) / 3600.0)
        return (hours * 15.0) % 360.0
    except Exception:
        return None


def parse_dec_dms(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if not any(mark in text.lower() for mark in (":", "d", "°", "'", '"')):
            number = float(text)
            return number if math.isfinite(number) else None
    except Exception:
        pass
    clean = (text.lower().replace("°", ":").replace("d", ":")
             .replace("'", ":").replace('"', ""))
    parts = [part for part in re.split(r"[:\s]+", clean) if part]
    try:
        d = float(parts[0]); m = float(parts[1]) if len(parts) > 1 else 0.0; sec = float(parts[2]) if len(parts) > 2 else 0.0
        sign = -1.0 if str(parts[0]).startswith("-") or d < 0 else 1.0
        return sign * (abs(d) + abs(m) / 60.0 + abs(sec) / 3600.0)
    except Exception:
        return None


def _parse_temperature_list(value: str) -> list[float]:
    values = []
    for token in re.split(r"[,;/\s]+", str(value).strip()):
        if not token:
            continue
        number = _finite_float(re.sub(r"[^0-9eE+\-.]", "", token))
        if number is not None and number > 0:
            values.append(number)
    return sorted(set(values))


def _parse_coord_pair(ra_text: str, dec_text: str) -> tuple[float | None, float | None]:
    """Interpreta coordenadas decimales o sexagesimales usando Astropy."""
    ra_clean, dec_clean = str(ra_text).strip(), str(dec_text).strip()
    try:
        # Decimal degrees do not require Astropy; useful for lightweight readers.
        if not any(mark in ra_clean.lower() for mark in (":", "h", "m", "s")):
            return float(ra_clean), float(dec_clean)
    except Exception:
        pass
    try:
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        # Si RA contiene ':'/h se interpreta como hora; de lo contrario grados.
        if any(mark in ra_clean.lower() for mark in (":", "h", "m", "s")):
            coord = SkyCoord(ra_clean, dec_clean, unit=(u.hourangle, u.deg), frame="icrs")
        else:
            coord = SkyCoord(float(ra_clean) * u.deg, float(dec_clean) * u.deg, frame="icrs")
        return float(coord.ra.deg), float(coord.dec.deg)
    except Exception:
        return None, None


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def parse_ascii_header(path: str | Path, max_lines: int = 300) -> dict[str, Any]:
    """Parse tolerant structured ASCII metadata without discarding unknown keys.

    Recognized fields are normalized into CZSpec's internal schema.  Unknown
    ``key: value``/``key=value`` entries are retained under ``extra_metadata``.
    ``reference_frequency`` (M1 display reference) and ``rest_frequency``
    (physical transition rest frequency) are deliberately distinct.
    """
    p = Path(path)
    result: dict[str, Any] = {}
    if not p.is_file():
        return result
    lines: list[str] = []
    try:
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            for _ in range(max_lines):
                line = fh.readline()
                if not line:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                if re.match(r"^[+\-]?(?:\d|\.\d)", stripped):
                    break
                lines.append(stripped.lstrip("#!;% "))
    except Exception:
        return result

    raw_pairs: dict[str, tuple[str, str]] = {}
    for line in lines:
        for frag in re.split(r"\s*\|\s*", line):
            match = re.match(r"^\s*([A-Za-z][A-Za-z0-9_ .\-/()]+?)\s*[:=]\s*(.*?)\s*$", frag)
            if match:
                original = match.group(1).strip()
                raw_pairs[_normalized_key(original)] = (original, match.group(2).strip())
    pairs = {k:v for k,(_orig,v) in raw_pairs.items()}

    aliases = {
        "source": ("source","object","target","sourcename","rawsource","rawsourcename"),
        "canonical": ("canonicalname","canonicalsource","realname"),
        "ra": ("ra","radeg","rightascension","alpha","lambda"),
        "dec": ("dec","decdeg","declination","delta","beta"),
        "vlsr": ("vlsr","vlsrkms","velolsr","lsrvelocity","sourcevelocity","systemicvelocity"),
        "rest": ("restfreq","restfrequency","restfrequencymhz","molecularrestfrequency"),
        "reference": ("referencefrequency","referencefrequencymhz","spectralreferencefrequency","spectralaxisreferencefrequency","nuref"),
        "telescope": ("telescope","observatory","facility"),
        "instrument": ("instrument","backend","receiver"),
        "bunit": ("bunit","yunit","intensityunit"),
        "xunit": ("xunit","spectralunit","frequencyunit"),
        "beam": ("beameff","beamefficiency","eta","etamb"),
        "beamsize": ("beam","beamsize","beamfwhm","beamfwhmarcsec"),
        "forward": ("forwardeff","forwardefficiency","feff"),
        "tex": ("tex","texk","texcitation","excitationtemperature","excitationtemperatures"),
        "tkin": ("tkin","kinetictemperature","tkinetic"),
        "trot": ("trot","rotationaltemperature"),
        "specsys": ("specsys","spectralreferenceframe","velocityframe","frame"),
        "convention": ("velocityconvention","dopplerconvention"),
        "freqstep": ("frequencystepmhz","freqstep","freqstepmhz","channelspacingmhz"),
        "velostep": ("velocitystepkms","velostep","velostepkms","channelspacingkms"),
        "velref": ("velocityreferencechannel","referencechannel","classreferencechannel"),
        "classfreq": ("classreferencefrequencymhz","classfrequency","classfrequencymhz"),
        "classvelo": ("classreferencevelocitykms","classvelocity","classvelocitykms"),
        "classfreqstep": ("classfrequencystepmhz",),
        "classvelostep": ("classvelocitystepkms",),
        "equinox": ("equinox","coordinateequinox"),
        "profile": ("profilename","metadataprofile","profile"),
        "component": ("component","region","subcomponent"),
        "date": ("observationdate","dateobs","date"),
        "jyk": ("jyk","jykfactor","jyperk","jyperkfactor"),
    }
    consumed=set()
    def first(kind):
        for key in aliases[kind]:
            if key in pairs:
                consumed.add(key); return pairs[key]
        return None
    def number_with_freq_unit(text):
        if text is None: return None
        n=_finite_float(re.sub(r"[^0-9eE+\-.]", "", str(text)))
        if n is None: return None
        low=str(text).lower()
        if "thz" in low: n*=1e6
        elif "ghz" in low: n*=1e3
        elif "khz" in low: n/=1e3
        elif "hz" in low and "mhz" not in low: n/=1e6
        return n

    source=first("source"); canonical=first("canonical")
    if source: result["raw_source_name"]=source
    if canonical: result["canonical_name"]=canonical
    ra,dec=first("ra"),first("dec")
    if ra is not None and dec is not None:
        ra_deg,dec_deg=_parse_coord_pair(ra,dec)
        if ra_deg is not None: result["ra_deg"]=ra_deg
        if dec_deg is not None: result["dec_deg"]=dec_deg

    numeric=(
        ("vlsr_kms","vlsr"),("beam_eff","beam"),("forward_eff","forward"),
        ("kinetic_temperature_k","tkin"),("rotational_temperature_k","trot"),
        ("frequency_step_mhz","freqstep"),("velocity_step_kms","velostep"),
        ("velocity_reference_channel","velref"),("equinox","equinox"),
        ("beam_arcsec","beamsize"),("jy_per_k","jyk"),
        ("class_reference_channel","velref"),("class_reference_velocity_kms","classvelo"),
        ("class_frequency_step_mhz","classfreqstep"),("class_velocity_step_kms","classvelostep"),
    )
    for outkey,kind in numeric:
        value=first(kind)
        if value is not None:
            n=_finite_float(re.sub(r"[^0-9eE+\-.]", "", str(value)))
            if n is not None: result[outkey]=n
    rest=first("rest"); ref=first("reference"); classfreq=first("classfreq")
    n=number_with_freq_unit(rest)
    if n is not None: result["rest_frequency_mhz"]=n
    n=number_with_freq_unit(ref)
    if n is not None: result["spectral_axis_reference_frequency_mhz"]=n
    n=number_with_freq_unit(classfreq)
    if n is not None: result["class_reference_frequency_mhz"]=n

    tex=first("tex")
    if tex: result["excitation_temperatures_k"]=_parse_temperature_list(tex)
    text_fields=(("telescope","telescope"),("instrument","instrument"),("bunit","bunit"),
                 ("input_frequency_unit","xunit"),("spectral_reference_frame","specsys"),
                 ("velocity_convention","convention"),("profile_name","profile"),
                 ("component","component"),("observation_date","date"))
    for outkey,kind in text_fields:
        value=first(kind)
        if value: result[outkey]=value

    extra={orig: value for norm,(orig,value) in raw_pairs.items() if norm not in consumed}
    if extra: result["extra_metadata"]=extra
    result["metadata_categories"]={
        "recognized_used": sorted(k for k in result if k not in {"extra_metadata","metadata_categories","provenance"}),
        "recognized_unused_m1": sorted(k for k in ("rest_frequency_mhz","vlsr_kms") if k in result),
        "unknown_preserved": sorted(extra),
    }
    if result:
        result.setdefault("provenance", {})["ascii_header"] = str(p)
    return result


def merge_metadata(*items: dict | SourceMetadata | None) -> dict[str, Any]:
    """Fusiona metadatos de izquierda a derecha sin borrar valores útiles."""
    out: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for item in items:
        if not item:
            continue
        data = item.as_dict() if isinstance(item, SourceMetadata) else dict(item)
        provenance.update(dict(data.pop("provenance", {}) or {}))
        for key, value in data.items():
            if value is None or value == "" or value == []:
                continue
            out[key] = value
    if provenance:
        out["provenance"] = provenance
    return out


class SourceRegistry:
    """Bitácora persistente de perfiles físicos por fuente.

    A diferencia de versiones anteriores, una misma fuente puede tener múltiples
    perfiles (global, hot core, envolvente, outflow, etc.). El ``profile_id``
    identifica cada registro; el nombre canónico ya no es una clave única.
    """
    def __init__(self, path: str | Path = REGISTRY_PATH):
        self.path = Path(path)
        self.builtin_entries = [
            {**dict(row), "profile_id": f"builtin:{_normalized_key(row.get('canonical_name',''))}",
             "profile_name": "Referencia global", "builtin": True}
            for row in BUILTIN_SOURCES
        ]
        self.user_entries = self._load_user_entries()
        self.entries = [*self.builtin_entries, *self.user_entries]

    def _load_user_entries(self) -> list[dict[str, Any]]:
        try:
            if not self.path.is_file():
                return []
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                rows = payload.get("profiles", payload.get("sources", []))
            else:
                rows = payload
            if not isinstance(rows, list):
                return []
            out=[]
            for row in rows:
                if not isinstance(row, dict):
                    continue
                item=dict(row)
                item.setdefault("profile_id", uuid.uuid4().hex)
                item.setdefault("profile_name", item.get("component") or "Global")
                out.append(item)
            return out
        except Exception:
            return []

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"profiles": self.user_entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.entries = [*self.builtin_entries, *self.user_entries]

    def save_entry(self, metadata: dict[str, Any], *, duplicate: bool = False) -> dict[str, Any]:
        entry = {k: v for k, v in dict(metadata).items() if v not in (None, "", [])}
        canonical = str(entry.get("canonical_name") or entry.get("raw_source_name") or "").strip()
        if not canonical:
            raise ValueError("Se requiere un nombre para guardar la fuente en la bitácora.")
        entry["canonical_name"] = canonical
        aliases = list(entry.get("aliases") or [])
        raw = str(entry.get("raw_source_name") or "").strip()
        if raw and raw not in aliases and raw != canonical:
            aliases.append(raw)
        entry["aliases"] = aliases
        entry["profile_name"] = str(entry.get("profile_name") or entry.get("component") or "Global").strip() or "Global"
        entry["component"] = str(entry.get("component") or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        profile_id = str(entry.get("profile_id") or "").strip()
        if duplicate or not profile_id or profile_id.startswith("builtin:"):
            profile_id = uuid.uuid4().hex
            entry["created_at"] = now
        else:
            for old in self.user_entries:
                if str(old.get("profile_id")) == profile_id:
                    entry.setdefault("created_at", old.get("created_at") or now)
                    break
        entry["profile_id"] = profile_id
        entry["updated_at"] = now
        replaced=False
        for idx, row in enumerate(self.user_entries):
            if str(row.get("profile_id")) == profile_id:
                self.user_entries[idx]=entry; replaced=True; break
        if not replaced:
            self.user_entries.append(entry)
        self._write()
        return dict(entry)

    def delete_entry(self, profile_id: str) -> bool:
        pid=str(profile_id or "")
        before=len(self.user_entries)
        self.user_entries=[row for row in self.user_entries if str(row.get("profile_id")) != pid]
        if len(self.user_entries) != before:
            self._write(); return True
        return False

    def list_profiles(self, raw_name: str = "", canonical_name: str = "",
                      ra_deg: float | None = None, dec_deg: float | None = None,
                      radius_arcsec: float = 60.0, include_builtin: bool = False) -> list[dict[str, Any]]:
        rows = self.entries if include_builtin else self.user_entries
        keys={_normalized_key(raw_name), _normalized_key(canonical_name)} - {""}
        matched=[]
        for row in rows:
            names=[row.get("canonical_name", ""), *(row.get("aliases") or []), row.get("raw_source_name", "")]
            if keys and any(_normalized_key(name) in keys for name in names):
                matched.append(dict(row)); continue
            rra, rdec=_finite_float(row.get("ra_deg")), _finite_float(row.get("dec_deg"))
            if ra_deg is None or dec_deg is None or rra is None or rdec is None:
                continue
            # Pequeña separación angular sin exigir Astropy.
            dra=math.radians(rra-float(ra_deg)); d1=math.radians(float(dec_deg)); d2=math.radians(rdec)
            a=math.sin((d2-d1)/2)**2 + math.cos(d1)*math.cos(d2)*math.sin(dra/2)**2
            sep=math.degrees(2*math.asin(min(1.0, math.sqrt(max(0.0,a)))))*3600.0
            if sep <= radius_arcsec:
                matched.append(dict(row))
        return matched

    def match(self, raw_name: str = "", ra_deg: float | None = None, dec_deg: float | None = None,
              radius_arcsec: float = 30.0) -> dict[str, Any] | None:
        key = _normalized_key(raw_name)
        # Para autoaplicación sólo usamos un perfil inequívoco. Si hay varios
        # perfiles físicos de la misma fuente, M1 conserva sólo nombre/posición
        # base y deja que el usuario elija explícitamente el perfil térmico.
        candidates=self.list_profiles(raw_name=raw_name, ra_deg=ra_deg, dec_deg=dec_deg,
                                      radius_arcsec=radius_arcsec, include_builtin=True)
        user=[row for row in candidates if not row.get("builtin")]
        if len(user)==1:
            return dict(user[0])
        if len(user)>1:
            # No inyectar Tex/Tkin/Trot ambiguos; combinar sólo identidad de la fuente.
            row=dict(user[-1])
            for key_phys in ("excitation_temperatures_k","kinetic_temperature_k","rotational_temperature_k",
                             "profile_id","profile_name","component","notes"):
                row.pop(key_phys, None)
            return row
        if candidates:
            return dict(candidates[-1])
        return None

def _simbad_row_coordinates(row, colnames) -> tuple[float | None, float | None]:
    """Lee coordenadas SIMBAD sin confundir grados decimales con hourangle.

    Astroquery moderno devuelve ``ra`` y ``dec`` en grados decimales. Versiones
    antiguas/campos personalizados pueden devolver texto sexagesimal; se aceptan
    ambos formatos. Esta distinción evita el bug histórico en el que una RA como
    344.08 deg se interpretaba como 344 horas.
    """
    ra_col = next((name for name in ("ra", "RA") if name in colnames), None)
    dec_col = next((name for name in ("dec", "DEC") if name in colnames), None)
    if not ra_col or not dec_col:
        return None, None
    raw_ra, raw_dec = row[ra_col], row[dec_col]
    try:
        ra_num, dec_num = float(raw_ra), float(raw_dec)
        if math.isfinite(ra_num) and math.isfinite(dec_num):
            return ra_num % 360.0, dec_num
    except Exception:
        pass
    try:
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        ra_text, dec_text = str(raw_ra).strip(), str(raw_dec).strip()
        hour_like = any(mark in ra_text.lower() for mark in (":", "h", "m", "s"))
        if hour_like:
            coord = SkyCoord(ra_text, dec_text, unit=(u.hourangle, u.deg), frame="icrs")
        else:
            coord = SkyCoord(float(ra_text) * u.deg, float(dec_text) * u.deg, frame="icrs")
        return float(coord.ra.deg), float(coord.dec.deg)
    except Exception:
        return None, None


def resolve_simbad_candidates(*, raw_name: str = "", canonical_name: str = "",
                              ra_deg: float | None = None, dec_deg: float | None = None,
                              radius_arcsec: float = 90.0, limit: int = 12) -> list[dict[str, Any]]:
    """Devuelve candidatos SIMBAD ordenados por identidad y separación.

    Primero intenta el nombre canónico y el alias. Si ninguno resuelve, consulta
    la región. SIMBAD se usa sólo como ayuda de identidad/posición: no aporta ni
    sobreescribe VLSR, Tex, Tkin o Trot.
    """
    require_online("SIMBAD source resolution")
    try:
        from astroquery.simbad import Simbad
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        simbad = Simbad()
        try:
            simbad.add_votable_fields("otype")
        except Exception:
            pass
        target = None
        if ra_deg is not None and dec_deg is not None:
            try:
                target = SkyCoord(float(ra_deg) * u.deg, float(dec_deg) * u.deg, frame="icrs")
            except Exception:
                target = None

        rows = []
        seen = set()

        def consume(table, query_kind: str):
            if table is None or len(table) == 0:
                return
            colnames = list(table.colnames)
            main_col = next((name for name in ("main_id", "MAIN_ID") if name in colnames), None)
            otype_col = next((name for name in ("otype", "OTYPE") if name in colnames), None)
            for row in table:
                name = str(row[main_col]).strip() if main_col else ""
                rra, rdec = _simbad_row_coordinates(row, colnames)
                if not name and rra is None:
                    continue
                key = (_normalized_key(name), None if rra is None else round(rra, 8), None if rdec is None else round(rdec, 8))
                if key in seen:
                    continue
                seen.add(key)
                separation = None
                if target is not None and rra is not None and rdec is not None:
                    try:
                        separation = float(target.separation(SkyCoord(rra*u.deg, rdec*u.deg)).arcsec)
                    except Exception:
                        separation = None
                obj_type = ""
                if otype_col:
                    try:
                        obj_type = str(row[otype_col]).strip()
                    except Exception:
                        pass
                rows.append({
                    "canonical_name": name, "ra_deg": rra, "dec_deg": rdec,
                    "object_type": obj_type, "separation_arcsec": separation,
                    "query_kind": query_kind,
                    "provenance": {"canonical_name": "SIMBAD", "coordinates": "SIMBAD"},
                })

        # Priorizar el nombre canónico que el usuario ya conoce.
        for label in (canonical_name, raw_name):
            label = str(label or "").strip()
            if not label:
                continue
            try:
                table = simbad.query_object(label)
            except Exception:
                table = None
            if table is not None and len(table):
                consume(table, "name")
                # Una resolución directa de nombre es preferible a miles de fuentes
                # puntuales vecinas; aun así se conserva cualquier candidato previo.
                if rows:
                    break

        if not rows and target is not None:
            try:
                table = simbad.query_region(target, radius=float(radius_arcsec) * u.arcsec)
            except Exception:
                table = None
            consume(table, "position")

        rows.sort(key=lambda item: (0 if item.get("query_kind") == "name" else 1,
                                    float("inf") if item.get("separation_arcsec") is None else item["separation_arcsec"]))
        return rows[:max(1, int(limit))]
    except Exception as exc:
        raise RuntimeError(f"No se pudo consultar SIMBAD: {exc}") from exc


def resolve_simbad(*, raw_name: str = "", canonical_name: str = "",
                   ra_deg: float | None = None, dec_deg: float | None = None,
                   radius_arcsec: float = 90.0) -> dict[str, Any]:
    """Compatibilidad: devuelve el candidato SIMBAD preferente."""
    candidates = resolve_simbad_candidates(raw_name=raw_name, canonical_name=canonical_name,
                                           ra_deg=ra_deg, dec_deg=dec_deg,
                                           radius_arcsec=radius_arcsec, limit=1)
    return dict(candidates[0]) if candidates else {}


def velocity_from_frequency(freq_mhz, rest_frequency_mhz: float):
    """Velocidad Doppler de radio respecto a una frecuencia de reposo."""
    freq = np.asarray(freq_mhz, dtype=float)
    rest = float(rest_frequency_mhz)
    if not np.isfinite(rest) or rest <= 0:
        raise ValueError("La frecuencia de reposo debe ser positiva.")
    return C_KMS * (rest - freq) / rest


def line_velocity_kms(observed_frequency_mhz: float, rest_frequency_mhz: float) -> float:
    return float(velocity_from_frequency(np.asarray([observed_frequency_mhz]), rest_frequency_mhz)[0])


def velocity_axis_from_metadata(freq_mhz, metadata: dict[str, Any]):
    """Convert frequency to the M1 display velocity coordinate.

    CLASS products use their native FREQUENCY/VELOCITY/FREQ_STEP/VELO_STEP
    calibration. Generic ASCII/FITS spectra require an explicit
    ``spectral_axis_reference_frequency_mhz`` and are shown as velocity
    relative to that reference. Source VLSR and molecular rest frequency are
    not used to invent an M1 axis.
    """
    freq = np.asarray(freq_mhz, dtype=float)
    meta = dict(metadata or {})
    f0 = _finite_float(meta.get("class_reference_frequency_mhz"))
    v0 = _finite_float(meta.get("class_reference_velocity_kms"))
    df = _finite_float(meta.get("class_frequency_step_mhz"))
    dv = _finite_float(meta.get("class_velocity_step_kms"))
    provenance = meta.get("provenance") or {}
    is_class = (
        isinstance(provenance, dict) and bool(provenance.get("class_header"))
    ) or "CLASS" in str(meta.get("spectral_reference_frame") or "").upper() \
      or "CLASS" in str(meta.get("spectral_axis_calibration") or "").upper()
    if is_class and (f0 is None or v0 is None or df in (None, 0.0) or dv is None):
        # Compatibility only for products that are explicitly known to come
        # from CLASS.  Generic rest_frequency/VLSR metadata must never define
        # the M1 display axis.
        lf0 = _finite_float(meta.get("rest_frequency_mhz"))
        lv0 = _finite_float(meta.get("vlsr_kms"))
        ldf = _finite_float(meta.get("frequency_step_mhz"))
        ldv = _finite_float(meta.get("velocity_step_kms"))
        if lf0 is not None and lv0 is not None and ldf not in (None, 0.0) and ldv is not None:
            f0, v0, df, dv = lf0, lv0, ldf, ldv
    if f0 is not None and v0 is not None and df not in (None, 0.0) and dv is not None:
        return v0 + (freq - f0) * (dv / df)
    if is_class:
        raise ValueError("CLASS velocity calibration is incomplete; generic reference-frequency fallback is disabled.")
    ref = _finite_float(meta.get("spectral_axis_reference_frequency_mhz"))
    if ref is None or ref <= 0:
        raise ValueError("No explicit M1 reference frequency or CLASS velocity calibration is available.")
    convention = str(meta.get("velocity_convention") or "radio").strip().lower()
    if convention not in {"radio", "radial radio", "radio velocity"}:
        raise ValueError(f"Unsupported M1 velocity convention: {convention}")
    return velocity_from_frequency(freq, ref)

