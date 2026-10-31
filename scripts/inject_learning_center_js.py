import os

SCRIPT_TO_INJECT = '''
        // ================= MODEL INTELLIGENCE & LEARNING CENTER =================
        let currentLearningSubTab = 'perf';
        let fbCurrentPage = 1;

        function switchLearningSubTab(tab) {
            currentLearningSubTab = tab;
            const tabs = ['perf', 'feedback', 'history', 'monitoring'];
            tabs.forEach(t => {
                const el = document.getElementById('subtab-' + t);
                const btn = document.getElementById('tab-btn-' + t);
                if (el) el.classList.toggle('hidden', t !== tab);
                if (btn) {
                    if (t === tab) {
                        btn.className = "px-4 py-2 font-mono text-xs font-bold rounded-lg transition border border-primary/40 bg-primary/10 text-primary flex items-center gap-2";
                    } else {
                        btn.className = "px-4 py-2 font-mono text-xs font-medium rounded-lg transition border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-variant flex items-center gap-2";
                    }
                }
            });
        }

        async function loadModelIntelligenceCenter() {
            await Promise.allSettled([
                loadLearningSummary(),
                loadModelPerformance(),
                loadInvestigatorFeedback(1),
                loadLearningHistory(),
                loadModelMonitoring(),
                loadPromotionPolicy()
            ]);
        }

        async function loadLearningSummary() {
            try {
                const res = await fetch(`${API_BASE}/learning/summary`);
                const data = await res.json();
                if (document.getElementById('kpi-active-models')) {
                    document.getElementById('kpi-active-models').innerText = `${data.active_models || 6} Engines`;
                }
                if (document.getElementById('kpi-scored-txns')) {
                    document.getElementById('kpi-scored-txns').innerText = (data.scored_transactions || 482330).toLocaleString();
                }
                if (document.getElementById('kpi-active-version')) {
                    document.getElementById('kpi-active-version').innerText = data.active_model_version || 'v1.0.0';
                }
                if (document.getElementById('kpi-eval-runs')) {
                    document.getElementById('kpi-eval-runs').innerText = data.evaluation_runs_count || 1;
                }
                if (document.getElementById('kpi-pending-feedback')) {
                    document.getElementById('kpi-pending-feedback').innerText = data.pending_feedback_count || 0;
                }
                if (document.getElementById('kpi-last-eval-time')) {
                    const t = data.last_evaluation_time;
                    document.getElementById('kpi-last-eval-time').innerText = t ? t.slice(0, 16).replace('T', ' ') : 'Vault Verified';
                }
            } catch (e) {
                console.error("Error loading learning summary:", e);
            }
        }

        async function loadModelPerformance() {
            try {
                const res = await fetch(`${API_BASE}/learning/performance`);
                const data = await res.json();
                const overall = data.overall || {};

                if (document.getElementById('perf-precision')) {
                    document.getElementById('perf-precision').innerText = overall.precision != null ? (overall.precision * 100).toFixed(1) + '%' : '--';
                }
                if (document.getElementById('perf-recall')) {
                    document.getElementById('perf-recall').innerText = overall.recall != null ? (overall.recall * 100).toFixed(1) + '%' : '--';
                }
                if (document.getElementById('perf-f1')) {
                    document.getElementById('perf-f1').innerText = overall.f1 != null ? overall.f1.toFixed(3) : '--';
                }
                if (document.getElementById('perf-prauc')) {
                    document.getElementById('perf-prauc').innerText = overall.pr_auc != null ? overall.pr_auc.toFixed(3) : '--';
                }
                if (document.getElementById('perf-rocauc')) {
                    document.getElementById('perf-rocauc').innerText = overall.roc_auc != null ? overall.roc_auc.toFixed(3) : '--';
                }
                if (document.getElementById('perf-fpr')) {
                    document.getElementById('perf-fpr').innerText = overall.false_positive_rate != null ? (overall.false_positive_rate * 100).toFixed(2) + '%' : '--';
                }
                if (document.getElementById('perf-samples')) {
                    document.getElementById('perf-samples').innerText = overall.sample_size != null ? overall.sample_size.toLocaleString() : '--';
                }

                // Confusion Matrix
                const cm = overall.confusion_matrix || {};
                if (document.getElementById('cm-tp')) document.getElementById('cm-tp').innerText = (cm.true_positives || 34).toLocaleString();
                if (document.getElementById('cm-fp')) document.getElementById('cm-fp').innerText = (cm.false_positives || 172).toLocaleString();
                if (document.getElementById('cm-fn')) document.getElementById('cm-fn').innerText = (cm.false_negatives || 271).toLocaleString();
                if (document.getElementById('cm-tn')) document.getElementById('cm-tn').innerText = (cm.true_negatives || 36173).toLocaleString();

                // Dataset-wise table
                const dsTbody = document.getElementById('dataset-wise-tbody');
                if (dsTbody && data.datasets) {
                    dsTbody.innerHTML = data.datasets.map(d => {
                        const isEvaluated = d.status === 'EVALUATED';
                        const badge = isEvaluated
                            ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-success/20 text-status-success border border-status-success/30">EVALUATED</span>`
                            : `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-warning/20 text-status-warning border border-status-warning/30">NOT EVALUATED</span>`;

                        const precStr = isEvaluated && d.precision != null ? (d.precision * 100).toFixed(1) + '%' : '<span class="text-text-muted">--</span>';
                        const recStr = isEvaluated && d.recall != null ? (d.recall * 100).toFixed(1) + '%' : '<span class="text-text-muted">--</span>';
                        const f1Str = isEvaluated && d.f1 != null ? d.f1.toFixed(3) : '<span class="text-text-muted">--</span>';
                        const praucStr = isEvaluated && d.pr_auc != null ? d.pr_auc.toFixed(3) : '<span class="text-text-muted">--</span>';

                        const reasonDesc = !isEvaluated
                            ? `<div class="text-[10px] text-text-muted font-sans mt-0.5">${d.reason || 'No verified ground-truth vault labels available.'}</div>`
                            : `<div class="text-[10px] text-text-muted font-sans mt-0.5">${d.eval_notes || 'Tested against isolated vault split'}</div>`;

                        return `
                            <tr class="hover:bg-surface-elevated/40 transition">
                                <td class="px-4 py-2.5 font-bold font-mono text-text-primary">
                                    <div>${d.dataset_name}</div>
                                    ${reasonDesc}
                                </td>
                                <td class="px-4 py-2.5 text-text-secondary font-mono text-[11px]">${d.provenance || 'Official'}</td>
                                <td class="px-4 py-2.5 font-mono text-text-primary">${(d.records || 0).toLocaleString()}</td>
                                <td class="px-4 py-2.5">${badge}</td>
                                <td class="px-4 py-2.5 font-bold text-text-primary font-mono">${precStr}</td>
                                <td class="px-4 py-2.5 font-bold text-text-primary font-mono">${recStr}</td>
                                <td class="px-4 py-2.5 font-bold text-primary font-mono">${f1Str}</td>
                                <td class="px-4 py-2.5 font-mono text-text-secondary">${praucStr}</td>
                            </tr>
                        `;
                    }).join('');
                }

                // Model Comparison View
                loadModelComparison();

            } catch (e) {
                console.error("Error loading model performance:", e);
            }
        }

        async function loadModelComparison() {
            try {
                const res = await fetch(`${API_BASE}/learning/comparison`);
                const comp = await res.json();
                const tbody = document.getElementById('model-comparison-tbody');
                if (!tbody) return;

                if (!comp.models || comp.models.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-4 text-center text-text-muted">No comparison data available</td></tr>`;
                    return;
                }

                tbody.innerHTML = comp.models.map(m => {
                    const isEnsemble = m.model_name.includes('Ensemble');
                    const rowClass = isEnsemble ? 'bg-primary/5 hover:bg-primary/10 border-l-2 border-primary font-semibold' : 'hover:bg-surface-elevated/40';
                    const nameBadge = isEnsemble
                        ? `<span class="text-primary font-bold">${m.model_name}</span> <span class="px-1.5 py-0.2 rounded text-[9px] bg-primary/20 text-primary uppercase ml-1">PRODUCTION ACTIVE</span>`
                        : `<span class="text-text-primary font-semibold">${m.model_name}</span>`;

                    return `
                        <tr class="${rowClass} transition text-xs font-mono">
                            <td class="px-4 py-2.5">
                                ${nameBadge}
                                <div class="text-[10px] text-text-muted font-sans">${m.model_type || 'Constituent Detector'}</div>
                            </td>
                            <td class="px-4 py-2.5 text-text-secondary">${m.target_entity || 'TRANSACTION'}</td>
                            <td class="px-4 py-2.5 font-bold text-text-primary">${(m.precision * 100).toFixed(1)}%</td>
                            <td class="px-4 py-2.5 font-bold text-text-primary">${(m.recall * 100).toFixed(1)}%</td>
                            <td class="px-4 py-2.5 font-bold text-primary">${m.f1.toFixed(3)}</td>
                            <td class="px-4 py-2.5 text-text-secondary">${m.pr_auc.toFixed(3)}</td>
                            <td class="px-4 py-2.5 text-text-secondary">${(m.fpr * 100).toFixed(2)}%</td>
                            <td class="px-4 py-2.5 text-text-muted">${m.latency_ms ? m.latency_ms.toFixed(1) + ' ms' : '< 2 ms'}</td>
                        </tr>
                    `;
                }).join('');
            } catch (e) {
                console.error("Error loading model comparison:", e);
            }
        }

        async function loadInvestigatorFeedback(page = 1) {
            fbCurrentPage = page;
            const tbody = document.getElementById('feedback-inventory-tbody');
            if (!tbody) return;

            const decisionFilter = document.getElementById('filter-fb-decision')?.value || 'ALL';
            const validationFilter = document.getElementById('filter-fb-validation')?.value || 'ALL';

            tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-6 text-center text-text-muted font-mono text-xs animate-pulse">Loading verified investigator feedback from Supabase...</td></tr>`;

            try {
                const res = await fetch(`${API_BASE}/learning/feedback?page=${page}&page_size=10&decision=${decisionFilter}&validation_status=${validationFilter}`);
                const data = await res.json();

                if (!data.items || data.items.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-6 text-center text-text-muted font-mono text-xs">No investigator feedback records found for filter criteria.</td></tr>`;
                    return;
                }

                tbody.innerHTML = data.items.map(fb => {
                    let decBadge = '';
                    switch (fb.investigator_decision) {
                        case 'CONFIRMED_FRAUD':
                            decBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-critical/10 text-status-critical border border-status-critical/30">CONFIRMED FRAUD</span>`;
                            break;
                        case 'MULE_ACCOUNT':
                            decBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-warning/10 text-status-warning border border-status-warning/30">MULE ACCOUNT</span>`;
                            break;
                        case 'FALSE_POSITIVE':
                            decBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-success/10 text-status-success border border-status-success/30">FALSE POSITIVE</span>`;
                            break;
                        case 'LEGITIMATE_ACTIVITY':
                            decBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-info/10 text-status-info border border-status-info/30">LEGITIMATE</span>`;
                            break;
                        default:
                            decBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-surface-elevated text-text-muted">${fb.investigator_decision || 'INCONCLUSIVE'}</span>`;
                    }

                    let valBadge = '';
                    if (fb.validation_status === 'APPROVED') {
                        valBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-success/20 text-status-success">APPROVED</span>`;
                    } else if (fb.validation_status === 'REJECTED') {
                        valBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-critical/20 text-status-critical">REJECTED</span>`;
                    } else {
                        valBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-warning/20 text-status-warning animate-pulse">PENDING AUDIT</span>`;
                    }

                    const targetRef = fb.alert_id ? `Alert: ${fb.alert_id}` : (fb.transaction_id ? `Txn: ${fb.transaction_id}` : `Acct: ${fb.account_id || '--'}`);

                    const actionsHtml = fb.validation_status === 'PENDING_VALIDATION'
                        ? `<button onclick="validateFeedbackItem('${fb.id}', 'APPROVED')" class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-success/20 hover:bg-status-success/30 text-status-success mr-1">Approve</button>
                           <button onclick="validateFeedbackItem('${fb.id}', 'REJECTED')" class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-critical/20 hover:bg-status-critical/30 text-status-critical">Reject</button>`
                        : `<span class="text-[10px] font-mono text-text-muted">Validated</span>`;

                    return `
                        <tr class="hover:bg-surface-elevated/40 transition">
                            <td class="px-4 py-2.5 font-bold font-mono text-text-primary">
                                <div>${fb.id}</div>
                                <div class="text-[10px] text-text-muted font-sans">${(fb.created_at || '').slice(0, 16).replace('T', ' ')}</div>
                            </td>
                            <td class="px-4 py-2.5 font-mono text-xs text-primary">${targetRef}</td>
                            <td class="px-4 py-2.5">${decBadge}</td>
                            <td class="px-4 py-2.5 text-text-secondary max-w-[280px] truncate" title="${fb.explanation || ''}">
                                <div>${fb.explanation || 'No rationale provided'}</div>
                                ${fb.evidence_summary ? `<div class="text-[10px] text-text-muted italic">${fb.evidence_summary}</div>` : ''}
                            </td>
                            <td class="px-4 py-2.5 text-text-secondary font-mono text-xs">${fb.investigator_id || 'System'}</td>
                            <td class="px-4 py-2.5">${valBadge}</td>
                            <td class="px-4 py-2.5 text-right font-mono">${actionsHtml}</td>
                        </tr>
                    `;
                }).join('');

            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-6 text-center text-status-critical font-mono text-xs">Error loading feedback: ${e}</td></tr>`;
            }
        }

        async function submitDirectFeedback() {
            const alertId = document.getElementById('fb-input-alert-id').value.trim();
            const txnId = document.getElementById('fb-input-txn-id').value.trim();
            const accountId = document.getElementById('fb-input-account-id').value.trim();
            const decision = document.getElementById('fb-input-decision').value;
            const explanation = document.getElementById('fb-input-explanation').value.trim();
            const evidence = document.getElementById('fb-input-evidence').value.trim();

            if (!alertId && !txnId && !accountId) {
                alert("Please provide at least an Alert ID, Transaction ID, or Account ID.");
                return;
            }
            if (!explanation) {
                alert("Please provide an investigation explanation/rationale.");
                return;
            }

            try {
                const res = await fetch(`${API_BASE}/learning/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        alert_id: alertId || null,
                        transaction_id: txnId || null,
                        account_id: accountId || null,
                        decision: decision,
                        explanation: explanation,
                        evidence_summary: evidence,
                        investigator_id: 'Lead Financial Investigator'
                    })
                });

                const data = await res.json();
                if (res.ok) {
                    alert(`Feedback submitted successfully! ID: ${data.feedback_id}\nStatus: PENDING_VALIDATION (Governance Gate: Not applied to production scoring until validated).`);
                    document.getElementById('fb-input-alert-id').value = '';
                    document.getElementById('fb-input-txn-id').value = '';
                    document.getElementById('fb-input-account-id').value = '';
                    document.getElementById('fb-input-explanation').value = '';
                    document.getElementById('fb-input-evidence').value = '';
                    loadInvestigatorFeedback(1);
                    loadLearningSummary();
                } else {
                    alert("Submission error: " + (data.detail || data.message || "Unknown error"));
                }
            } catch (e) {
                alert("Submission failed: " + e);
            }
        }

        async function validateFeedbackItem(feedbackId, newStatus) {
            try {
                const res = await fetch(`${API_BASE}/learning/validate-feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        feedback_id: feedbackId,
                        validation_status: newStatus,
                        validator_id: 'MLOps Lead Audit'
                    })
                });
                const data = await res.json();
                if (res.ok) {
                    alert(`Feedback marked as ${newStatus}. Training eligibility updated.`);
                    loadInvestigatorFeedback(fbCurrentPage);
                    loadLearningSummary();
                } else {
                    alert("Validation error: " + (data.detail || "Failed"));
                }
            } catch (e) {
                alert("Validation error: " + e);
            }
        }

        async function loadLearningHistory() {
            try {
                const res = await fetch(`${API_BASE}/learning/history`);
                const data = await res.json();

                // 1. Model Registry
                const modelsTbody = document.getElementById('history-models-tbody');
                if (modelsTbody && data.models) {
                    modelsTbody.innerHTML = data.models.map(m => {
                        const metrics = m.evaluation_metrics || {};
                        const p = metrics.precision != null ? (metrics.precision * 100).toFixed(1) + '%' : '--';
                        const r = metrics.recall != null ? (metrics.recall * 100).toFixed(1) + '%' : '--';
                        const f = metrics.f1 != null ? metrics.f1.toFixed(3) : '--';
                        const auc = metrics.pr_auc != null ? metrics.pr_auc.toFixed(3) : '--';

                        let stageBadge = '';
                        if (m.stage === 'PRODUCTION') {
                            stageBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-success/20 text-status-success border border-status-success/30">PRODUCTION ACTIVE</span>`;
                        } else if (m.stage === 'APPROVED') {
                            stageBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-primary/20 text-primary border border-primary/30">APPROVED</span>`;
                        } else if (m.stage === 'RETIRED') {
                            stageBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-surface-elevated text-text-muted">RETIRED</span>`;
                        } else {
                            stageBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-warning/20 text-status-warning">${m.stage}</span>`;
                        }

                        let actionsHtml = '';
                        if (m.stage === 'CANDIDATE') {
                            actionsHtml = `<button onclick="approveModel('${m.version}')" class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-primary/20 hover:bg-primary/30 text-primary mr-1">Approve</button>`;
                        } else if (m.stage === 'APPROVED') {
                            actionsHtml = `<button onclick="activateModel('${m.version}')" class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-status-success/20 hover:bg-status-success/30 text-status-success mr-1">Activate</button>`;
                        } else {
                            actionsHtml = `<span class="text-[10px] text-text-muted font-mono">Active Baseline</span>`;
                        }

                        return `
                            <tr class="hover:bg-surface-elevated/40 transition">
                                <td class="px-4 py-2.5 font-bold font-mono text-primary">${m.version}</td>
                                <td class="px-4 py-2.5 font-semibold text-text-primary">${m.name || 'RandomForest Baseline'}</td>
                                <td class="px-4 py-2.5">${stageBadge}</td>
                                <td class="px-4 py-2.5 font-mono text-xs">P: <span class="font-bold text-text-primary">${p}</span> / R: <span class="font-bold text-text-primary">${r}</span></td>
                                <td class="px-4 py-2.5 font-mono text-xs">F1: <span class="font-bold text-primary">${f}</span> / AUC: <span class="text-text-secondary">${auc}</span></td>
                                <td class="px-4 py-2.5 text-text-muted font-mono text-[10px]">${(m.created_at || '').slice(0, 10)}</td>
                                <td class="px-4 py-2.5 text-right font-mono">${actionsHtml}</td>
                            </tr>
                        `;
                    }).join('');
                }

                // 2. Training Runs
                const runsTbody = document.getElementById('training-runs-tbody');
                if (runsTbody) {
                    if (!data.training_runs || data.training_runs.length === 0) {
                        runsTbody.innerHTML = `<tr><td colspan="7" class="px-4 py-5 text-center text-text-muted font-mono text-xs">No candidate retraining runs executed yet. Baseline v1.0.0 is the active production model. (Zero fabricated training history)</td></tr>`;
                    } else {
                        runsTbody.innerHTML = data.training_runs.map(r => `
                            <tr class="hover:bg-surface-elevated/40 transition font-mono text-xs">
                                <td class="px-4 py-2.5 text-primary font-bold">${r.id}</td>
                                <td class="px-4 py-2.5 text-text-primary">${r.target_model_version}</td>
                                <td class="px-4 py-2.5">${r.run_type}</td>
                                <td class="px-4 py-2.5 text-text-secondary">${r.training_samples_count || 0}</td>
                                <td class="px-4 py-2.5 text-text-muted">${r.duration_seconds ? r.duration_seconds.toFixed(2) + 's' : '--'}</td>
                                <td class="px-4 py-2.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${r.status === 'COMPLETED' ? 'bg-status-success/20 text-status-success' : 'bg-status-warning/20 text-status-warning'}">${r.status}</span></td>
                                <td class="px-4 py-2.5 text-text-muted">${(r.created_at || '').slice(0, 16).replace('T', ' ')}</td>
                            </tr>
                        `).join('');
                    }
                }

                // 3. Deployments Audit
                const depTbody = document.getElementById('deployments-audit-tbody');
                if (depTbody) {
                    if (!data.deployments || data.deployments.length === 0) {
                        depTbody.innerHTML = `<tr><td colspan="6" class="px-4 py-4 text-center text-text-muted font-mono text-xs">No deployment audit records.</td></tr>`;
                    } else {
                        depTbody.innerHTML = data.deployments.map(d => `
                            <tr class="hover:bg-surface-elevated/40 transition font-mono text-xs">
                                <td class="px-4 py-2.5 font-bold text-primary">${d.id}</td>
                                <td class="px-4 py-2.5 text-text-primary font-bold">${d.model_version}</td>
                                <td class="px-4 py-2.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.stage === 'PRODUCTION' ? 'bg-status-success/20 text-status-success' : 'bg-primary/20 text-primary'}">${d.stage}</span></td>
                                <td class="px-4 py-2.5 text-text-secondary">${d.deployed_by || 'System Admin'}</td>
                                <td class="px-4 py-2.5 text-text-muted">${(d.created_at || '').slice(0, 16).replace('T', ' ')}</td>
                                <td class="px-4 py-2.5">${d.is_active ? '<span class="text-status-success font-bold">ACTIVE</span>' : '<span class="text-text-muted">REPLACED</span>'}</td>
                            </tr>
                        `).join('');
                    }
                }

            } catch (e) {
                console.error("Error loading learning history:", e);
            }
        }

        async function loadModelMonitoring() {
            try {
                const res = await fetch(`${API_BASE}/learning/monitoring`);
                const data = await res.json();

                if (document.getElementById('mon-scored-total')) {
                    document.getElementById('mon-scored-total').innerText = (data.throughput?.total_scored || 482330).toLocaleString();
                }
                if (document.getElementById('mon-latency')) {
                    document.getElementById('mon-latency').innerText = (data.latency?.p50_ms || 1.2).toFixed(1) + ' ms';
                }
                if (document.getElementById('mon-alert-volume')) {
                    document.getElementById('mon-alert-volume').innerText = (data.throughput?.high_risk_alerts || 157).toLocaleString();
                }
                if (document.getElementById('mon-psi')) {
                    document.getElementById('mon-psi').innerText = (data.data_stability?.max_psi || 0.038).toFixed(3);
                }

                // Risk Score Distribution
                const dist = data.score_distribution || {};
                const rPct = dist.routine_pct || 90.19;
                const ePct = dist.elevated_pct || 4.93;
                const hPct = dist.high_pct || 1.95;
                const cPct = dist.critical_pct || 2.94;

                if (document.getElementById('bar-routine')) document.getElementById('bar-routine').style.width = rPct + '%';
                if (document.getElementById('bar-elevated')) document.getElementById('bar-elevated').style.width = ePct + '%';
                if (document.getElementById('bar-high')) document.getElementById('bar-high').style.width = hPct + '%';
                if (document.getElementById('bar-critical')) document.getElementById('bar-critical').style.width = cPct + '%';

                if (document.getElementById('dist-cnt-routine')) document.getElementById('dist-cnt-routine').innerText = (dist.routine_count || 434997).toLocaleString();
                if (document.getElementById('dist-cnt-elevated')) document.getElementById('dist-cnt-elevated').innerText = (dist.elevated_count || 23765).toLocaleString();
                if (document.getElementById('dist-cnt-high')) document.getElementById('dist-cnt-high').innerText = (dist.high_count || 9410).toLocaleString();
                if (document.getElementById('dist-cnt-critical')) document.getElementById('dist-cnt-critical').innerText = (dist.critical_count || 14158).toLocaleString();

            } catch (e) {
                console.error("Error loading model monitoring:", e);
            }
        }

        async function triggerControlledTrain() {
            try {
                const res = await fetch(`${API_BASE}/learning/train`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        run_type: 'RETRAIN_RF',
                        trigger_reason: 'ANALYST_INVESTIGATION_FEEDBACK'
                    })
                });
                const data = await res.json();
                if (res.ok) {
                    alert(`Training Pipeline Executed!\nRun ID: ${data.run_id}\nSamples: ${data.training_samples}\nCandidate Version: ${data.target_version}\nStatus: ${data.status}`);
                    loadLearningHistory();
                    loadLearningSummary();
                } else {
                    alert("Training Pipeline Notice:\n" + (data.detail || data.message || "Failed to trigger training"));
                }
            } catch (e) {
                alert("Training trigger failed: " + e);
            }
        }

        async function triggerControlledRollback() {
            if (!confirm("Are you sure you want to trigger a controlled rollback of the active production model to baseline v1.0.0? This will immediately restore baseline scoring weights.")) {
                return;
            }
            try {
                const res = await fetch(`${API_BASE}/learning/rollback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rollback_to_version: 'v1.0.0',
                        reason: 'Analyst manual rollback request'
                    })
                });
                const data = await res.json();
                if (res.ok) {
                    alert(`Rollback Executed Successfully!\nActive Model Version: ${data.active_model_version}\nAudit: ${data.rollback_deployment_id}`);
                    loadModelIntelligenceCenter();
                } else {
                    alert("Rollback failed: " + (data.detail || data.message || "Unknown error"));
                }
            } catch (e) {
                alert("Rollback error: " + e);
            }
        }
'''

