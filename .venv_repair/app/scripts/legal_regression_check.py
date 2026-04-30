from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Iterable

# Allow running directly from repository root without package install.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.legal_lookup import search_entries


@dataclass(frozen=True)
class Case:
    query: str
    expected_any: tuple[str, ...]
    forbidden: tuple[str, ...] = ()
    source: str = "ALL"


TUNING_CASES_PATH = ROOT / "app" / "data" / "legal" / "legal_tuning_cases.jsonl"


CASES: tuple[Case, ...] = (
    Case("65 in a 25", ("OCGA 40-6-181",), ("OCGA 16-10-20",)),
    Case("sex in public", ("OCGA 16-6-8",), ("OCGA 16-6-1", "Article 120")),
    Case("indecent exposure", ("OCGA 16-6-8",), ("OCGA 16-6-1",)),
    Case("husband raped his wife", ("OCGA 16-6-1", "Article 120")),
    Case("home owner had the car stolen", ("OCGA 16-8-2",), ("OCGA 40-6-48",)),
    Case("dui refusal", ("OCGA 40-6-391", "OCGA 40-5-67.1", "OCGA 40-6-392")),
    Case(
        "driver was weaving and refused breath test",
        ("OCGA 40-6-391", "OCGA 40-5-67.1", "OCGA 40-6-392", "OCGA 40-6-48"),
    ),
    Case(
        "driver was weaving and refused breath test and ran stop sign",
        ("OCGA 40-6-391", "OCGA 40-6-48", "OCGA 40-6-72"),
    ),
    Case("awol", ("Article 86",)),
    Case("disrespect to officer", ("Article 89", "Article 91")),
    Case("mclb traffic court", ("MCLBAO 5560.9G CH6",)),
    Case("texting while driving", ("OCGA 40-6-241",)),
    Case("felon in possession of a firearm", ("OCGA 16-11-131",)),
    Case("drug trafficking", ("OCGA 16-13-31",)),
    Case("possession of methamphetamine", ("OCGA 16-13-30", "OCGA 16-13-58"), ("OCGA 40-6-241",)),
    Case("sold cocaine near a school", ("OCGA 16-13-30", "OCGA 16-13-30.1"), ("OCGA 40-6-48",)),
    Case("fake pills being sold", ("OCGA 16-13-32.4", "OCGA 16-13-32.5"), ("OCGA 40-6-181",)),
    Case("used a child to run narcotics", ("OCGA 16-13-30.3",), ("OCGA 40-6-241",)),
    Case("drug pipe with residue", ("OCGA 16-13-32.2",), ("OCGA 40-6-72",)),
    Case("forged prescription for oxycodone", ("OCGA 16-13-33", "OCGA 16-13-33.1"), ("OCGA 40-5-20",)),
    Case("possession of prescription pills", ("OCGA 16-13-30", "OCGA 16-13-58"), ("OCGA 16-13-37", "OCGA 16-13-33", "OCGA 16-13-33.1")),
    Case("posassion of prescription pills", ("OCGA 16-13-30", "OCGA 16-13-58"), ("OCGA 16-13-37", "OCGA 16-13-33", "OCGA 16-13-33.1")),
    Case("posession of prescription pills", ("OCGA 16-13-30", "OCGA 16-13-58"), ("OCGA 16-13-37", "OCGA 16-13-33", "OCGA 16-13-33.1")),
    Case("possession of controlled substance", ("OCGA 16-13-30",), ("OCGA 16-13-37",)),
    Case("meth lab precursor chemicals", ("OCGA 16-13-45",), ("OCGA 40-6-49",)),
    Case("doctor writing unlawful narcotic scripts", ("OCGA 16-13-39",), ("OCGA 40-6-20",)),
    Case("possession of marijuana", ("OCGA 16-13-75", "OCGA 16-13-30", "OCGA 16-13-71")),
    Case("possion of marjauana", ("OCGA 16-13-75", "OCGA 16-13-30", "OCGA 16-13-71")),
    Case("marijuana", ("OCGA 16-13-75", "OCGA 16-13-30", "OCGA 16-13-71")),
    Case("marine used cocaine", ("Article 112a",)),
    Case("service member drug use", ("Article 112a",)),
    Case("introduced drugs on base", ("Article 112a",)),
    Case("high on duty", ("Article 112", "Article 112a")),
    Case("shoplifting from store", ("OCGA 16-8-14",)),
    Case("stealing from the store", ("OCGA 16-8-14", "OCGA 16-8-2"), ("OCGA 16-5-40",)),
    Case("stealing from the store and then resisted officer", ("OCGA 16-8-14", "OCGA 16-10-24"), ("OCGA 16-5-40",)),
    Case("retail theft", ("OCGA 16-8-14", "OCGA 16-8-2"), ("OCGA 16-5-40",)),
    Case("stole merchandise from store", ("OCGA 16-8-14", "OCGA 16-8-2"), ("OCGA 16-5-40",)),
    Case("armed robbery with gun", ("OCGA 16-8-41",)),
    Case("driver ran red light", ("OCGA 40-6-20",)),
    Case("following too close", ("OCGA 40-6-49",)),
    Case("no turn signal lane change", ("OCGA 40-6-123",)),
    Case("suspended license traffic stop", ("OCGA 40-5-121",)),
    Case("no valid license", ("OCGA 40-5-20",)),
    Case("parking in handicap without sticker", ("OCGA 40-6-221",)),
    Case("ran stop sign", ("OCGA 40-6-20", "OCGA 40-6-72")),
    Case("homeowner says vehicle was taken overnight", ("OCGA 16-8-2",)),
    Case("public sex in parking lot", ("OCGA 16-6-8",), ("OCGA 16-6-1",)),
    Case("streaking", ("OCGA 16-6-8",), ("OCGA 16-6-1",)),
    Case("wife reports husband forced sex", ("OCGA 16-6-1", "Article 120")),
    Case("base speed limit mclb", ("MCLBAO 5560.9G CH3-11",)),
    Case("mclb seat belt violation", ("MCLBAO 5560.9G CH3-18",)),
    Case("fleeing and eluding police", ("OCGA 40-6-395",)),
    Case("obstruction pulled away from officer", ("OCGA 16-10-24",)),
    Case("false name to officer", ("OCGA 16-10-25",)),
    Case("parking in hancicap without sticker", ("OCGA 40-6-221",)),
    Case("disrepect to officer", ("Article 89", "Article 91")),
    Case("felonn in posession of wepon", ("OCGA 16-11-131",)),
    Case("he slapped her during an argument", ("OCGA 16-5-23", "OCGA 16-5-20")),
    Case("pushed spouse during domestic argument", ("OCGA 16-5-23", "OCGA 16-5-23.1")),
    Case("simple assault no injury", ("OCGA 16-5-20",)),
    Case("marine disobeyed direct order", ("Article 92",)),
    Case("refused lawful command", ("Article 92", "Article 91")),
    Case("drunk in barracks and fighting", ("Article 112", "Article 128")),
    Case("shoplifting from px", ("OCGA 16-8-14", "OCGA 16-8-2")),
    Case("weed found in vehicle", ("OCGA 16-13-75", "OCGA 16-13-30")),
    Case("drove on base while intoxicated", ("MCLBAO 5560.9G CH3-11", "MCLBAO 5560.9G CH6")),
    Case("false statement to police", ("OCGA 16-10-20",), ("OCGA 40-6-48",)),
    Case("trespassing after being told to leave", ("OCGA 16-7-21",), ("OCGA 40-6-48",)),
    Case("federal felon in possession", ("18 USC 922(g)",)),
    Case("stole government property", ("18 USC 641",)),
    Case("damaged government property", ("18 USC 1361",)),
    Case("wire fraud over interstate communications", ("18 USC 1343",)),
    Case("identity theft with stolen ids", ("18 USC 1028", "18 USC 1028A")),
    Case("mail theft from mailbox", ("18 USC 1708",)),
    Case("threat sent across state lines", ("18 USC 875(c)",)),
    Case("unauthorized access to government computer", ("18 USC 1030",)),
    Case("counterfeit money passed at store", ("18 USC 471",)),
    Case("firearm in federal facility", ("18 USC 930",)),
    Case("service member stole government property on base", ("18 USC 641", "Article 121")),
    Case("driver on base drunk and speeding 65 in a 25", ("MCLBAO 5560.9G CH3-11", "OCGA 40-6-181", "OCGA 40-6-391")),
    Case("barred from base and came back", ("18 USC 1382",)),
    Case("subject refused lawful order", ("Article 92", "Article 91")),
    Case("weed in vehicle on base", ("OCGA 16-13-75", "OCGA 16-13-30", "MCLBAO 5560.9G CH3-11")),
    Case("pushed spouse during argument", ("OCGA 16-5-23", "OCGA 16-5-23.1")),
    Case("fake id", ("18 USC 1028",)),
    Case("gave false name to police", ("OCGA 16-10-25",)),
    Case("entered room without permission", ("OCGA 16-7-21", "OCGA 16-7-22", "18 USC 1382")),
    Case("threatened by text", ("18 USC 2261A", "OCGA 16-5-102")),
    Case("drunk in barracks", ("Article 112",)),
    Case("suspicious person in restricted area", ("18 USC 1382",)),
)


