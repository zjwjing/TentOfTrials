package com.tentoftrials.compliance;

import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class RuleEngineTest {
    private final RuleEngine engine = new RuleEngine();

    @Test
    void kycFailsForPendingPepWithByteIdenticalLegacyMessages() {
        Map<String, Object> data = new HashMap<>();
        data.put("user_id", "user-123");
        data.put("kyc_status", "pending");
        data.put("is_pep", true);

        ComplianceAuditor.ComplianceResult result = engine.audit("KYC", data);

        assertFalse(result.isCompliant());
        assertEquals(
            List.of(
                "User user-123 has not completed KYC. What the fuck?",
                "Fuck, they're a PEP. Enhanced due diligence required."
            ),
            List.copyOf(result.getViolations())
        );
        assertEquals(
            "KYC check failed: User user-123 has not completed KYC. What the fuck?; Fuck, they're a PEP. Enhanced due diligence required.",
            result.getSummary()
        );
    }

    @Test
    void amlFlagsAmountsAboveLegacyThreshold() {
        Map<String, Object> data = Map.of("transaction_amount", 10000.01);

        ComplianceAuditor.ComplianceResult result = engine.audit("AML", data);

        assertFalse(result.isCompliant());
        assertEquals(List.of("Transaction exceeds AML threshold of $10000.0"), List.copyOf(result.getViolations()));
        assertEquals("AML flagged: Transaction exceeds AML threshold of $10000.0", result.getSummary());
    }

    @Test
    void unknownCheckTypeStillAssumesCompliance() {
        ComplianceAuditor.ComplianceResult result = engine.audit("SOME_NEW_REGULATOR_THING", Collections.emptyMap());

        assertTrue(result.isCompliant());
        assertTrue(result.getViolations().isEmpty());
        assertEquals("Unknown check type: assuming compliant", result.getSummary());
    }
}
