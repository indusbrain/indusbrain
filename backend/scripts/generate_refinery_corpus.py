"""
Generates a realistic Oil & Gas refinery document corpus for IndusBrain.

WHY A REFINERY
--------------
The platform's recognised asset classes (PUMP, COMP, PSV, HX, TK, BLR, MTR,
VALVE, FAN) and its conflict units (PSI, BAR, CELSIUS, RPM, GPM) describe a
continuous process plant. A refinery Crude Distillation Unit is the sharpest fit:

  * Equipment tagging is a formal standard, so asset extraction has real anchors.
  * Nearly every instruction carries a numeric limit, which is what cross-document
    conflict detection compares.
  * Root-cause analysis after failures is mandatory, which is exactly the
    institutional knowledge Organizational Memory is meant to preserve.
  * OSHA PSM and API standards impose preconditions, which the compliance agent
    surfaces.
  * The retiring-expert problem this product targets is acute and well documented
    in this sector.

WHAT IS IN HERE
---------------
These are SAMPLE SOURCE DOCUMENTS - ordinary inputs that get parsed, chunked,
embedded and graphed exactly like a customer's own files. Nothing here is
injected into an answer, a confidence score or a conflict report. Every finding
the platform reports must be discovered by genuine extraction and retrieval.

The corpus contains deliberate, realistic cross-document situations so the
capabilities have something true to find:

  1. A CONTRADICTION - P-101A discharge pressure is 285 PSI in the OEM manual and
     340 PSI in a later revision notice.
  2. AN INCOMPLETE PRECONDITION - the revision requires PSV-1201 to be reset, and
     the maintenance log records that it was NOT done.
  3. A REPEAT FAILURE - P-101A mechanical seals fail twice from the same root
     cause, which only becomes visible by reading two documents together.
  4. A DOCUMENTATION GAP - E-1503 and K-2101 have partial coverage.

Usage:  python scripts/generate_refinery_corpus.py [output_dir]
"""

import os
import sys
import textwrap

import fitz  # PyMuPDF


