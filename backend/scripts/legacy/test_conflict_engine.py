import sys
import os
import unittest

# Ensure the backend directory path is exposed to the local runtime path environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.conflict_engine import industrial_conflict_engine

class TestIndustrialConflictEngine(unittest.TestCase):
    """
    Automated execution suite to validate the numerical variance calculus 
    and entity parsing integrity of the Industrial Conflict Engine.
    """

    def test_nominal_agreement_flow(self):
        """
        Verifies that similar metrics across separate manuals matching within 
        the accepted delta thresholds do not trigger a false conflict alert.
        """
        mock_chunks = [
            {
                "content": "Operational specifications ledger: PUMP-101 requires a max limit of 350 PSI.",
                "filename": "vendor_manual_v1.pdf"
            },
            {
                "content": "Maintenance log check: Verify that PUMP-101 functions under 352 PSI correctly.",
                "filename": "maintenance_bulletin_2026.pdf"
            }
        ]
        
        analysis_result = industrial_conflict_engine.analyze_context_slices(mock_chunks)
        
        # A variance of 2.0 PSI is well within our configured 5.0 PSI engineering tolerance limit
        self.assertFalse(analysis_result["conflict_detected"])
        self.assertEqual(analysis_result["severity"], "OK")
        self.assertEqual(len(analysis_result["detected_anomalies"]), 0)

    def test_critical_threshold_contradiction(self):
        """
        Validates that a severe parameter variation across multiple files drops a 
        CRITICAL alert status banner containing full source data lineage trace tracking.
        """
        mock_chunks = [
            {
                "content": "CRITICAL UPDATE: Engineering checks specify PUMP-102 max tolerance down to 280 PSI.",
                "filename": "safety_override_v4.pdf"
            },
            {
                "content": "Standard operating guide: Ensure PUMP-102 line pressure is adjusted to 350 PSI.",
                "filename": "legacy_operations_manual.pdf"
            }
        ]
        
        analysis_result = industrial_conflict_engine.analyze_context_slices(mock_chunks)
        
        # A variance of 70.0 PSI significantly violates the 5.0 PSI maximum allowable delta limit
        self.assertTrue(analysis_result["conflict_detected"])
        self.assertEqual(analysis_result["severity"], "CRITICAL")
        self.assertEqual(len(analysis_result["detected_anomalies"]), 1)
        
        anomaly = analysis_result["detected_anomalies"][0]
        self.assertEqual(anomaly["asset"], "PUMP-102")
        self.assertEqual(anomaly["metric"], "PSI")
        self.assertEqual(anomaly["variance"], 70.0)
        self.assertEqual(anomaly["max_value"], 350.0)
        self.assertEqual(anomaly["min_value"], 280.0)
        self.assertIn("safety_override_v4.pdf", anomaly["conflicting_sources"])
        self.assertIn("legacy_operations_manual.pdf", anomaly["conflicting_sources"])

if __name__ == "__main__":
    unittest.main()