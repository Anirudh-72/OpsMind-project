/**
 * OpsMind — Core Application Controller (Phase 2 Full Workspace Workflow)
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM References
  const statusBadge = document.getElementById("system-status-badge");
  const scenarioSelect = document.getElementById("scenario-select");
  const scenarioTag = document.getElementById("scenario-tag");
  const btnReset = document.getElementById("btn-reset");

  const incidentForm = document.getElementById("incident-form");
  const titleInput = document.getElementById("incident-title");
  const serviceInput = document.getElementById("incident-service");
  const severitySelect = document.getElementById("incident-severity");
  const descInput = document.getElementById("incident-desc");
  const logInput = document.getElementById("incident-log");
  const formErrorBanner = document.getElementById("form-error-banner");
  const btnInvestigate = document.getElementById("btn-investigate");
  const investigateSpinner = document.getElementById("investigate-spinner");

  const titleCount = document.getElementById("title-count");
  const descCount = document.getElementById("desc-count");

  const resultsEmptyState = document.getElementById("results-empty-state");
  const resultsLoadingState = document.getElementById("results-loading-state");
  const resultsContent = document.getElementById("results-content");
  const resultsProvenanceTags = document.getElementById("results-provenance-tags");

  const resSummary = document.getElementById("res-summary");
  const resPastIncidents = document.getElementById("res-past-incidents");
  const resHistorySuggests = document.getElementById("res-history-suggests");
  const resDiagnosticChecks = document.getElementById("res-diagnostic-checks");
  const resDifferences = document.getElementById("res-differences");
  const resNextStep = document.getElementById("res-next-step");

  const memoryCountBadge = document.getElementById("memory-count-badge");
  const memoryEmptyState = document.getElementById("memory-empty-state");
  const memoryList = document.getElementById("memory-list");

  const outcomeForm = document.getElementById("outcome-form");
  const outcomeService = document.getElementById("outcome-service");
  const outcomeCause = document.getElementById("outcome-cause");
  const outcomeFix = document.getElementById("outcome-fix");
  const outcomeStatus = document.getElementById("outcome-status");
  const outcomeNotes = document.getElementById("outcome-notes");
  const outcomeNotice = document.getElementById("outcome-notice");
  const btnSeedMemory = document.getElementById("btn-seed-memory");
  const btnPrefillOutcome = document.getElementById("btn-prefill-outcome");

  const traceLog = document.getElementById("trace-log");

  // State
  let scenariosCache = {};

  // Helper: Format Time for Trace
  function getTimestamp() {
    const d = new Date();
    return d.toTimeString().split(" ")[0];
  }

  // Helper: Add Line to Execution Trace
  function addTrace(stage, message, type = "info") {
    const line = document.createElement("div");
    line.className = "trace-line";

    const timeSpan = document.createElement("span");
    timeSpan.className = "trace-time";
    timeSpan.textContent = getTimestamp();

    const stageSpan = document.createElement("span");
    stageSpan.className = "trace-stage";
    stageSpan.textContent = `[${stage}]`;

    const msgSpan = document.createElement("span");
    msgSpan.className = type === "success" ? "trace-success" : "trace-info";
    msgSpan.textContent = message;

    line.appendChild(timeSpan);
    line.appendChild(stageSpan);
    line.appendChild(msgSpan);

    traceLog.appendChild(line);
    traceLog.scrollTop = traceLog.scrollHeight;
  }

  // 1. Initial Health Check
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const health = await res.json();

      if (health.hindsight && health.hindsight.configured) {
        statusBadge.className = "badge badge-ok";
        statusBadge.textContent = "Hindsight: Live Cloud";
        addTrace("SYSTEM", `Hindsight connected to Cloud (${health.hindsight.bank_id})`, "success");
      } else {
        statusBadge.className = "badge badge-warning";
        statusBadge.textContent = "Hindsight: Simulation Mode";
        addTrace("SYSTEM", "Hindsight running in local simulation mode (no API key configured)", "info");
      }
    } catch (err) {
      statusBadge.className = "badge badge-error";
      statusBadge.textContent = "Offline";
      addTrace("ERROR", `Health check failed: ${err.message}`, "error");
    }
  }

  // 2. Fetch and Populate Sample Scenarios
  async function loadScenarios() {
    try {
      const res = await fetch("/api/scenarios");
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const list = await res.json();

      scenarioSelect.innerHTML = '<option value="">-- Load Sample Scenario --</option>';
      list.forEach((sc) => {
        scenariosCache[sc.id] = sc;
        const opt = document.createElement("option");
        opt.value = sc.id;
        opt.textContent = sc.label;
        scenarioSelect.appendChild(opt);
      });
    } catch (err) {
      addTrace("ERROR", `Failed loading scenario list: ${err.message}`, "error");
    }
  }

  // Scenario Selection Handler
  scenarioSelect.addEventListener("change", async (e) => {
    const scId = e.target.value;
    if (!scId) return;

    try {
      addTrace("SCENARIO", `Loading sample scenario '${scId}'...`, "info");
      const res = await fetch(`/api/scenarios/${scId}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();

      const inc = data.incident;
      titleInput.value = inc.title;
      serviceInput.value = inc.service;
      severitySelect.value = inc.severity;
      descInput.value = inc.description;
      logInput.value = inc.log_excerpt || "";

      outcomeService.value = inc.service;
      scenarioTag.style.display = "inline-flex";
      if (btnPrefillOutcome) btnPrefillOutcome.style.display = "inline-flex";

      updateCounters();
      formErrorBanner.style.display = "none";
      addTrace("SCENARIO", `Populated fields for ${inc.service} (${inc.severity})`, "success");
    } catch (err) {
      addTrace("ERROR", `Failed fetching scenario: ${err.message}`, "error");
    }
  });

  // Character Counter Updates
  function updateCounters() {
    titleCount.textContent = `${titleInput.value.length}/200`;
    descCount.textContent = `${descInput.value.length}/2000`;
  }
  titleInput.addEventListener("input", updateCounters);
  descInput.addEventListener("input", updateCounters);

  // Keyboard Submission Shortcut (Ctrl+Enter)
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      if (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA") {
        incidentForm.requestSubmit();
      }
    }
  });

  // 3. Investigate Incident Submission
  incidentForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    formErrorBanner.style.display = "none";

    const payload = {
      title: titleInput.value.trim(),
      service: serviceInput.value.trim(),
      severity: severitySelect.value,
      description: descInput.value.trim(),
      log_excerpt: logInput.value.trim() || null,
    };

    // Validation
    if (!payload.title || !payload.service || !payload.description) {
      formErrorBanner.textContent = "Please fill in all required fields (Title, Service, Description).";
      formErrorBanner.style.display = "block";
      return;
    }

    // Set Loading State
    btnInvestigate.disabled = true;
    investigateSpinner.style.display = "inline";
    resultsEmptyState.style.display = "none";
    resultsContent.style.display = "none";
    resultsProvenanceTags.style.display = "none";
    resultsLoadingState.style.display = "block";

    addTrace("REQUEST", `Investigating incident for '${payload.service}' [${payload.severity}]`, "info");
    addTrace("HINDSIGHT", `Querying memory bank for similar historical incidents...`, "info");

    try {
      const res = await fetch("/api/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Server error" }));
        throw new Error(errorData.detail || `Server returned ${res.status}`);
      }

      const result = await res.json();

      // Log real trace events
      addTrace("HINDSIGHT", `Retrieved ${result.memory_evidence.length} relevant historical incident(s)`, "success");
      const reasonerName = result.provenance_summary.reasoner_source || "LLM";
      addTrace("LLM", `Generated structured investigation analysis via ${reasonerName}`, "success");

      const reasonerBadge = document.getElementById("provenance-reasoner-badge");
      if (reasonerBadge) {
        reasonerBadge.textContent = reasonerName.toUpperCase();
      }

      // Render Memory Evidence
      renderMemoryEvidence(result.memory_evidence);

      // Render 6 Structured Sections
      resSummary.textContent = result.incident_summary;

      if (result.relevant_past_incidents && result.relevant_past_incidents.length > 0) {
        resPastIncidents.innerHTML = result.relevant_past_incidents
          .map((item) => `<div style="margin-bottom: 4px;">• <span class="font-mono">${escapeHtml(item)}</span></div>`)
          .join("");
      } else {
        resPastIncidents.innerHTML = `<span class="text-muted">No relevant historical incidents retrieved from memory bank.</span>`;
      }

      resHistorySuggests.textContent = result.what_history_suggests;

      // Diagnostic Checks
      resDiagnosticChecks.innerHTML = result.recommended_diagnostic_checks
        .map(
          (check) => `
          <div class="check-item">
            <div class="check-num">${check.step}.</div>
            <div class="check-body">
              <div class="text-sm font-medium text-primary">${escapeHtml(check.action)}</div>
              <div class="text-xs text-secondary" style="margin-top: 2px;">${escapeHtml(check.purpose)}</div>
              ${
                check.command_example
                  ? `<div class="check-cmd font-mono">${escapeHtml(check.command_example)}</div>`
                  : ""
              }
            </div>
          </div>
        `
        )
        .join("");

      resDifferences.textContent = result.differences_and_uncertainty;
      resNextStep.textContent = result.suggested_next_step;

      // Set target service on outcome form
      outcomeService.value = payload.service;
      if (btnPrefillOutcome) btnPrefillOutcome.style.display = "inline-flex";

      // Show results
      resultsLoadingState.style.display = "none";
      resultsContent.style.display = "block";
      resultsProvenanceTags.style.display = "flex";
      addTrace("COMPLETE", "Investigation results rendered successfully", "success");
    } catch (err) {
      resultsLoadingState.style.display = "none";
      resultsEmptyState.style.display = "block";
      formErrorBanner.textContent = `Investigation error: ${err.message}`;
      formErrorBanner.style.display = "block";
      addTrace("ERROR", `Investigation failed: ${err.message}`, "error");
    } finally {
      btnInvestigate.disabled = false;
      investigateSpinner.style.display = "none";
    }
  });

  // Render Memory Evidence Cards
  function renderMemoryEvidence(memories) {
    memoryCountBadge.textContent = `${memories.length} ${memories.length === 1 ? "memory" : "memories"}`;

    if (!memories || memories.length === 0) {
      memoryEmptyState.style.display = "block";
      memoryEmptyState.innerHTML = `
        <div class="text-secondary font-medium" style="margin-bottom: 2px;">No historical incident memory retrieved</div>
        <div class="text-xs text-muted">The agent is operating without prior experience for this service.</div>
      `;
      memoryList.style.display = "none";
      memoryList.innerHTML = "";
      return;
    }

    memoryEmptyState.style.display = "none";
    memoryList.style.display = "block";
    memoryList.innerHTML = memories
      .map(
        (m) => `
        <div class="memory-card">
          <div class="memory-card-header">
            <div style="display: flex; align-items: center; gap: var(--space-2);">
              <span class="badge badge-neutral font-mono">${escapeHtml(m.incident_id)}</span>
              <span class="text-xs font-semibold text-primary">${escapeHtml(m.title)}</span>
            </div>
            <span class="badge badge-ok">${escapeHtml(m.historical_verification_status)}</span>
          </div>
          <div class="text-xs text-secondary" style="margin-bottom: var(--space-2); line-height: 1.4;">
            ${escapeHtml(m.excerpt)}
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--border-subtle); padding-top: var(--space-1);">
            <span class="text-xs text-muted">Reason: ${escapeHtml(m.relevance_reason)}</span>
            <span class="text-xs font-mono text-muted">${escapeHtml(m.recorded_at)}</span>
          </div>
        </div>
      `
      )
      .join("");
  }

  // 3.5 Seed Baseline Memory Handler
  if (btnSeedMemory) {
    btnSeedMemory.addEventListener("click", async () => {
      btnSeedMemory.disabled = true;
      const originalText = btnSeedMemory.textContent;
      btnSeedMemory.textContent = "Seeding...";
      addTrace("HINDSIGHT", "Seeding baseline incident INC-2026-0417 into memory bank...", "info");

      try {
        const res = await fetch("/api/seed", { method: "POST" });
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const data = await res.json();
        addTrace("HINDSIGHT", `Seeded baseline memory bank successfully (${data.details.mode})`, "success");
        btnSeedMemory.textContent = "Seeded";
        setTimeout(() => {
          btnSeedMemory.textContent = originalText;
          btnSeedMemory.disabled = false;
        }, 2000);
      } catch (err) {
        addTrace("ERROR", `Seeding failed: ${err.message}`, "error");
        btnSeedMemory.textContent = "Failed";
        setTimeout(() => {
          btnSeedMemory.textContent = originalText;
          btnSeedMemory.disabled = false;
        }, 2000);
      }
    });
  }

  // 3.6 Sample Outcome Pre-fill Handler
  if (btnPrefillOutcome) {
    btnPrefillOutcome.addEventListener("click", () => {
      const currentSvc = (serviceInput.value || outcomeService.value || "checkout-api").trim();
      outcomeService.value = currentSvc;

      if (currentSvc.toLowerCase().includes("notification") || currentSvc.toLowerCase().includes("worker")) {
        outcomeCause.value = "Downstream SMS gateway rate limiting triggered exponential retry backoff, choking message partition workers.";
        outcomeFix.value = "Introduced asynchronous dispatch queue with circuit breaker to shed unacknowledged SMS bursts without worker blocking.";
        outcomeStatus.value = "VERIFIED";
        outcomeNotes.value = "Consumer partition lag returned to normal (12 msgs) within 5 minutes of deploying circuit breaker.";
      } else {
        outcomeCause.value = "Upstream transaction lock timeout was holding database connection pool slots open for >60s during burst.";
        outcomeFix.value = "Reduced upstream transaction lock timeout to 2s, patched query index on orders table, and recycled connection pool.";
        outcomeStatus.value = "VERIFIED";
        outcomeNotes.value = "Validated zero connection acquisition timeouts across 45m load test window.";
      }
      outcomeNotice.className = "notice-banner info";
      outcomeNotice.textContent = "Sample outcome populated. Review and click 'Save Outcome to Hindsight' to persist.";
      addTrace("OUTCOME", `Pre-filled sample verified outcome for '${currentSvc}'`, "info");
    });
  }

  // 4. Verified Outcome Form Handler
  outcomeForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      service: outcomeService.value.trim(),
      confirmed_root_cause: outcomeCause.value.trim(),
      resolution_fix: outcomeFix.value.trim(),
      verification_status: outcomeStatus.value,
      notes: outcomeNotes.value.trim() || null,
    };

    if (!payload.service || !payload.confirmed_root_cause || !payload.resolution_fix) {
      outcomeNotice.className = "notice-banner error";
      outcomeNotice.textContent = "Please fill in confirmed root cause and resolution before saving.";
      return;
    }

    addTrace("OUTCOME", `Submitting verified outcome for '${payload.service}' to Hindsight...`, "info");

    try {
      const res = await fetch("/api/outcomes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      const rec = data.recorded_outcome;
      const retainInfo = data.retention_result || {};
      const docId = retainInfo.incident_id || "INC-NEW";

      outcomeNotice.className = "notice-banner success";
      outcomeNotice.innerHTML = `
        <strong>Outcome successfully saved to memory!</strong><br>
        Document ID: <code class="font-mono">${escapeHtml(docId)}</code> (${escapeHtml(data.storage_mode)}).<br>
        Click <em>"Investigate Incident"</em> again to observe how OpsMind now retrieves this verified history!
      `;

      addTrace("HINDSIGHT", `Retained verified outcome for '${payload.service}' [Document: ${docId}, Status: ${payload.verification_status}, Mode: ${data.storage_mode}]`, "success");
      addTrace("HINDSIGHT", `Persistent memory updated. Subsequent investigations on '${payload.service}' will recall this record.`, "info");

      // Dynamically prepend newly retained memory to Memory Evidence panel if current investigation matches service
      if (serviceInput.value.trim().toLowerCase() === payload.service.toLowerCase()) {
        memoryEmptyState.style.display = "none";
        memoryList.style.display = "block";
        const newCard = document.createElement("div");
        newCard.className = "memory-card";
        newCard.style.borderColor = "var(--status-ok)";
        newCard.innerHTML = `
          <div class="memory-card-header">
            <div style="display: flex; align-items: center; gap: var(--space-2);">
              <span class="badge badge-ok font-mono">${escapeHtml(docId)}</span>
              <span class="text-xs font-semibold text-primary">Verified Outcome: ${escapeHtml(payload.service)}</span>
              <span class="badge badge-provenance memory">NEWLY RETAINED</span>
            </div>
            <span class="badge badge-ok">${escapeHtml(payload.verification_status)}</span>
          </div>
          <div class="text-xs text-secondary" style="margin-bottom: var(--space-2); line-height: 1.4;">
            Confirmed Cause: ${escapeHtml(payload.confirmed_root_cause)}<br>
            Verified Resolution: ${escapeHtml(payload.resolution_fix)}
            ${payload.notes ? `<br><span class="text-muted">Notes: ${escapeHtml(payload.notes)}</span>` : ""}
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--border-subtle); padding-top: var(--space-1);">
            <span class="text-xs text-muted">Reason: Newly submitted verified resolution.</span>
            <span class="text-xs font-mono text-muted">${escapeHtml(rec.timestamp || getTimestamp())}</span>
          </div>
        `;
        memoryList.insertBefore(newCard, memoryList.firstChild);
        const currentCount = memoryList.querySelectorAll(".memory-card").length;
        memoryCountBadge.textContent = `${currentCount} ${currentCount === 1 ? "memory" : "memories"}`;
      }
    } catch (err) {
      outcomeNotice.className = "notice-banner error";
      outcomeNotice.textContent = `Failed saving outcome: ${err.message}`;
      addTrace("ERROR", `Outcome retention failed: ${err.message}`, "error");
    }
  });

  // 5. Reset / New Investigation Button
  btnReset.addEventListener("click", () => {
    incidentForm.reset();
    scenarioSelect.value = "";
    scenarioTag.style.display = "none";
    if (btnPrefillOutcome) btnPrefillOutcome.style.display = "none";
    formErrorBanner.style.display = "none";
    updateCounters();

    resultsLoadingState.style.display = "none";
    resultsContent.style.display = "none";
    resultsProvenanceTags.style.display = "none";
    resultsEmptyState.style.display = "block";

    memoryCountBadge.textContent = "0 memories";
    memoryEmptyState.style.display = "block";
    memoryEmptyState.textContent = "No memories retrieved yet. Submit an incident to query Hindsight memory banks.";
    memoryList.style.display = "none";
    memoryList.innerHTML = "";

    outcomeForm.reset();
    outcomeNotice.className = "notice-banner info";
    outcomeNotice.textContent = "Record verified root cause and resolution to store in persistent memory for future investigations.";

    addTrace("RESET", "Cleared investigation workspace for new incident", "info");
  });

  // Helper: HTML Escaping
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initialize
  checkHealth();
  loadScenarios();
  updateCounters();
});
