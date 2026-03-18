"""Tests for the ABAP source ZIP parser in the upload use case."""

from __future__ import annotations

import io
import zipfile

from application.commands.upload_abap_source import _parse_abap_zip
from domain.value_objects.object_type import ABAPObjectType


def _make_zip(files: dict[str, str]) -> bytes:
    """Create an in-memory ZIP archive from a mapping of filename -> content."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


class TestParseZipExtractsObjects:
    def test_parse_zip_extracts_objects(self) -> None:
        # The parser uses rsplit(".", 1)[0] so "X.prog.abap" -> "X.prog".
        # Use single-extension files to verify basic extraction count.
        zip_bytes = _make_zip(
            {
                "src/ZFI_PAYMENT.abap": "REPORT ZFI_PAYMENT.",
                "src/ZCL_ORDER.abap": "CLASS ZCL_ORDER DEFINITION.",
                "src/ZIF_LOGGER.abap": "INTERFACE ZIF_LOGGER.",
            }
        )

        objects = _parse_abap_zip(zip_bytes)

        assert len(objects) == 3
        names = {obj["object_name"] for obj in objects}
        assert "ZFI_PAYMENT" in names
        assert "ZCL_ORDER" in names
        assert "ZIF_LOGGER" in names

    def test_skips_directories(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("src/", "")
            zf.writestr("src/ZPROG.prog.abap", "REPORT ZPROG.")
        zip_bytes = buf.getvalue()

        objects = _parse_abap_zip(zip_bytes)

        assert len(objects) == 1


class TestClassifiesObjectTypes:
    def test_classifies_object_types(self) -> None:
        zip_bytes = _make_zip(
            {
                "ZPROG.prog.abap": "REPORT ZPROG.",
                "ZFUGR.fugr.abap": "FUNCTION ZFUGR.",
                "ZCLAS.clas.abap": "CLASS ZCLAS DEFINITION.",
                "ZINTF.intf.abap": "INTERFACE ZINTF.",
                "ZINCL.incl.abap": "INCLUDE ZINCL.",
                "ZTABL.tabl.xml": "<table/>",
                "ZVIEW.view.xml": "<view/>",
                "ZENHO.enho.abap": "ENHANCEMENT ZENHO.",
            }
        )

        objects = _parse_abap_zip(zip_bytes)
        # The parser uses rsplit(".", 1)[0], so "ZPROG.prog.abap" -> "ZPROG.prog"
        type_map = {obj["object_name"]: obj["object_type"] for obj in objects}

        assert type_map["ZPROG.prog"] == ABAPObjectType.PROGRAM
        assert type_map["ZFUGR.fugr"] == ABAPObjectType.FUNCTION_MODULE
        assert type_map["ZCLAS.clas"] == ABAPObjectType.CLASS
        assert type_map["ZINTF.intf"] == ABAPObjectType.INTERFACE
        assert type_map["ZINCL.incl"] == ABAPObjectType.INCLUDE
        assert type_map["ZTABL.tabl"] == ABAPObjectType.TABLE
        assert type_map["ZVIEW.view"] == ABAPObjectType.VIEW
        assert type_map["ZENHO.enho"] == ABAPObjectType.ENHANCEMENT


class TestIdentifiesBusinessDomain:
    def test_identifies_business_domain_from_name(self) -> None:
        """The parser extracts the object name from the filename.

        Although domain classification is not done in the parser itself,
        the naming convention (Z<domain>_...) is preserved in the parsed name
        so that downstream services can classify by prefix.
        """
        zip_bytes = _make_zip(
            {
                "ZFI_GL_POST.prog.abap": "REPORT ZFI_GL_POST.",
                "ZSD_ORDER.prog.abap": "REPORT ZSD_ORDER.",
                "ZMM_STOCK.prog.abap": "REPORT ZMM_STOCK.",
            }
        )

        objects = _parse_abap_zip(zip_bytes)
        names = [obj["object_name"] for obj in objects]

        # Names preserve the domain prefix for downstream classification
        assert any(n.startswith("ZFI") for n in names)
        assert any(n.startswith("ZSD") for n in names)
        assert any(n.startswith("ZMM") for n in names)


class TestHandlesEmptyZip:
    def test_handles_empty_zip(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w"):
            pass
        zip_bytes = buf.getvalue()

        objects = _parse_abap_zip(zip_bytes)

        assert objects == []