def _codes(results) -> list[str]:
    return [item.entry.code for item in results]


def _load_tuning_cases() -> tuple[Case, ...]:
    if not TUNING_CASES_PATH.exists():
        return ()
    loaded: list[Case] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    with TUNING_CASES_PATH.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            query = str(payload.get("query") or "").strip()
            if not query:
                continue
            source = str(payload.get("source") or "ALL").strip().upper()
            if source not in {"ALL", "GEORGIA", "UCMJ", "BASE_ORDER", "FEDERAL_USC"}:
                source = "ALL"
            expected_raw = payload.get("expected_codes")
            if isinstance(expected_raw, list):
                expected = tuple(str(item).strip() for item in expected_raw if str(item).strip())
            else:
                expected = ()
            if not expected:
                continue
            dedupe_key = (query.lower(), source, expected)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            loaded.append(Case(query=query, expected_any=expected, source=source))
    return tuple(loaded)


def run_cases(cases: Iterable[Case]) -> int:
    failures = 0
    for case in cases:
        results = search_entries(case.query, case.source)
        codes = _codes(results)
        missing = [code for code in case.expected_any if code not in codes]
        present_forbidden = [code for code in case.forbidden if code in codes]
        if missing or present_forbidden:
            failures += 1
            print(f"\nFAIL: {case.query}")
            print(f"  got: {codes[:8]}")
            if missing:
                print(f"  missing expected: {missing}")
            if present_forbidden:
                print(f"  contained forbidden: {present_forbidden}")
        else:
            print(f"PASS: {case.query} -> {codes[:5]}")
    return failures


def main() -> int:
    tuning_cases = _load_tuning_cases()
    all_cases = CASES + tuning_cases
    failures = run_cases(all_cases)
    print(
        f"\nTotal cases: {len(all_cases)} (static={len(CASES)}, tuning={len(tuning_cases)}) | failures: {failures}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
