"""Business Partner consolidation service — pure domain logic.

Detects Customer/Vendor records that must be merged for the
S/4HANA Business Partner model.
"""

from __future__ import annotations

from domain.value_objects.data_quality import BPConsolidationResult


class BPConsolidationService:
    """Assesses BP consolidation readiness by matching customers against vendors."""

    def assess_consolidation(
        self,
        customer_records: list[dict],
        vendor_records: list[dict],
    ) -> BPConsolidationResult:
        """Match customer and vendor records to identify merge candidates.

        Matching criteria (in priority order):
        1. Exact tax_id match (highest confidence)
        2. Name similarity with address match
        """
        merge_candidates: list[tuple[str, str]] = []

        # Build vendor lookup indexes
        vendor_by_tax_id: dict[str, list[dict]] = {}
        for vendor in vendor_records:
            tax_id = self._normalise_tax_id(vendor.get("tax_id", ""))
            if tax_id:
                vendor_by_tax_id.setdefault(tax_id, []).append(vendor)

        matched_vendor_ids: set[str] = set()

        # Pass 1: Match on tax_id
        for customer in customer_records:
            cust_tax_id = self._normalise_tax_id(customer.get("tax_id", ""))
            if not cust_tax_id:
                continue

            matching_vendors = vendor_by_tax_id.get(cust_tax_id, [])
            for vendor in matching_vendors:
                vendor_id = vendor.get("id", vendor.get("vendor_id", ""))
                if vendor_id in matched_vendor_ids:
                    continue
                customer_id = customer.get("id", customer.get("customer_id", ""))
                merge_candidates.append((customer_id, vendor_id))
                matched_vendor_ids.add(vendor_id)

        # Pass 2: Name + address similarity for unmatched vendors
        unmatched_vendors = [v for v in vendor_records if v.get("id", v.get("vendor_id", "")) not in matched_vendor_ids]

        for customer in customer_records:
            cust_name = self._normalise_name(customer.get("name", ""))
            cust_addr = self._normalise_address(customer.get("address", ""))
            if not cust_name:
                continue

            for vendor in unmatched_vendors:
                vendor_id = vendor.get("id", vendor.get("vendor_id", ""))
                if vendor_id in matched_vendor_ids:
                    continue

                vendor_name = self._normalise_name(vendor.get("name", ""))
                vendor_addr = self._normalise_address(vendor.get("address", ""))

                if vendor_name and self._names_match(cust_name, vendor_name):
                    if cust_addr and vendor_addr and self._addresses_match(cust_addr, vendor_addr):
                        customer_id = customer.get("id", customer.get("customer_id", ""))
                        merge_candidates.append((customer_id, vendor_id))
                        matched_vendor_ids.add(vendor_id)

        # Determine complexity
        duplicate_pairs = len(merge_candidates)
        total_records = len(customer_records) + len(vendor_records)

        if total_records == 0:
            complexity = "LOW"
        else:
            ratio = duplicate_pairs / total_records
            if ratio <= 0.05:
                complexity = "LOW"
            elif ratio <= 0.20:
                complexity = "MEDIUM"
            else:
                complexity = "HIGH"

        return BPConsolidationResult(
            customer_count=len(customer_records),
            vendor_count=len(vendor_records),
            duplicate_pairs=duplicate_pairs,
            merge_candidates=tuple(merge_candidates),
            consolidation_complexity=complexity,
        )

    @staticmethod
    def _normalise_tax_id(tax_id: str) -> str:
        """Strip whitespace, dashes, dots from tax ID for comparison."""
        return tax_id.strip().replace("-", "").replace(".", "").replace(" ", "").upper()

    @staticmethod
    def _normalise_name(name: str) -> str:
        """Normalise company name for fuzzy comparison."""
        return name.strip().lower()

    @staticmethod
    def _normalise_address(address: str) -> str:
        """Normalise address for comparison."""
        return address.strip().lower()

    @staticmethod
    def _names_match(name_a: str, name_b: str) -> bool:
        """Simple name similarity: exact match or one contains the other."""
        if name_a == name_b:
            return True
        # Check if one name is a substantial substring of the other
        if len(name_a) >= 4 and len(name_b) >= 4:
            if name_a in name_b or name_b in name_a:
                return True
        return False

    @staticmethod
    def _addresses_match(addr_a: str, addr_b: str) -> bool:
        """Simple address comparison."""
        return addr_a == addr_b