DOCUMENTS = {
    # ======================================================================
    # MACHINES / EQUIPMENT
    # ======================================================================
    "Machines/OEM_Manual_P-101A_Crude_Charge_Pump.pdf": """
CRUDE CHARGE PUMP - INSTALLATION, OPERATION AND MAINTENANCE MANUAL
Unit 100 Crude Distillation Unit (CDU)
Tag: P-101A          Manufacturer Model: HPX-6x8-13A
Document Ref: IOM-P101A-R6      Revision 6      Issued 04/02/2022

1. EQUIPMENT IDENTIFICATION
Asset Tag: P-101A (duty)   Spare: P-101B (standby)
Service: Crude oil charge from TK-1001 to preheat train E-1501 through E-1504
Driver: Motor MTR-101A, 355 kW, 2 pole, 2975 RPM
Suction isolation: VALVE-1010     Discharge isolation: VALVE-1011
Relief protection: PSV-1201 on the discharge header

2. OPERATING LIMITS
Maximum discharge pressure for P-101A is 285 PSI at rated flow.
Maximum suction pressure is 60 PSI.
Normal operating speed is 2975 RPM. Do not exceed 3100 RPM.
Maximum bearing housing temperature is 80 CELSIUS.
Minimum continuous stable flow is 190 GPM.
Maximum pumped fluid temperature is 150 CELSIUS.

3. MECHANICAL SEAL ARRANGEMENT
P-101A is fitted with a dual pressurised cartridge seal, API Plan 53B.
Barrier fluid pressure must be maintained at least 25 PSI above suction pressure.
Seal face temperature must not exceed 90 CELSIUS during continuous operation.
Loss of barrier pressure will cause process fluid to enter the seal chamber and
destroy the inboard faces within minutes.

4. LUBRICATION
Bearing oil is ISO VG 46 turbine oil. Change every 4000 operating hours.
Oil level must sit at the centre of the constant level oiler sight glass.
Do not mix oil grades. Mixing VG 46 and VG 68 degrades the additive package.

5. STARTUP PROCEDURE
5.1 Confirm suction valve VALVE-1010 is fully open and TK-1001 level is above 30 percent.
5.2 Confirm discharge valve VALVE-1011 is throttled to the minimum flow position.
5.3 Confirm API Plan 53B barrier fluid pressure is established before rotation.
5.4 Prime the casing completely. Running dry destroys the seal within seconds.
5.5 Start motor MTR-101A and open VALVE-1011 slowly to the duty point.
5.6 Verify discharge pressure stabilises below the 285 PSI maximum.

6. VIBRATION LIMITS
Overall vibration must not exceed 7.1 MM/S RMS at the bearing housings.
An increase above 4.5 MM/S RMS requires investigation within 7 days.

7. SPARE PARTS
Impeller assembly part number HPX-IMP-6813A.
Mechanical seal cartridge part number JC-2800-65.
Bearing set part number SKF-7312-BECBM.
""",

    "Machines/Asset_Register_Unit100_CDU.pdf": """
ASSET REGISTER - UNIT 100 CRUDE DISTILLATION UNIT
Register Ref: AR-U100-2024      Revision 11      Issued 15/01/2024

ROTATING EQUIPMENT
P-101A   Crude charge pump, duty. Centrifugal, API 610 OH2. Driver MTR-101A.
P-101B   Crude charge pump, standby. Identical to P-101A. Driver MTR-101B.
P-102A   Reflux pump, duty. Driver MTR-102A, 110 kW.
K-2101   Wet gas compressor. Reciprocating, 2 stage. Driver MTR-2101, 1200 kW.

STATIC EQUIPMENT
E-1501   Crude preheat exchanger, shell and tube. Design 450 PSI at 200 CELSIUS.
E-1502   Crude preheat exchanger, shell and tube. Design 450 PSI at 250 CELSIUS.
E-1503   Crude preheat exchanger, shell and tube. Design 450 PSI at 300 CELSIUS.
TK-1001  Crude feed tank. Floating roof, 45000 cubic metres.
BLR-3001 Steam generation package boiler. 60 tonnes per hour at 600 PSI.

SAFETY DEVICES
PSV-1201 Relief valve protecting the P-101A and P-101B discharge header.
PSV-1202 Relief valve protecting the E-1501 shell side.
PSV-3001 Relief valve protecting the BLR-3001 steam drum.

FLOW CONTROL
VALVE-1010  P-101A suction isolation, 8 inch gate.
VALVE-1011  P-101A discharge isolation, 6 inch gate.
VALVE-1020  P-101B suction isolation, 8 inch gate.
VALVE-1021  P-101B discharge isolation, 6 inch gate.

CRITICALITY
P-101A, K-2101 and BLR-3001 are Criticality 1. Failure stops the unit.
E-1501 through E-1503 are Criticality 2. Failure reduces throughput.
""",

    # ======================================================================
    # ENGINEERING CHANGE  (creates the deliberate contradiction)
    # ======================================================================
    "Machines/Engineering_Revision_Notice_P-101A_Uprate.pdf": """
ENGINEERING REVISION NOTICE
Document Ref: ERN-2024-0342      Issued 12/06/2024
Supersedes: Operating limits in IOM-P101A-R6 Section 2

SUBJECT: Uprated discharge pressure for P-101A following hydraulic end upgrade

1. BACKGROUND
P-101A was fitted with a high-head impeller (HPX-IMP-6813C) during the May 2024
turnaround to support the heavy crude blend. The revised hydraulic end permits a
higher discharge pressure than the original equipment rating.

2. REVISED OPERATING LIMIT
Maximum discharge pressure for P-101A is 340 PSI following the impeller change.
This supersedes the 285 PSI figure printed in the OEM manual.
Maximum suction pressure remains unchanged at 60 PSI.
Maximum operating speed remains 3100 RPM.

3. MANDATORY PRECONDITIONS
The uprated limit is valid ONLY where all of the following are satisfied:
3.1 Discharge piping re-rated to ANSI Class 300 and stamped.
3.2 Relief valve PSV-1201 reset to 375 PSI and re-certified.
3.3 Casing hydrostatic test passed at 510 PSI.
3.4 Mechanical seal upgraded to cartridge JC-2800-90.

4. WARNING
If any precondition in Section 3 is not met, P-101A must continue to operate
under the original 285 PSI limit. Operating at 340 PSI with PSV-1201 still set
at its previous pressure removes the overpressure protection for the discharge
header and can result in loss of containment of hot crude.

5. DOCUMENT CONTROL
This notice must be read together with IOM-P101A-R6.
The OEM manual has NOT been reissued. Field copies still show 285 PSI.
""",

    # ======================================================================
    # FAILURE HISTORY  (repeat failure + the incomplete precondition)
    # ======================================================================
    "Failure_History/Maintenance_History_Log_Unit100.pdf": """
MAINTENANCE HISTORY LOG - UNIT 100 ROTATING EQUIPMENT
Report Ref: MNT-U100-2024-Q3      Printed 30/09/2024

ENTRY 1
Date: 18/03/2023
Asset: P-101A
Work Order: WO-2023-0781
Event: Inboard mechanical seal failed after 9 months in service. Seal faces
showed heavy scoring. Barrier fluid reservoir was found empty and the Plan 53B
pressure alarm had been inhibited on the DCS.
Action: Replaced mechanical seal cartridge JC-2800-65. Refilled barrier reservoir.
Removed the alarm inhibit. Realigned coupling to 0.05 mm.
Downtime: 26 hours.

ENTRY 2
Date: 07/09/2023
Asset: E-1502
Work Order: WO-2023-1544
Event: Tube-side fouling reduced preheat duty. Crude outlet temperature dropped
from 210 CELSIUS to 178 CELSIUS over eight weeks.
Action: Hydroblasted the tube bundle. Duty restored. Recommended shortening the
cleaning interval from 24 months to 18 months.
Downtime: 40 hours.

ENTRY 3
Date: 22/01/2024
Asset: P-101A
Work Order: WO-2024-0112
Event: Inboard mechanical seal failed again after 10 months. Same scoring pattern
as WO-2023-0781. Barrier fluid pressure was found at 8 PSI above suction, below
the 25 PSI minimum required by the seal plan.
Action: Replaced seal cartridge JC-2800-65. Rebuilt the Plan 53B pressure
maintenance system and fitted a local pressure gauge.
NOTE: This is the second identical failure on P-101A. Root cause analysis
RCA-2024-004 was raised.
Downtime: 31 hours.

ENTRY 4
Date: 19/05/2024
Asset: P-101A
Work Order: WO-2024-0655
Event: Planned turnaround. High-head impeller upgrade performed under ERN-2024-0342.
Action: Replaced impeller HPX-IMP-6813A with HPX-IMP-6813C. Casing hydrostatic
test completed at 510 PSI and passed. Mechanical seal upgraded to JC-2800-90.
Discharge piping re-rated to ANSI Class 300 and stamped.
NOTE: Relief valve PSV-1201 was NOT reset during this turnaround. It remains set
at 310 PSI. This is an open action against work order WO-2024-0655.
Downtime: 96 hours.

ENTRY 5
Date: 03/08/2024
Asset: K-2101
Work Order: WO-2024-0980
Event: Wet gas compressor tripped on high second-stage discharge temperature.
Intercooler was found fouled on the cooling water side.
Action: Chemically cleaned the intercooler. Discharge temperature returned to
94 CELSIUS. Compressor returned to service.
Downtime: 14 hours.

ENTRY 6
Date: 11/09/2024
Asset: VALVE-1011
Work Order: WO-2024-1103
Event: Discharge isolation valve stem packing leak found on routine round.
Action: Repacked with graphite rings. Leak eliminated.
Downtime: 5 hours.
""",

    "Failure_History/RCA-2024-004_P-101A_Repeat_Seal_Failure.pdf": """
ROOT CAUSE ANALYSIS REPORT
RCA Ref: RCA-2024-004      Issued 14/02/2024
Asset: P-101A crude charge pump
Trigger: Second identical mechanical seal failure within 11 months

1. EVENT SUMMARY
P-101A suffered inboard mechanical seal failure on 18/03/2023 (WO-2023-0781) and
again on 22/01/2024 (WO-2024-0112). Both failures showed the same scoring pattern
on the inboard faces, indicating process fluid ingress into the seal chamber.

2. IMMEDIATE CAUSE
Loss of API Plan 53B barrier fluid differential pressure. The seal plan requires
barrier pressure to be at least 25 PSI above suction pressure. At the second
failure it was measured at 8 PSI above suction.

3. UNDERLYING CAUSE
The Plan 53B pressure maintenance system had no local indication and no
functioning alarm. The DCS alarm had been inhibited during the 2023 event and the
inhibit was reinstated during a later DCS change without review.

4. ROOT CAUSE
Barrier fluid system integrity was not treated as a critical protective function.
There was no routine verification task for barrier pressure, and alarm inhibits
were not subject to review before reinstatement.

5. CORRECTIVE ACTIONS
5.1 Fit local pressure indication on the Plan 53B system. COMPLETE, WO-2024-0112.
5.2 Add barrier pressure verification to the weekly operator round. COMPLETE.
5.3 Prohibit inhibiting seal-protection alarms without engineering authorisation.
COMPLETE, procedural change to SOP-U100-021.
5.4 Review all Plan 53B installations in Unit 100 for the same weakness. OPEN.

6. LESSON LEARNED
A seal failure repeated because the protective system that prevents it was not
monitored. Where a seal plan defines a minimum differential pressure, that
pressure requires indication, alarm and a routine verification task. Replacing the
seal without restoring the protection guarantees the failure will recur.
""",

    # ======================================================================
    # SAFETY
    # ======================================================================
    "Safety/Lockout_Tagout_SOP.pdf": """
STANDARD OPERATING PROCEDURE - LOCKOUT TAGOUT (LOTO)
SOP Ref: SOP-SAF-002      Revision 5      Effective 01/03/2024

1. SCOPE
Applies to all maintenance on rotating and pressure equipment in Units 100, 2100
and 3000, including P-101A, P-101B, K-2101 and BLR-3001.

2. ISOLATION REQUIREMENTS
2.1 Positive isolation is required before any pressure boundary is opened.
2.2 Double block and bleed is mandatory on hydrocarbon service above 150 CELSIUS.
2.3 Electrical isolation of the driver must be locked at the motor control centre.
2.4 Each technician applies a personal lock. Group locks alone are not acceptable.

3. STORED ENERGY
3.1 Depressurise and verify at zero on a calibrated local gauge.
3.2 Drain and flush hydrocarbon inventory to the closed drain system.
3.3 Allow bearing housings to cool below 45 CELSIUS before handling.
3.4 Barrier fluid systems must be depressurised separately. A Plan 53B reservoir
can retain pressure after the pump is isolated.

4. VERIFICATION
4.1 Attempt to start the equipment from the field station to prove isolation.
4.2 The permit issuer must physically verify each isolation point.
4.3 Record every isolation point on the permit before work begins.

5. RESTORATION
5.1 Remove locks only in reverse order of application.
5.2 Confirm all relief devices are in service and correctly set before restart.
5.3 Confirm no open work orders exist against protective devices for the equipment.
""",

    "Safety/PPE_and_Hot_Work_Guidelines.pdf": """
PERSONAL PROTECTIVE EQUIPMENT AND HOT WORK GUIDELINES
Ref: SAF-PPE-004      Revision 3      Effective 12/11/2023

1. MINIMUM PPE - PROCESS AREAS
Flame resistant coveralls, safety helmet, impact goggles, steel toe boots and
hydrogen sulphide personal monitor are mandatory in all Unit 100 process areas.

2. ADDITIONAL PPE BY TASK
2.1 Opening hydrocarbon lines: chemical splash suit and full face shield.
2.2 Handling hot bearing assemblies: heat resistant gloves rated to 250 CELSIUS.
2.3 High pressure water jetting: operator must wear jetting protection to the
full working pressure of the equipment.
2.4 Confined space entry into TK-1001: supplied air, harness and standby person.

3. HOT WORK
3.1 A hot work permit is required for any spark or flame producing activity.
3.2 Continuous gas testing is mandatory. Work stops at 5 percent LEL.
3.3 A fire watch must remain for 30 minutes after work ends.
3.4 Hot work within 15 metres of TK-1001 requires area supervisor authorisation.

4. HYDROGEN SULPHIDE
4.1 Crude feed to Unit 100 is sour. Assume hydrogen sulphide is present.
4.2 Personal monitors alarm at 5 ppm and evacuate at 10 ppm.
4.3 Escape sets must be carried when working downwind of TK-1001.
""",

    # ======================================================================
    # SOP
    # ======================================================================
    "SOP/SOP-U100-021_Pump_Changeover.pdf": """
STANDARD OPERATING PROCEDURE - CRUDE CHARGE PUMP CHANGEOVER
SOP Ref: SOP-U100-021      Revision 7      Effective 20/02/2024

1. PURPOSE
Controlled changeover between duty pump P-101A and standby pump P-101B without
interrupting crude charge to the preheat train.

2. PREREQUISITES
2.1 Both P-101A and P-101B available and primed.
2.2 Suction valves VALVE-1010 and VALVE-1020 fully open.
2.3 Standby pump rotated within the last 7 days.
2.4 API Plan 53B barrier pressure verified at least 25 PSI above suction on the
pump being started. Do NOT start a pump with low barrier pressure.
2.5 Verify the currently approved discharge pressure limit for the duty pump.
Refer to the OEM manual AND any active engineering revision notice.

3. CHANGEOVER SEQUENCE
3.1 Start standby pump P-101B against throttled discharge valve VALVE-1021.
3.2 Allow P-101B to reach stable speed of 2975 RPM.
3.3 Slowly open VALVE-1021 while throttling VALVE-1011 to hold header pressure.
3.4 Confirm header pressure remains within limits throughout the transfer.
3.5 When P-101B carries full duty, close VALVE-1011 completely.
3.6 Stop P-101A and record the changeover in the shift log.

4. POST-CHANGEOVER CHECKS
4.1 Verify P-101B bearing temperature below 80 CELSIUS after 30 minutes.
4.2 Verify vibration below 4.5 MM/S RMS.
4.3 Verify no seal leakage at either pump.
4.4 Verify barrier fluid differential holds at 25 PSI or above.

5. ABNORMAL CONDITIONS
5.1 If header pressure falls below 220 PSI during transfer, abort and restore
P-101A to duty.
5.2 If either pump exceeds its approved discharge pressure limit, trip the pump
immediately and raise a work order.
5.3 If PSV-1201 lifts at any point, stop work and notify the shift supervisor.
5.4 Alarms protecting the mechanical seal must NOT be inhibited to complete a
changeover. See RCA-2024-004.
""",

    "SOP/SOP-U100-005_Unit_Startup.pdf": """
STANDARD OPERATING PROCEDURE - UNIT 100 COLD STARTUP
SOP Ref: SOP-U100-005      Revision 4      Effective 08/01/2024

1. PURPOSE
Bring the Crude Distillation Unit from a fully shut down state to stable crude
throughput.

2. PRE-STARTUP SAFETY REVIEW
2.1 All work orders on Criticality 1 equipment must be closed.
2.2 All relief devices must be in service and correctly set. Confirm PSV-1201,
PSV-1202 and PSV-3001 certification is current.
2.3 No open actions may remain against any protective device.
2.4 Confirm the approved operating limits for P-101A, including any active
engineering revision notice.

3. UTILITIES
3.1 Establish instrument air and confirm K-2101 is available.
3.2 Establish steam from BLR-3001 and warm the unit at no more than 30 CELSIUS
per hour to avoid thermal shock to E-1501 through E-1503.
3.3 Establish cooling water and confirm return temperature below 45 CELSIUS.

4. CRUDE CIRCULATION
4.1 Confirm TK-1001 level above 30 percent.
4.2 Establish API Plan 53B barrier pressure on P-101A before rotation.
4.3 Start P-101A per SOP-U100-021 Section 3.
4.4 Circulate on total reflux until column bottom reaches 180 CELSIUS.
4.5 Increase charge rate in 10 percent steps, holding 30 minutes at each step.

5. HOLD POINTS
5.1 Do not exceed 250 CELSIUS at the E-1503 outlet until the preheat train has
been at temperature for two hours.
5.2 Do not increase charge rate above 70 percent until column pressure is stable.
5.3 Any relief valve lift requires a full stop and engineering review.
""",

    # ======================================================================
    # MAINTENANCE
    # ======================================================================
    "Maintenance/Preventive_Maintenance_Schedule_Unit100.pdf": """
PREVENTIVE MAINTENANCE SCHEDULE - UNIT 100
Ref: PM-U100-2024      Revision 6      Effective 01/04/2024

WEEKLY
P-101A / P-101B  Verify API Plan 53B barrier fluid differential is at least 25 PSI
above suction. Record the value. Raise a work order if below.
P-101A / P-101B  Record bearing housing temperature and overall vibration.
K-2101           Check intercooler cooling water outlet temperature.

MONTHLY
P-101A / P-101B  Rotate the standby pump for 30 minutes at duty conditions.
VALVE-1011       Stroke check and visual inspection of stem packing.
BLR-3001         Blowdown and water chemistry verification.

QUARTERLY
E-1501 to E-1503 Record approach temperature and trend fouling.
K-2101           Valve condition check and cylinder lubrication rate audit.

ANNUAL
P-101A / P-101B  Bearing oil change. ISO VG 46 turbine oil. Do not mix grades.
PSV-1201         Bench test and re-certify. Interval 24 months maximum.
PSV-1202         Bench test and re-certify. Interval 24 months maximum.

TURNAROUND
E-1501 to E-1503 Tube bundle cleaning. Interval reduced from 24 to 18 months
following WO-2023-1544.
P-101A           Casing thickness survey and full seal overhaul.

NOTE ON CRITICAL PROTECTION
Barrier fluid verification is a protective task, not a routine check. It was
introduced as corrective action 5.2 of RCA-2024-004 after two repeat seal
failures on P-101A. It must not be deferred.
""",

    # ======================================================================
    # INSPECTION
    # ======================================================================
    "Inspection/Relief_Valve_Certification_Register.pdf": """
RELIEF VALVE CERTIFICATION REGISTER - UNIT 100
Register Ref: INS-PSV-2024      Printed 30/09/2024

PSV-1201
Protects: P-101A / P-101B discharge header
Current set pressure: 310 PSI
Last bench test: 14/06/2023
Next due: 14/06/2025
Status: IN SERVICE
Remark: ERN-2024-0342 requires this valve to be reset to 375 PSI before P-101A
operates at the uprated 340 PSI limit. Reset has NOT been performed. Open action
against WO-2024-0655.

PSV-1202
Protects: E-1501 shell side
Current set pressure: 450 PSI
Last bench test: 02/11/2023
Next due: 02/11/2025
Status: IN SERVICE

PSV-3001
Protects: BLR-3001 steam drum
Current set pressure: 660 PSI
Last bench test: 21/03/2024
Next due: 21/03/2026
Status: IN SERVICE

REGISTER NOTES
A relief device must be re-certified after any change to the set pressure.
Equipment must not operate above the pressure its relief device protects.
""",

    "Inspection/Turnaround_Inspection_Report_2024.pdf": """
TURNAROUND INSPECTION REPORT - MAY 2024
Report Ref: INS-TA-2024-05      Issued 28/05/2024

1. SCOPE
Inspection of Unit 100 pressure equipment and rotating machinery during the
May 2024 turnaround.

2. P-101A
Casing thickness survey completed. Minimum measured wall 11.4 mm against a
retirement limit of 9.5 mm. Acceptable for the next interval.
Hydrostatic test performed at 510 PSI. Passed with no visible deformation.
Impeller replaced with HPX-IMP-6813C under ERN-2024-0342.
Mechanical seal upgraded to JC-2800-90.

3. E-1501
Tube bundle inspected. Light scale on the tube side. No tube plugging required.

4. E-1503
Tube bundle inspected. Moderate fouling on the shell side. Cleaned.
NOTE: No thickness survey was performed on E-1503 during this turnaround. The
last recorded survey for E-1503 is dated 2019. A survey is outstanding.

5. K-2101
Cylinder bores measured within tolerance. Valve plates replaced on both stages.

6. OUTSTANDING ITEMS
6.1 PSV-1201 reset to 375 PSI. NOT COMPLETED.
6.2 E-1503 thickness survey. NOT COMPLETED.
""",

    # ======================================================================
    # COMPLIANCE
    # ======================================================================
    "Compliance/Pressure_System_Integrity_Standard.pdf": """
PLANT SAFETY STANDARD - PRESSURE SYSTEM INTEGRITY
Standard Ref: PSS-116      Revision 3      Effective 01/01/2024
Aligned to: OSHA 1910.119 Process Safety Management, API RP 520, API RP 576

1. SCOPE
Applies to all pressure retaining equipment in Units 100, 2100 and 3000.

2. RELIEF DEVICE REQUIREMENTS
2.1 Every pressure system must be protected by a relief device sized for the
maximum credible overpressure scenario.
2.2 The relief device set pressure must not exceed 105 percent of the design
pressure of the weakest component in the protected system.
2.3 Where equipment operating limits are uprated, the associated relief device
MUST be reset and re-certified BEFORE the uprated limit is applied in the field.
2.4 Operating equipment above its stated limit while the relief device remains
set for the previous, lower limit is a Category 1 process safety violation.

3. INSPECTION INTERVALS
3.1 Relief valves must be bench tested every 24 months.
3.2 Casing and shell thickness surveys are required every 60 months for equipment
in continuous hydrocarbon service.
3.3 Hydrostatic testing is required after any modification to a pressure boundary.

4. MANAGEMENT OF CHANGE
4.1 Any change to an operating limit requires a documented engineering revision
notice and a pre-startup safety review.
4.2 Where an engineering revision notice supersedes an OEM manual, BOTH documents
must be available at the point of work.
4.3 Conflicting operating limits between controlled documents must be escalated to
the Plant Engineering Authority before work proceeds.
4.4 The more conservative limit applies until the conflict is formally resolved.

5. PROTECTIVE FUNCTION INTEGRITY
5.1 Alarms and trips protecting equipment from damage are protective functions.
5.2 Inhibiting a protective function requires engineering authorisation and a
documented time limit.
5.3 Reinstating an inhibit during a control system change requires the same
authorisation as the original inhibit.

6. COMPETENCY
6.1 Only technicians certified for pressure systems may perform relief device work.
6.2 Certification must be renewed every 36 months.
""",
}


def build_pdf(destination_path: str, body_text: str) -> None:
    """Renders plain text into a multi-page A4 PDF with a real text layer."""
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
            page.insert_text((left_margin, cursor_y), wrapped, fontsize=9.5, fontname="helv")
            cursor_y += line_height

    document.save(destination_path)
    document.close()


def main() -> None:
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "refinery_corpus"

    for relative_path, body in DOCUMENTS.items():
        target = os.path.join(output_dir, relative_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        build_pdf(target, body)
        print(f"  {relative_path}  ({os.path.getsize(target) / 1024:.1f} KB)")

    print(f"\nGenerated {len(DOCUMENTS)} refinery documents in '{output_dir}'.")
    print("\nDeliberate situations for the platform to discover:")
    print("  - P-101A discharge pressure: 285 PSI (OEM) vs 340 PSI (ERN-2024-0342)")
    print("  - PSV-1201 reset required by the ERN, recorded as NOT DONE in two documents")
    print("  - P-101A seal failed twice from the same root cause (WO-2023-0781, WO-2024-0112)")
    print("  - E-1503 thickness survey outstanding since 2019")


if __name__ == "__main__":
    main()
