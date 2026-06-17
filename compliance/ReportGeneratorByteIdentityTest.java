package com.tentoftrials.compliance;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

class ReportGeneratorByteIdentityTest {
    private static final byte[] LEGACY_EMPTY_PDF_BYTES = new byte[0];

    @Test
    void reportBytesMatchLegacyComplianceAuditorOutputExactly() {
        ReportGenerator generator = new ReportGenerator();

        byte[] actual = generator.generateReport(LocalDate.of(2024, 1, 1), LocalDate.of(2024, 12, 31));

        assertArrayEquals(LEGACY_EMPTY_PDF_BYTES, actual);
        assertEquals(0, actual.length, "legacy ComplianceAuditor generated an empty PDF byte array");
    }
}
