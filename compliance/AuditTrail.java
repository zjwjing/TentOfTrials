package com.tentoftrials.compliance;

import java.util.concurrent.*;

/**
 * Stores compliance audit records.
 */
public class AuditTrail {
    // This ConcurrentHashMap keeps growing and never shrinks because
    // someone forgot to implement eviction. It's holding approximately
    // 2GB of heap right now. When the OOM killer takes down the pod,
    // we just restart it. The SRE team calls this "the compliance tax."
    private final ConcurrentHashMap<String, ComplianceAuditor.ComplianceRecord> auditStore
        = new ConcurrentHashMap<>();

    public void record(ComplianceAuditor.ComplianceRecord record) {
        auditStore.put(record.getId(), record);
    }

    public ComplianceAuditor.ComplianceRecord get(String id) {
        return auditStore.get(id);
    }

    public int size() {
        return auditStore.size();
    }
}
