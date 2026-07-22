"""
Generates a small, realistic industrial document corpus for demonstration.

These are SAMPLE DOCUMENTS used as system input - they are ordinary source files
that get ingested, parsed and indexed exactly like a customer's real documents.
They are NOT fabricated system output: nothing here is injected into an answer,
a confidence score, or a conflict report. The platform must discover everything
in them through genuine extraction and retrieval.

The corpus deliberately contains ONE real contradiction (PUMP-101 discharge
pressure is stated as 250 PSI in the OEM manual and 380 PSI in a later revision
notice) so that conflict detection can be demonstrated against a genuine finding.

Usage:  python seed_industrial_corpus.py [output_dir]
"""

import os
import sys
import textwrap

import fitz  # PyMuPDF


DOCUMENTS = {
    "OEM_Manual_PUMP-101_Centrifugal.pdf": """
CENTRIFUGAL PROCESS PUMP - INSTALLATION, OPERATION AND MAINTENANCE MANUAL
Model 3196i / Asset Tag PUMP-101
Document Ref: IOM-3196i-R4    Revision 4    Issued 12/03/2023

1. EQUIPMENT IDENTIFICATION
Asset Tag: PUMP-101
Service: Boiler feedwater transfer, Unit 2
Driver: Motor MTR-441, 75 kW, 2900 RPM
Suction Valve: VALVE-220     Discharge Valve: VALVE-221

2. OPERATING LIMITS
Maximum discharge pressure for PUMP-101 is 250 PSI under continuous duty.
Maximum suction pressure is 45 PSI.
Normal operating speed is 2900 RPM. Do not exceed 3100 RPM.
Maximum bearing housing temperature is 82 CELSIUS.
Minimum continuous stable flow is 120 GPM.

3. MECHANICAL SEAL
PUMP-101 uses a cartridge-type mechanical seal, John Crane Type 5620.
Seal flush plan is API Plan 11. Flush line must be verified clear before start.
Seal face temperature must not exceed 95 CELSIUS during operation.

4. LUBRICATION SCHEDULE
Bearing oil must be changed every 4000 operating hours.
Use ISO VG 68 mineral oil. Oil level must sit at the centre of the sight glass.
Grease-lubricated units require regreasing every 2000 operating hours.

5. STARTUP PROCEDURE
5.1 Confirm VALVE-220 suction valve is fully open.
5.2 Confirm discharge valve VALVE-221 is closed or throttled.
5.3 Prime the casing completely. Running dry will destroy the seal within seconds.
5.4 Start the motor and open VALVE-221 slowly to the duty point.
5.5 Verify discharge pressure stabilises below the 250 PSI maximum.

6. SHUTDOWN PROCEDURE
6.1 Slowly close discharge valve VALVE-221.
6.2 Stop the motor MTR-441.
6.3 Close suction valve VALVE-220 if the pump will be isolated for maintenance.
6.4 Refer to SECTION 9 for lockout requirements before opening the casing.

7. VIBRATION LIMITS
Overall vibration must not exceed 7.1 mm/s RMS at the bearing housings.
An increase above 4.5 mm/s RMS requires investigation within 7 days.

8. SPARE PARTS
Impeller assembly part number 3196-IMP-A.
Mechanical seal cartridge part number JC-5620-50.
Bearing set part number SKF-7310-BECBM.
""",

    "Engineering_Revision_Notice_PUMP-101.pdf": """
ENGINEERING REVISION NOTICE
Document Ref: ERN-2024-0187      Issued 08/07/2024
Supersedes: Operating limits stated in IOM-3196i-R4 Section 2

SUBJECT: Uprated discharge pressure limit for PUMP-101 following impeller change

1. BACKGROUND
PUMP-101 was fitted with a replacement high-head impeller (part 3196-IMP-C)
during the June 2024 outage. The revised hydraulic end permits operation at a
higher discharge pressure than the original equipment rating.

2. REVISED OPERATING LIMIT
Maximum discharge pressure for PUMP-101 is 380 PSI following the impeller change.
This supersedes the 250 PSI figure printed in the OEM manual.
Maximum suction pressure remains unchanged at 45 PSI.
Maximum operating speed remains 3100 RPM.

3. MANDATORY PRECONDITIONS
The uprated limit is valid ONLY where all of the following are satisfied:
3.1 Discharge piping has been re-rated to ANSI Class 300.
3.2 Pressure safety valve PSV-330 has been reset to 400 PSI.
3.3 The casing has passed hydrostatic test at 570 PSI.
3.4 Mechanical seal has been upgraded to cartridge JC-5620-80.

4. WARNING
If any precondition in Section 3 is not met, PUMP-101 must continue to operate
under the original 250 PSI limit. Operating at 380 PSI without the upgraded
seal will cause rapid seal failure and possible loss of containment.

5. DOCUMENT CONTROL
This notice must be read together with IOM-3196i-R4.
The OEM manual has NOT been reissued. Field copies still show 250 PSI.
""",

    "Maintenance_History_Log_Unit2.pdf": """
MAINTENANCE HISTORY LOG - UNIT 2 ROTATING EQUIPMENT
Report Ref: MNT-U2-2024-Q3      Printed 30/09/2024

ENTRY 1
Date: 14/02/2023
Asset: PUMP-101
Work Order: WO-2023-0412
Event: Mechanical seal failed after 11 months in service. Seal faces showed
heavy scoring consistent with dry running. Casing was found partially drained
following a suction valve VALVE-220 closure during the previous shift handover.
Action: Replaced mechanical seal cartridge JC-5620-50. Realigned coupling to
0.05 mm. Reinstated the flush line and verified API Plan 11 flow.
Downtime: 18 hours.

ENTRY 2
Date: 03/08/2023
Asset: PUMP-101
Work Order: WO-2023-1188
Event: Bearing housing temperature reached 91 CELSIUS during a hot ambient
period, exceeding the 82 CELSIUS limit. Oil analysis returned high particulate
count and degraded additive package.
Action: Flushed the bearing reservoir and refilled with ISO VG 68. Replaced the
bearing set SKF-7310-BECBM. Fitted a larger breather. Temperature returned to
74 CELSIUS at full load.
Downtime: 9 hours.

ENTRY 3
Date: 21/06/2024
Asset: PUMP-101
Work Order: WO-2024-0733
Event: Planned outage. High-head impeller upgrade performed under ERN-2024-0187.
Action: Replaced impeller 3196-IMP-A with 3196-IMP-C. Hydrostatic test completed
at 570 PSI and passed. Mechanical seal upgraded to JC-5620-80.
NOTE: Pressure safety valve PSV-330 was NOT reset during this outage. It remains
set at 300 PSI. This is an open action against work order WO-2024-0733.
Downtime: 72 hours.

ENTRY 4
Date: 11/09/2024
Asset: VALVE-221
Work Order: WO-2024-1002
Event: Discharge valve VALVE-221 stem packing leak detected during routine round.
Action: Repacked the valve with graphite packing rings. Leak eliminated.
Downtime: 4 hours.

ENTRY 5
Date: 27/09/2024
Asset: COMP-350
Work Order: WO-2024-1051
Event: Instrument air compressor COMP-350 tripped on high discharge temperature.
Aftercooler was found fouled with scale on the water side.
Action: Chemically cleaned the aftercooler. Discharge temperature returned to
normal at 38 CELSIUS. Compressor returned to service.
Downtime: 6 hours.
""",

    "Safety_Standard_Pressure_Systems.pdf": """
PLANT SAFETY STANDARD - PRESSURE SYSTEM INTEGRITY
Standard Ref: PSS-116      Revision 2      Effective 01/01/2024

1. SCOPE
This standard applies to all pressure-retaining rotating equipment on site,
including centrifugal pumps, compressors and their associated relief devices.

2. RELIEF DEVICE REQUIREMENTS
2.1 Every pressure system must be protected by a relief device sized for the
maximum credible overpressure scenario.
2.2 The relief device set pressure must not exceed 105 percent of the design
pressure of the weakest component in the protected system.
2.3 Where equipment operating limits are uprated, the associated relief device
MUST be reset and re-certified BEFORE the uprated limit is applied in the field.
2.4 Operating equipment above its stated limit while the relief device remains
set for the previous, lower limit is a Category 1 safety violation.

3. INSPECTION INTERVALS
3.1 Pressure safety valves must be bench tested every 24 months.
3.2 Casing thickness surveys are required every 60 months for pumps in
continuous service.
3.3 Hydrostatic testing is required after any modification to a pressure boundary.

4. LOCKOUT AND ISOLATION
4.1 Positive isolation is required before any pressure boundary is opened.
4.2 Isolation valves must be locked and tagged by the responsible technician.
4.3 Stored energy must be relieved and verified at zero before work begins.

5. DOCUMENTATION CONTROL
5.1 Where an engineering revision notice supersedes an OEM manual, BOTH documents
must be available at the point of work.
5.2 Conflicting operating limits between controlled documents must be escalated
to the Plant Engineering Authority before work proceeds.
5.3 The more conservative limit applies until the conflict is formally resolved.

6. COMPETENCY
6.1 Only technicians certified for pressure systems may perform relief device work.
6.2 Certification must be renewed every 36 months.
""",

    "SOP_Pump_Changeover_Unit2.pdf": """
STANDARD OPERATING PROCEDURE - PUMP CHANGEOVER, UNIT 2
SOP Ref: SOP-U2-014      Revision 3      Effective 15/05/2024

1. PURPOSE
To define the controlled changeover between duty pump PUMP-101 and standby
pump PUMP-102 without interrupting boiler feedwater supply.

2. PREREQUISITES
2.1 Both PUMP-101 and PUMP-102 must be available and primed.
2.2 Confirm suction valves VALVE-220 and VALVE-230 are fully open.
2.3 Confirm the standby pump has been rotated within the last 7 days.
2.4 Verify the current approved discharge pressure limit for the duty pump.
Refer to the OEM manual AND any active engineering revision notice.

3. CHANGEOVER SEQUENCE
3.1 Start standby pump PUMP-102 against a closed discharge valve VALVE-231.
3.2 Allow PUMP-102 to reach stable speed of 2900 RPM.
3.3 Slowly open VALVE-231 while throttling VALVE-221 to maintain header pressure.
3.4 Confirm header pressure remains within limits throughout the transfer.
3.5 When PUMP-102 carries full duty, close VALVE-221 completely.
3.6 Stop PUMP-101 and record the changeover in the shift log.

4. POST-CHANGEOVER CHECKS
4.1 Verify PUMP-102 bearing temperature is below 82 CELSIUS after 30 minutes.
4.2 Verify vibration is below 4.5 mm/s RMS.
4.3 Verify no seal leakage is present at either pump.

5. ABNORMAL CONDITIONS
5.1 If header pressure falls below 180 PSI during transfer, abort and restore
PUMP-101 to duty.
5.2 If either pump exceeds its approved discharge pressure limit, trip the pump
immediately and raise a work order.
5.3 If PSV-330 lifts at any point, stop work and notify the shift supervisor.
""",
}


def build_pdf(destination_path: str, body_text: str) -> None:
    """Renders plain text into a simple multi-page A4 PDF with real text layers."""
    document = fitz.open()
    page = document.new_page()
    cursor_y = 60.0
    left_margin = 55.0
    line_height = 12.5
    page_bottom = 780.0

    for raw_line in body_text.strip().split("\n"):
        wrapped_lines = textwrap.wrap(raw_line, width=92) or [""]
        for wrapped in wrapped_lines:
            if cursor_y > page_bottom:
                page = document.new_page()
                cursor_y = 60.0
            page.insert_text(
                (left_margin, cursor_y),
                wrapped,
                fontsize=9.5,
                fontname="helv",
            )
            cursor_y += line_height

    document.save(destination_path)
    document.close()


def main() -> None:
    output_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("sample_corpus")
    os.makedirs(output_dir, exist_ok=True)

    for filename, body in DOCUMENTS.items():
        target = os.path.join(output_dir, filename)
        build_pdf(target, body)
        size_kb = os.path.getsize(target) / 1024
        print(f"  wrote {filename}  ({size_kb:.1f} KB)")

    print(f"\nGenerated {len(DOCUMENTS)} industrial sample documents in '{output_dir}'.")


if __name__ == "__main__":
    main()
