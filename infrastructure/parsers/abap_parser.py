"""ABAPSourceParser — extracts and classifies ABAP objects from ZIP archives.

Supports .abap and .txt source files, determines object type from file
extension/name patterns, and classifies business domain using semantic
analysis of object naming conventions (Z_FI_*, Z_MM_*, etc.).
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass

from domain.value_objects.object_type import ABAPObjectType, BusinessDomain


@dataclass(frozen=True)
class ParsedABAPObject:
    """A single ABAP object extracted from a source archive."""

    object_name: str
    object_type: ABAPObjectType
    source_code: str
    package_name: str


# ---------------------------------------------------------------------------
# Business domain classification by object name prefix
# ---------------------------------------------------------------------------

_DOMAIN_PREFIXES: list[tuple[re.Pattern[str], BusinessDomain]] = [
    (re.compile(r"^[ZY]_?FI", re.IGNORECASE), BusinessDomain.FI),
    (re.compile(r"^[ZY]_?CO", re.IGNORECASE), BusinessDomain.CO),
    (re.compile(r"^[ZY]_?MM", re.IGNORECASE), BusinessDomain.MM),
    (re.compile(r"^[ZY]_?SD", re.IGNORECASE), BusinessDomain.SD),
    (re.compile(r"^[ZY]_?PP", re.IGNORECASE), BusinessDomain.PP),
    (re.compile(r"^[ZY]_?HR", re.IGNORECASE), BusinessDomain.HCM),
    (re.compile(r"^[ZY]_?HCM", re.IGNORECASE), BusinessDomain.HCM),
    (re.compile(r"^[ZY]_?PA", re.IGNORECASE), BusinessDomain.HCM),
    (re.compile(r"^[ZY]_?QM", re.IGNORECASE), BusinessDomain.QM),
    (re.compile(r"^[ZY]_?PM", re.IGNORECASE), BusinessDomain.PM),
    (re.compile(r"^[ZY]_?PS", re.IGNORECASE), BusinessDomain.PS),
    (re.compile(r"^[ZY]_?WM", re.IGNORECASE), BusinessDomain.WM),
    (re.compile(r"^[ZY]_?EWM", re.IGNORECASE), BusinessDomain.EWMS),
    (re.compile(r"^[ZY]_?BC", re.IGNORECASE), BusinessDomain.BASIS),
    (re.compile(r"^[ZY]_?BASIS", re.IGNORECASE), BusinessDomain.BASIS),
    (re.compile(r"^[ZY]_?CA", re.IGNORECASE), BusinessDomain.CROSS_APPLICATION),
]

# Object type classification by file extension
_EXTENSION_MAP: dict[str, ABAPObjectType] = {
    ".prog.abap": ABAPObjectType.PROGRAM,
    ".fugr.abap": ABAPObjectType.FUNCTION_MODULE,
    ".clas.abap": ABAPObjectType.CLASS,
    ".intf.abap": ABAPObjectType.INTERFACE,
    ".incl.abap": ABAPObjectType.INCLUDE,
    ".enho.abap": ABAPObjectType.ENHANCEMENT,
    ".tabl.xml": ABAPObjectType.TABLE,
    ".view.xml": ABAPObjectType.VIEW,
    ".form.abap": ABAPObjectType.FORM,
    ".dtel.xml": ABAPObjectType.DATA_ELEMENT,
    ".doma.xml": ABAPObjectType.DOMAIN_TYPE,
    ".shlp.xml": ABAPObjectType.SEARCH_HELP,
    ".enqu.xml": ABAPObjectType.LOCK_OBJECT,
}


def _classify_object_type(filename: str) -> ABAPObjectType:
    """Determine ABAPObjectType from the filename extension pattern."""
    lower = filename.lower()
    for ext, obj_type in _EXTENSION_MAP.items():
        if lower.endswith(ext):
            return obj_type

    # Fallback heuristics
    if lower.endswith(".abap") or lower.endswith(".txt"):
        return ABAPObjectType.PROGRAM

    return ABAPObjectType.PROGRAM


def _classify_domain(object_name: str) -> BusinessDomain:
    """Classify business domain by matching object name against known prefixes."""
    for pattern, domain in _DOMAIN_PREFIXES:
        if pattern.match(object_name):
            return domain
    return BusinessDomain.UNKNOWN


def _extract_package_name(filepath: str) -> str:
    """Infer package name from directory structure within the ZIP.

    Convention: src/<PACKAGE>/<object_name>.<type>.abap
    Falls back to empty string if structure is flat.
    """
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) >= 2:
        # Use the first directory as package name
        return parts[0].upper()
    return ""


class ABAPSourceParser:
    """Parses ABAP source archives (ZIP) into structured ParsedABAPObject entries."""

    def parse_zip(self, file_bytes: bytes) -> list[ParsedABAPObject]:
        """Extract ABAP objects from a ZIP archive.

        Processes .abap and .txt files, determines object type from
        extension patterns, and classifies business domain from naming
        conventions.
        """
        objects: list[ParsedABAPObject] = []

        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            for entry in zf.namelist():
                # Skip directories and non-source files
                if entry.endswith("/"):
                    continue

                lower = entry.lower()
                if not (
                    lower.endswith(".abap")
                    or lower.endswith(".txt")
                    or lower.endswith(".xml")
                ):
                    continue

                source_code = zf.read(entry).decode("utf-8", errors="replace")

                # Derive object name from filename (strip path and extension)
                basename = entry.rsplit("/", 1)[-1]
                # Remove composite extension (.prog.abap -> just the name)
                object_name = basename.split(".")[0].upper()

                object_type = _classify_object_type(entry)
                package_name = _extract_package_name(entry)
                domain = _classify_domain(object_name)

                objects.append(
                    ParsedABAPObject(
                        object_name=object_name,
                        object_type=object_type,
                        source_code=source_code,
                        package_name=package_name or domain.value,
                    )
                )

        return objects