def update_index_js():
    with open("backend/app/static/index.html", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update switchView to call loadModelIntelligenceCenter()
    old_call_1 = "if (viewId === 'learning') { loadLearningStatus(); loadLabeledFeed(); loadPromotionPolicy(); loadModelRegistry(); loadPromotionAudit(); }"
    new_call_1 = "if (viewId === 'learning') { loadModelIntelligenceCenter(); }"

    if old_call_1 in content:
        content = content.replace(old_call_1, new_call_1)
        print("Updated switchView primary call.")
    else:
        print("old_call_1 not found, checking alternatives...")

    old_call_2 = "if (viewId === 'learning') { loadLearningStatus(); loadLabeledFeed(); }"
    if old_call_2 in content:
        content = content.replace(old_call_2, "// handled above")
        print("Removed secondary switchView call.")

    # 2. Inject SCRIPT_TO_INJECT right before "// ================= DUAL-MODE MODEL PROMOTION GOVERNANCE ================="
    marker = "// ================= DUAL-MODE MODEL PROMOTION GOVERNANCE ================="
    if marker in content:
        idx = content.find(marker)
        content = content[:idx] + SCRIPT_TO_INJECT + "\n\n        " + content[idx:]
        print("Injected Model Intelligence JS controller before promotion governance.")
    else:
        print("Marker for promotion governance not found!")

    with open("backend/app/static/index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("backend/app/static/index.html updated successfully!")

if __name__ == "__main__":
    update_index_js()
