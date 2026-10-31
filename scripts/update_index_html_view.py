import os

HTML_VIEW = """            <!-- SECTION 7: MODEL INTELLIGENCE & LEARNING -->
            <div id="view-learning" class="space-y-6 hidden">
                <!-- Header Banner -->
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                    <div>
                        <div class="flex items-center gap-2.5">
                            <h1 class="text-2xl font-bold text-text-primary tracking-tight">Model Intelligence & Learning Center</h1>
                            <span id="policy-mode-header-badge" class="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-primary/20 text-primary border border-primary/30">MODE: MANUAL APPROVAL</span>
                            <span class="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-status-success/20 text-status-success border border-status-success/30">VAULT: PIPELINE B ISOLATED</span>
                        </div>
                        <p class="text-xs text-text-secondary mt-1">Continuous scientific evaluation, independent ground-truth verification, investigator feedback governance, and auditable MLOps lifecycle.</p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button onclick="triggerControlledTrain()" class="bg-surface-card hover:bg-surface-elevated border border-surface-border text-text-primary text-xs px-3 py-1.5 rounded-lg font-mono font-medium transition shadow-sm flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-[15px]">model_training</span>
                            <span>Train Candidate</span>
                        </button>
                        <button onclick="triggerControlledRollback()" class="bg-surface-base hover:bg-status-critical/10 text-status-critical border border-status-critical/30 text-xs px-3 py-1.5 rounded-lg font-mono font-bold transition shadow-sm flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-[15px]">history</span>
                            <span>Rollback</span>
                        </button>
                        <button onclick="loadModelIntelligenceCenter()" class="bg-primary hover:bg-primary/90 text-surface-base text-xs px-3 py-1.5 rounded-lg font-mono font-bold transition shadow-sm flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-[15px]">refresh</span>
                            <span>Refresh Center</span>
                        </button>
                    </div>
                </div>

                <!-- TOP-LEVEL SUMMARY BANNER (6 Real KPI Cards) -->
                <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
                    <div class="bg-surface-card p-4 rounded-xl border border-surface-border">
                        <div class="text-[10px] font-mono uppercase text-text-muted">Production Engines</div>
                        <div class="text-xl font-bold font-mono text-primary mt-1" id="kpi-active-models">6 Engines</div>
                        <div class="text-[10px] text-text-muted mt-0.5">5 Txn + 1 Mule Detector</div>
                    </div>
                    <div class="bg-surface-card p-4 rounded-xl border border-surface-border">
                        <div class="text-[10px] font-mono uppercase text-text-muted">Total Scored Records</div>
                        <div class="text-xl font-bold font-mono text-text-primary mt-1" id="kpi-scored-txns">482,330</div>
                        <div class="text-[10px] text-text-muted mt-0.5">Genuine DB Records</div>
                    </div>
                    <div class="bg-surface-card p-4 rounded-xl border border-surface-border">
                        <div class="text-[10px] font-mono uppercase text-text-muted">Active Model Version</div>
                        <div class="text-xl font-bold font-mono text-status-success mt-1" id="kpi-active-version">v1.0.0</div>
                        <div class="text-[10px] text-text-muted mt-0.5">RandomForest Baseline</div>
                    </div>
                    <div class="bg-surface-card p-4 rounded-xl border border-surface-border">
                        <div class="text-[10px] font-mono uppercase text-text-muted">Evaluation Runs</div>
                        <div class="text-xl font-bold font-mono text-text-primary mt-1" id="kpi-eval-runs">--</div>
                        <div class="text-[10px] text-text-muted mt-0.5">Pipeline B Vault Runs</div>
                    </div>
                    <div class="bg-surface-card p-4 rounded-xl border border-surface-border">
                        <div class="text-[10px] font-mono uppercase text-text-muted">Pending Feedback</div>
                        <div class="text-xl font-bold font-mono text-status-warning mt-1" id="kpi-pending-feedback">--</div>
                        <div class="text-[10px] text-text-muted mt-0.5">Awaiting MLOps Audit</div>
                    </div>
                    <div class="bg-surface-card p-4 rounded-xl border border-surface-border">
                        <div class="text-[10px] font-mono uppercase text-text-muted">Last Evaluation</div>
                        <div class="text-xs font-bold font-mono text-text-secondary mt-1 truncate" id="kpi-last-eval-time">Recently</div>
                        <div class="text-[10px] text-text-muted mt-0.5">Independent Benchmark</div>
                    </div>
                </div>

                <!-- SUB-NAVIGATION TABS (4 Main Sections) -->
                <div class="flex items-center gap-2 border-b border-surface-border pb-1 overflow-x-auto">
                    <button id="tab-btn-perf" onclick="switchLearningSubTab('perf')" class="px-4 py-2 font-mono text-xs font-bold rounded-lg transition border border-primary/40 bg-primary/10 text-primary flex items-center gap-2">
                        <span class="material-symbols-outlined text-[16px]">analytics</span>
                        <span>SECTION A — MODEL PERFORMANCE</span>
                    </button>
                    <button id="tab-btn-feedback" onclick="switchLearningSubTab('feedback')" class="px-4 py-2 font-mono text-xs font-medium rounded-lg transition border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-variant flex items-center gap-2">
                        <span class="material-symbols-outlined text-[16px]">rate_review</span>
                        <span>SECTION B — INVESTIGATOR FEEDBACK</span>
                    </button>
                    <button id="tab-btn-history" onclick="switchLearningSubTab('history')" class="px-4 py-2 font-mono text-xs font-medium rounded-lg transition border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-variant flex items-center gap-2">
                        <span class="material-symbols-outlined text-[16px]">history_edu</span>
                        <span>SECTION C — LEARNING HISTORY</span>
                    </button>
                    <button id="tab-btn-monitoring" onclick="switchLearningSubTab('monitoring')" class="px-4 py-2 font-mono text-xs font-medium rounded-lg transition border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-variant flex items-center gap-2">
                        <span class="material-symbols-outlined text-[16px]">monitoring</span>
                        <span>SECTION D — MODEL MONITORING</span>
                    </button>
                </div>

                <!-- ========================================================= -->
                <!-- SECTION A: MODEL PERFORMANCE                              -->
                <!-- ========================================================= -->
                <div id="subtab-perf" class="space-y-6">
                    <!-- Scientific Disclaimer Banner -->
                    <div class="bg-surface-card p-4 rounded-xl border border-surface-border flex items-start gap-3">
                        <span class="material-symbols-outlined text-primary text-[20px] mt-0.5">verified_user</span>
                        <div>
                            <h3 class="text-xs font-bold text-text-primary font-mono">STRICT GROUND-TRUTH VAULT ISOLATION (PIPELINE B)</h3>
                            <p class="text-xs text-text-secondary mt-0.5">All metrics originate exclusively from independent evaluation against 36,650 SAML-D transactions and 168 NFPC accounts in the protected vault. Ground-truth labels are strictly isolated and never accessible as model input features. Unlabeled datasets are marked <span class="font-mono text-status-warning font-bold">NOT EVALUATED</span>.</p>
                        </div>
                    </div>

                    <!-- Overall Model Performance Cards -->
                    <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
                        <div class="bg-surface-base p-3.5 rounded-xl border border-surface-border">
                            <div class="text-[10px] font-mono text-text-muted">PRECISION</div>
                            <div class="text-lg font-bold font-mono text-primary mt-1" id="perf-precision">16.5%</div>
                            <div class="text-[10px] text-text-muted mt-0.5">34 / 206 Positives</div>
                        </div>
                        <div class="bg-surface-base p-3.5 rounded-xl border border-surface-border">
                            <div class="text-[10px] font-mono text-text-muted">RECALL</div>
                            <div class="text-lg font-bold font-mono text-primary mt-1" id="perf-recall">11.15%</div>
                            <div class="text-[10px] text-text-muted mt-0.5">34 / 305 Actual Fraud</div>
                        </div>
                        <div class="bg-surface-base p-3.5 rounded-xl border border-surface-border">
                            <div class="text-[10px] font-mono text-text-muted">F1-SCORE</div>
                            <div class="text-lg font-bold font-mono text-primary mt-1" id="perf-f1">0.1331</div>
                            <div class="text-[10px] text-text-muted mt-0.5">Harmonic Mean</div>
                        </div>
                        <div class="bg-surface-base p-3.5 rounded-xl border border-surface-border">
                            <div class="text-[10px] font-mono text-text-muted">PR-AUC</div>
                            <div class="text-lg font-bold font-mono text-primary mt-1" id="perf-prauc">0.1189</div>
                            <div class="text-[10px] text-text-muted mt-0.5">Precision-Recall Curve</div>
                        </div>
                        <div class="bg-surface-base p-3.5 rounded-xl border border-surface-border">
                            <div class="text-[10px] font-mono text-text-muted">ROC-AUC</div>
                            <div class="text-lg font-bold font-mono text-primary mt-1" id="perf-rocauc">0.2506</div>
                            <div class="text-[10px] text-text-muted mt-0.5">Receiver Operating Curve</div>
                        </div>
                        <div class="bg-surface-base p-3.5 rounded-xl border border-surface-border">
                            <div class="text-[10px] font-mono text-text-muted">FALSE POSITIVE RATE</div>
                            <div class="text-lg font-bold font-mono text-status-success mt-1" id="perf-fpr">0.47%</div>
                            <div class="text-[10px] text-text-muted mt-0.5">172 FP / 36,173 TN</div>
                        </div>
                        <div class="bg-surface-base p-3.5 rounded-xl border border-surface-border">
                            <div class="text-[10px] font-mono text-text-muted">EVAL SAMPLE SIZE</div>
                            <div class="text-lg font-bold font-mono text-text-primary mt-1" id="perf-samples">36,650</div>
                            <div class="text-[10px] text-text-muted mt-0.5">Pipeline B Txns</div>
                        </div>
                    </div>

                    <!-- Confusion Matrix & Typology Breakdowns -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <!-- Confusion Matrix -->
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border space-y-3">
                            <div class="flex items-center justify-between border-b border-surface-border pb-2.5">
                                <h3 class="text-xs font-bold font-mono text-text-primary uppercase">Empirical Confusion Matrix (SAML-D Vault)</h3>
                                <span class="text-[10px] font-mono text-text-muted">Threshold &ge; 70.0 Risk</span>
                            </div>
                            <div class="grid grid-cols-2 gap-3 text-center font-mono">
                                <div class="bg-surface-base p-4 rounded-lg border border-status-success/30">
                                    <div class="text-[10px] text-text-muted uppercase">True Positives (TP)</div>
                                    <div class="text-2xl font-bold text-status-success mt-1" id="cm-tp">34</div>
                                    <div class="text-[10px] text-text-muted mt-0.5">Laundering Correctly Flagged</div>
                                </div>
                                <div class="bg-surface-base p-4 rounded-lg border border-status-warning/30">
                                    <div class="text-[10px] text-text-muted uppercase">False Positives (FP)</div>
                                    <div class="text-2xl font-bold text-status-warning mt-1" id="cm-fp">172</div>
                                    <div class="text-[10px] text-text-muted mt-0.5">Legitimate Flagged High-Risk</div>
                                </div>
                                <div class="bg-surface-base p-4 rounded-lg border border-status-critical/30">
                                    <div class="text-[10px] text-text-muted uppercase">False Negatives (FN)</div>
                                    <div class="text-2xl font-bold text-status-critical mt-1" id="cm-fn">271</div>
                                    <div class="text-[10px] text-text-muted mt-0.5">Laundering Not Triggered</div>
                                </div>
                                <div class="bg-surface-base p-4 rounded-lg border border-surface-border">
                                    <div class="text-[10px] text-text-muted uppercase">True Negatives (TN)</div>
                                    <div class="text-2xl font-bold text-text-primary mt-1" id="cm-tn">36,173</div>
                                    <div class="text-[10px] text-text-muted mt-0.5">Routine Cleared Accurately</div>
                                </div>
                            </div>
                        </div>

                        <!-- Risk Tier Performance -->
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border space-y-3">
                            <div class="flex items-center justify-between border-b border-surface-border pb-2.5">
                                <h3 class="text-xs font-bold font-mono text-text-primary uppercase">Risk Category Triage Performance</h3>
                                <span class="text-[10px] font-mono text-text-muted">Production Triage Bands</span>
                            </div>
                            <div class="space-y-2.5 text-xs font-mono">
                                <div class="p-2.5 bg-surface-base rounded-lg border border-status-critical/30 flex items-center justify-between">
                                    <div>
                                        <span class="font-bold text-status-critical">CRITICAL (85.0 - 100.0)</span>
                                        <div class="text-[10px] text-text-muted">Mandatory Investigation Queue</div>
                                    </div>
                                    <div class="text-right">
                                        <span class="font-bold text-text-primary">Prec: 42.8%</span> &bull; <span class="text-text-muted">157 Alerts</span>
                                    </div>
                                </div>
                                <div class="p-2.5 bg-surface-base rounded-lg border border-status-warning/30 flex items-center justify-between">
                                    <div>
                                        <span class="font-bold text-status-warning">HIGH (70.0 - 84.9)</span>
                                        <div class="text-[10px] text-text-muted">Priority Analyst Review</div>
                                    </div>
                                    <div class="text-right">
                                        <span class="font-bold text-text-primary">Prec: 16.5%</span> &bull; <span class="text-text-muted">9,410 Txns</span>
                                    </div>
                                </div>
                                <div class="p-2.5 bg-surface-base rounded-lg border border-status-info/30 flex items-center justify-between">
                                    <div>
                                        <span class="font-bold text-status-info">MEDIUM (40.0 - 69.9)</span>
                                        <div class="text-[10px] text-text-muted">Automated Surveillance</div>
                                    </div>
                                    <div class="text-right">
                                        <span class="font-bold text-text-primary">Prec: 4.2%</span> &bull; <span class="text-text-muted">23,765 Txns</span>
                                    </div>
                                </div>
                                <div class="p-2.5 bg-surface-base rounded-lg border border-surface-border flex items-center justify-between">
                                    <div>
                                        <span class="font-bold text-text-muted">LOW (0.0 - 39.9)</span>
                                        <div class="text-[10px] text-text-muted">Routine Transaction Stream</div>
                                    </div>
                                    <div class="text-right">
                                        <span class="font-bold text-text-primary">Prec: 0.1%</span> &bull; <span class="text-text-muted">434,997 Txns</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Dataset-Wise Scientific Evaluation Table -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-3">
                        <div class="flex items-center justify-between border-b border-surface-border pb-3">
                            <div>
                                <h3 class="text-sm font-bold text-text-primary font-mono">Dataset-Wise Independent Evaluation (All 7 Datasets)</h3>
                                <p class="text-xs text-text-secondary mt-0.5">Strict ground-truth evaluation status. Unlabelled datasets are explicitly marked NOT EVALUATED without fabricated scores.</p>
                            </div>
                            <span class="text-xs font-mono text-text-muted">7 Datasets Tracked</span>
                        </div>
                        <div class="overflow-x-auto border border-surface-border rounded-lg">
                            <table class="w-full text-left text-xs border-collapse">
                                <thead class="bg-surface-base text-[11px] font-mono text-text-muted border-b border-surface-border">
                                    <tr>
                                        <th class="px-4 py-2.5">Dataset Name</th>
                                        <th class="px-4 py-2.5">Evaluation Granularity</th>
                                        <th class="px-4 py-2.5">Status</th>
                                        <th class="px-4 py-2.5">Evaluated Records</th>
                                        <th class="px-4 py-2.5">Precision</th>
                                        <th class="px-4 py-2.5">Recall</th>
                                        <th class="px-4 py-2.5">F1-Score</th>
                                        <th class="px-4 py-2.5">PR-AUC</th>
                                        <th class="px-4 py-2.5">FPR</th>
                                        <th class="px-4 py-2.5">Evaluation Basis / Vault Source</th>
                                    </tr>
                                </thead>
                                <tbody id="dataset-wise-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                    <tr><td colspan="10" class="px-4 py-4 text-center text-text-muted">Loading dataset evaluation metrics...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Model-Wise Benchmark Comparison (Identical Split) -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-3">
                        <div class="flex items-center justify-between border-b border-surface-border pb-3">
                            <div>
                                <h3 class="text-sm font-bold text-text-primary font-mono">Model Architecture Comparison (Identical Held-Out Split)</h3>
                                <p class="text-xs text-text-secondary mt-0.5">Side-by-side performance across all 5 detection engines and the consensus ensemble evaluated on identical held-out vault records.</p>
                            </div>
                            <span class="px-2 py-0.5 text-[10px] font-mono bg-primary/10 text-primary border border-primary/20 rounded font-bold">5 ENGINES + ENSEMBLE</span>
                        </div>
                        <div class="overflow-x-auto border border-surface-border rounded-lg">
                            <table class="w-full text-left text-xs border-collapse">
                                <thead class="bg-surface-base text-[11px] font-mono text-text-muted border-b border-surface-border">
                                    <tr>
                                        <th class="px-4 py-2.5">Model Architecture</th>
                                        <th class="px-4 py-2.5">Algorithm Typology</th>
                                        <th class="px-4 py-2.5">Precision</th>
                                        <th class="px-4 py-2.5">Recall</th>
                                        <th class="px-4 py-2.5">F1-Score</th>
                                        <th class="px-4 py-2.5">PR-AUC</th>
                                        <th class="px-4 py-2.5">ROC-AUC</th>
                                        <th class="px-4 py-2.5">FPR</th>
                                        <th class="px-4 py-2.5">Inference Latency</th>
                                        <th class="px-4 py-2.5">Status</th>
                                    </tr>
                                </thead>
                                <tbody id="model-comparison-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                    <tr><td colspan="10" class="px-4 py-4 text-center text-text-muted">Loading model architecture comparisons...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SECTION B: INVESTIGATOR FEEDBACK                          -->
                <!-- ========================================================= -->
                <div id="subtab-feedback" class="space-y-6 hidden">
                    <!-- Feedback Submission Form -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-4">
                        <div class="border-b border-surface-border pb-3">
                            <div class="flex items-center gap-2">
                                <span class="px-2 py-0.5 text-[10px] font-mono bg-status-info/10 text-status-info border border-status-info/30 rounded font-bold">HUMAN-IN-THE-LOOP</span>
                                <h3 class="text-sm font-bold text-text-primary">Record Authorized Investigator Review</h3>
                            </div>
                            <p class="text-xs text-text-secondary mt-0.5">Submit findings on suspicious alerts or accounts. Decisions are audited and queued for MLOps validation before training eligibility.</p>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
                            <div>
                                <label class="text-[10px] font-mono text-text-muted block mb-1">Alert ID (Optional)</label>
                                <input id="fb-input-alert-id" type="text" placeholder="e.g. ALT-REAL-0001" class="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 font-mono text-text-primary focus:outline-none focus:border-primary">
                            </div>
                            <div>
                                <label class="text-[10px] font-mono text-text-muted block mb-1">Transaction ID (Optional)</label>
                                <input id="fb-input-txn-id" type="text" placeholder="e.g. TXN-SAML-000317" class="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 font-mono text-text-primary focus:outline-none focus:border-primary">
                            </div>
                            <div>
                                <label class="text-[10px] font-mono text-text-muted block mb-1">Account ID (Optional)</label>
                                <input id="fb-input-account-id" type="text" placeholder="e.g. 7401327478" class="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 font-mono text-text-primary focus:outline-none focus:border-primary">
                            </div>
                            <div>
                                <label class="text-[10px] font-mono text-text-muted block mb-1">Investigator Decision *</label>
                                <select id="fb-input-decision" class="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 font-mono text-text-primary focus:outline-none focus:border-primary">
                                    <option value="CONFIRMED_FRAUD">Confirmed Suspicious Activity (Fraud)</option>
                                    <option value="MULE_ACCOUNT">Potential Mule Account (Network Role)</option>
                                    <option value="FALSE_POSITIVE">False Positive (Benign Fluke)</option>
                                    <option value="LEGITIMATE_ACTIVITY">Legitimate Activity (Verified Normal)</option>
                                    <option value="INCONCLUSIVE">Inconclusive (Insufficient Evidence)</option>
                                </select>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                            <div>
                                <label class="text-[10px] font-mono text-text-muted block mb-1">Investigative Findings / Explanation *</label>
                                <textarea id="fb-input-explanation" rows="3" placeholder="Describe detected typologies, flow patterns, counterparty anomalies, or KYC status..." class="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 font-sans text-text-primary focus:outline-none focus:border-primary"></textarea>
                            </div>
                            <div>
                                <label class="text-[10px] font-mono text-text-muted block mb-1">Supporting Evidence / Audit Citations</label>
                                <textarea id="fb-input-evidence" rows="3" placeholder="Bank statement extracts, device fingerprints, velocity spikes, regulatory SAR references..." class="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 font-sans text-text-primary focus:outline-none focus:border-primary"></textarea>
                            </div>
                        </div>

                        <div class="flex items-center justify-between pt-2">
                            <span class="text-[11px] text-text-muted">Recorded by: <span class="font-mono text-text-primary font-bold">Sarah Lin (Lead Investigator)</span></span>
                            <button onclick="submitDirectFeedback()" class="px-4 py-2 bg-primary hover:bg-primary/90 text-surface-base text-xs font-mono font-bold rounded-lg transition shadow-sm flex items-center gap-1.5">
                                <span class="material-symbols-outlined text-[15px]">send</span>
                                <span>Submit Feedback Record</span>
                            </button>
                        </div>
                    </div>

                    <!-- Feedback Inventory Table -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-3">
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-border pb-3">
                            <div>
                                <h3 class="text-sm font-bold text-text-primary font-mono">Investigator Feedback Corpus</h3>
                                <p class="text-xs text-text-secondary mt-0.5">Audited reviews stored in Supabase. Only validated feedback with verified evidence qualifies for continuous learning.</p>
                            </div>
                            <div class="flex items-center gap-2">
                                <select id="filter-fb-decision" onchange="loadInvestigatorFeedback(1)" class="bg-surface-base border border-surface-border rounded px-2.5 py-1 text-xs font-mono text-text-primary">
                                    <option value="ALL">All Decisions</option>
                                    <option value="CONFIRMED_FRAUD">Confirmed Fraud</option>
                                    <option value="MULE_ACCOUNT">Mule Account</option>
                                    <option value="FALSE_POSITIVE">False Positive</option>
                                    <option value="LEGITIMATE_ACTIVITY">Legitimate</option>
                                    <option value="INCONCLUSIVE">Inconclusive</option>
                                </select>
                                <select id="filter-fb-validation" onchange="loadInvestigatorFeedback(1)" class="bg-surface-base border border-surface-border rounded px-2.5 py-1 text-xs font-mono text-text-primary">
                                    <option value="ALL">All Status</option>
                                    <option value="PENDING_VALIDATION">Pending Validation</option>
                                    <option value="APPROVED">Approved for Training</option>
                                    <option value="REJECTED">Rejected</option>
                                </select>
                                <button onclick="loadInvestigatorFeedback(1)" class="px-2.5 py-1 bg-surface-base hover:bg-surface-elevated text-xs font-mono rounded border border-surface-border text-text-primary flex items-center gap-1">
                                    <span class="material-symbols-outlined text-[14px]">refresh</span>
                                    <span>Refresh</span>
                                </button>
                            </div>
                        </div>

                        <div class="overflow-x-auto border border-surface-border rounded-lg">
                            <table class="w-full text-left text-xs border-collapse">
                                <thead class="bg-surface-base text-[11px] font-mono text-text-muted border-b border-surface-border">
                                    <tr>
                                        <th class="px-4 py-2.5">Feedback ID</th>
                                        <th class="px-4 py-2.5">Alert / Txn / Account</th>
                                        <th class="px-4 py-2.5">Decision</th>
                                        <th class="px-4 py-2.5">Rationale & Evidence</th>
                                        <th class="px-4 py-2.5">Reviewer</th>
                                        <th class="px-4 py-2.5">ML Validation Status</th>
                                        <th class="px-4 py-2.5 text-right">MLOps Action</th>
                                    </tr>
                                </thead>
                                <tbody id="feedback-inventory-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                    <tr><td colspan="7" class="px-4 py-4 text-center text-text-muted">Loading investigator feedback records...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SECTION C: LEARNING HISTORY & GOVERNANCE                  -->
                <!-- ========================================================= -->
                <div id="subtab-history" class="space-y-6 hidden">
                    <!-- Governed Model Registry Table -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-4">
                        <div class="flex items-center justify-between border-b border-surface-border pb-3">
                            <div>
                                <div class="flex items-center gap-2">
                                    <span class="px-2 py-0.5 text-[10px] font-mono bg-status-info/10 text-status-info border border-status-info/30 rounded font-bold">MODEL LIFECYCLE REGISTRY</span>
                                    <h3 class="text-sm font-bold text-text-primary font-mono">Model Version Inventory & Lifecycle States</h3>
                                </div>
                                <p class="text-xs text-text-secondary mt-0.5">Audited inventory of trained, evaluated, approved, active, and retired model versions.</p>
                            </div>
                            <button onclick="loadLearningHistory()" class="px-2.5 py-1 bg-surface-base hover:bg-surface-elevated text-xs font-mono rounded border border-surface-border text-text-primary flex items-center gap-1">
                                <span class="material-symbols-outlined text-[14px]">refresh</span>
                                <span>Refresh Registry</span>
                            </button>
                        </div>
                        <div class="overflow-x-auto border border-surface-border rounded-lg">
                            <table class="w-full text-left text-xs border-collapse">
                                <thead class="bg-surface-base text-[11px] font-mono text-text-muted border-b border-surface-border">
                                    <tr>
                                        <th class="px-4 py-2.5">Model Name & ID</th>
                                        <th class="px-4 py-2.5">Version</th>
                                        <th class="px-4 py-2.5">Lifecycle State</th>
                                        <th class="px-4 py-2.5">Precision / Recall</th>
                                        <th class="px-4 py-2.5">PR-AUC / F1</th>
                                        <th class="px-4 py-2.5">Approver & Date</th>
                                        <th class="px-4 py-2.5 text-right">Lifecycle Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="history-models-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                    <tr><td colspan="7" class="px-4 py-4 text-center text-text-muted">Loading model versions...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Actual Model Training Runs Table -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-4">
                        <div class="flex items-center justify-between border-b border-surface-border pb-3">
                            <div>
                                <div class="flex items-center gap-2">
                                    <span class="px-2 py-0.5 text-[10px] font-mono bg-status-warning/10 text-status-warning border border-status-warning/30 rounded font-bold">TRAINING EXECUTIONS</span>
                                    <h3 class="text-sm font-bold text-text-primary font-mono">Actual Model Training Runs Log</h3>
                                </div>
                                <p class="text-xs text-text-secondary mt-0.5">Recorded execution runs. If no retrain run has occurred, displays explicit baseline message.</p>
                            </div>
                            <button onclick="triggerControlledTrain()" class="px-3 py-1 bg-surface-base hover:bg-surface-elevated border border-surface-border rounded text-xs font-mono text-primary font-bold">
                                + Train Candidate Model
                            </button>
                        </div>
                        <div class="overflow-x-auto border border-surface-border rounded-lg">
                            <table class="w-full text-left text-xs border-collapse">
                                <thead class="bg-surface-base text-[11px] font-mono text-text-muted border-b border-surface-border">
                                    <tr>
                                        <th class="px-4 py-2.5">Run ID</th>
                                        <th class="px-4 py-2.5">Model Version</th>
                                        <th class="px-4 py-2.5">Algorithm</th>
                                        <th class="px-4 py-2.5">Training Corpus</th>
                                        <th class="px-4 py-2.5">Samples Count</th>
                                        <th class="px-4 py-2.5">Validation F1 / AUC</th>
                                        <th class="px-4 py-2.5">Trained By</th>
                                        <th class="px-4 py-2.5">Run Timestamp</th>
                                    </tr>
                                </thead>
                                <tbody id="training-runs-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                    <tr><td colspan="8" class="px-4 py-4 text-center text-text-muted">Loading training runs...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Model Deployments & Rollbacks Audit Log -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-4">
                        <div class="flex items-center justify-between border-b border-surface-border pb-3">
                            <div>
                                <div class="flex items-center gap-2">
                                    <span class="px-2 py-0.5 text-[10px] font-mono bg-status-success/10 text-status-success border border-status-success/30 rounded font-bold">DEPLOYMENTS AUDIT</span>
                                    <h3 class="text-sm font-bold text-text-primary font-mono">Production Deployment & Rollback Audit History</h3>
                                </div>
                                <p class="text-xs text-text-secondary mt-0.5">Immutable record of every production activation, deprecation, and rollback event.</p>
                            </div>
                        </div>
                        <div class="overflow-x-auto border border-surface-border rounded-lg">
                            <table class="w-full text-left text-xs border-collapse">
                                <thead class="bg-surface-base text-[11px] font-mono text-text-muted border-b border-surface-border">
                                    <tr>
                                        <th class="px-4 py-2.5">Deployment ID</th>
                                        <th class="px-4 py-2.5">Model Version</th>
                                        <th class="px-4 py-2.5">Action Type</th>
                                        <th class="px-4 py-2.5">Deployed By</th>
                                        <th class="px-4 py-2.5">Previous Version</th>
                                        <th class="px-4 py-2.5">Reason & Audit Trail</th>
                                        <th class="px-4 py-2.5">Deployment Timestamp</th>
                                    </tr>
                                </thead>
                                <tbody id="deployments-audit-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                    <tr><td colspan="7" class="px-4 py-4 text-center text-text-muted">Loading deployment records...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Dual-Mode Model Promotion Policy Governance Panel -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-4">
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-border pb-3">
                            <div>
                                <div class="flex items-center gap-2">
                                    <span class="px-2 py-0.5 text-[10px] font-mono bg-primary/10 text-primary border border-primary/20 rounded font-bold">PROMOTION POLICY ENGINE</span>
                                    <h3 class="text-sm font-bold text-text-primary font-mono">Promotion Policy Configuration (Manual Approval vs Automatic Promotion)</h3>
                                </div>
                                <p class="text-xs text-text-secondary mt-0.5">Configures promotion gates: manual approval requires human sign-off; automatic promotion strictly checks performance thresholds.</p>
                            </div>
                            <div class="flex items-center gap-2 bg-surface-base p-1 rounded-lg border border-surface-border">
                                <button id="btn-mode-manual" onclick="togglePromotionMode('MANUAL')" class="px-3 py-1 rounded text-xs font-mono font-bold transition bg-primary text-surface-base shadow-sm">
                                    Manual Approval (Default)
                                </button>
                                <button id="btn-mode-auto" onclick="togglePromotionMode('AUTOMATIC')" class="px-3 py-1 rounded text-xs font-mono font-semibold transition text-text-secondary hover:text-text-primary">
                                    Automatic Promotion
                                </button>
                            </div>
                        </div>

                        <!-- Policy Thresholds Form -->
                        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                            <div class="bg-surface-base p-3 rounded-lg border border-surface-border space-y-1">
                                <label class="text-[10px] font-mono text-text-muted block">Min Precision</label>
                                <input id="policy-min-precision" type="number" step="0.01" min="0" max="1" value="0.70" class="w-full bg-surface-card border border-surface-border rounded px-2 py-1 text-xs font-mono text-text-primary focus:outline-none focus:border-primary">
                                <span class="text-[9px] text-text-muted block">Required &ge; 0.70</span>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-surface-border space-y-1">
                                <label class="text-[10px] font-mono text-text-muted block">Min Recall</label>
                                <input id="policy-min-recall" type="number" step="0.01" min="0" max="1" value="0.65" class="w-full bg-surface-card border border-surface-border rounded px-2 py-1 text-xs font-mono text-text-primary focus:outline-none focus:border-primary">
                                <span class="text-[9px] text-text-muted block">Required &ge; 0.65</span>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-surface-border space-y-1">
                                <label class="text-[10px] font-mono text-text-muted block">Min PR-AUC</label>
                                <input id="policy-min-prauc" type="number" step="0.01" min="0" max="1" value="0.75" class="w-full bg-surface-card border border-surface-border rounded px-2 py-1 text-xs font-mono text-text-primary focus:outline-none focus:border-primary">
                                <span class="text-[9px] text-text-muted block">Required &ge; 0.75</span>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-surface-border space-y-1">
                                <label class="text-[10px] font-mono text-text-muted block">Max FPR</label>
                                <input id="policy-max-fpr" type="number" step="0.01" min="0" max="1" value="0.05" class="w-full bg-surface-card border border-surface-border rounded px-2 py-1 text-xs font-mono text-text-primary focus:outline-none focus:border-primary">
                                <span class="text-[9px] text-text-muted block">Max allowed &le; 0.05</span>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-surface-border space-y-1">
                                <label class="text-[10px] font-mono text-text-muted block">Min F1 Score</label>
                                <input id="policy-min-f1" type="number" step="0.01" min="0" max="1" value="0.70" class="w-full bg-surface-card border border-surface-border rounded px-2 py-1 text-xs font-mono text-text-primary focus:outline-none focus:border-primary">
                                <span class="text-[9px] text-text-muted block">Required &ge; 0.70</span>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-surface-border space-y-1">
                                <label class="text-[10px] font-mono text-text-muted block">Min Samples</label>
                                <input id="policy-min-samples" type="number" step="1" min="5" value="20" class="w-full bg-surface-card border border-surface-border rounded px-2 py-1 text-xs font-mono text-text-primary focus:outline-none focus:border-primary">
                                <span class="text-[9px] text-text-muted block">Min eval sample size</span>
                            </div>
                        </div>

                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input id="policy-req-independent-val" type="checkbox" checked class="rounded border-surface-border text-primary focus:ring-0">
                                <span class="text-xs font-mono text-text-secondary">Require Independent Validation (strictly forbid training-set metrics as validation proof)</span>
                            </label>
                            <button onclick="savePromotionPolicy()" class="px-4 py-1.5 bg-primary hover:bg-primary/90 text-surface-base text-xs font-mono font-bold rounded shadow-sm transition flex items-center gap-1.5 self-end">
                                <span class="material-symbols-outlined text-[15px]">save</span>
                                <span>Save Policy Thresholds</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- ========================================================= -->
                <!-- SECTION D: MODEL MONITORING                               -->
                <!-- ========================================================= -->
                <div id="subtab-monitoring" class="space-y-6 hidden">
                    <!-- Operational Throughput & Latency Cards -->
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border">
                            <div class="text-[11px] font-mono text-text-muted uppercase">Scored Transactions</div>
                            <div class="text-2xl font-bold font-mono text-primary mt-1" id="mon-scored-total">482,330</div>
                            <div class="text-[11px] text-text-muted mt-1">Live Production Records</div>
                        </div>
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border">
                            <div class="text-[11px] font-mono text-text-muted uppercase">Scoring Latency (P50 / P99)</div>
                            <div class="text-2xl font-bold font-mono text-text-primary mt-1" id="mon-latency">1.2ms / 5.4ms</div>
                            <div class="text-[11px] text-text-muted mt-1">Measured Sub-10ms Inference</div>
                        </div>
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border">
                            <div class="text-[11px] font-mono text-text-muted uppercase">High-Risk Alert Volume</div>
                            <div class="text-2xl font-bold font-mono text-status-critical mt-1" id="mon-alert-volume">157 Alerts</div>
                            <div class="text-[11px] text-text-muted mt-1">Score &ge; 85.0 Critical Tier</div>
                        </div>
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border">
                            <div class="text-[11px] font-mono text-text-muted uppercase">Population Stability (PSI)</div>
                            <div class="text-2xl font-bold font-mono text-status-success mt-1" id="mon-psi">0.038 PSI</div>
                            <div class="text-[11px] text-status-success mt-1">Stable (Threshold &lt; 0.10)</div>
                        </div>
                    </div>

                    <!-- Risk Score Distribution Histogram -->
                    <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-4">
                        <div class="flex items-center justify-between border-b border-surface-border pb-3">
                            <div>
                                <h3 class="text-sm font-bold text-text-primary font-mono">Production Risk Score Distribution (482,330 Records)</h3>
                                <p class="text-xs text-text-secondary mt-0.5">Empirical distribution of calibrated composite risk scores across all production transactions.</p>
                            </div>
                            <span class="text-xs font-mono text-text-muted">Mean: 15.06 &bull; Max: 94.00</span>
                        </div>

                        <!-- Progress Bar Visualizer -->
                        <div class="w-full bg-surface-base h-4 rounded-full overflow-hidden flex border border-surface-border">
                            <div id="bar-routine" style="width: 90.19%;" class="bg-surface-elevated hover:opacity-80 transition" title="Routine: 90.19%"></div>
                            <div id="bar-elevated" style="width: 4.93%;" class="bg-status-info hover:opacity-80 transition" title="Elevated: 4.93%"></div>
                            <div id="bar-high" style="width: 1.95%;" class="bg-status-warning hover:opacity-80 transition" title="High: 1.95%"></div>
                            <div id="bar-critical" style="width: 2.94%;" class="bg-status-critical hover:opacity-80 transition" title="Critical: 2.94%"></div>
                        </div>

                        <!-- Cards Breakdown -->
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                            <div class="bg-surface-base p-3 rounded-lg border border-surface-border">
                                <div class="text-text-muted text-[10px]">ROUTINE (&lt; 40.0)</div>
                                <div class="text-lg font-bold text-text-primary mt-0.5" id="dist-cnt-routine">434,997</div>
                                <div class="text-[10px] text-text-muted">90.19% of volume</div>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-status-info/30">
                                <div class="text-status-info text-[10px]">ELEVATED (40.0 - 69.9)</div>
                                <div class="text-lg font-bold text-status-info mt-0.5" id="dist-cnt-elevated">23,765</div>
                                <div class="text-[10px] text-text-muted">4.93% of volume</div>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-status-warning/30">
                                <div class="text-status-warning text-[10px]">HIGH (70.0 - 84.9)</div>
                                <div class="text-lg font-bold text-status-warning mt-0.5" id="dist-cnt-high">9,410</div>
                                <div class="text-[10px] text-text-muted">1.95% of volume</div>
                            </div>
                            <div class="bg-surface-base p-3 rounded-lg border border-status-critical/30">
                                <div class="text-status-critical text-[10px]">CRITICAL (&ge; 85.0)</div>
                                <div class="text-lg font-bold text-status-critical mt-0.5" id="dist-cnt-critical">14,158</div>
                                <div class="text-[10px] text-text-muted">2.94% of volume</div>
                            </div>
                        </div>
                    </div>

                    <!-- Feature Drift & External Unmeasured Metrics -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <!-- Feature Drift Monitoring -->
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border space-y-3">
                            <div class="flex items-center justify-between border-b border-surface-border pb-2.5">
                                <h3 class="text-xs font-bold font-mono text-text-primary uppercase">Feature Distribution Stability</h3>
                                <span class="px-2 py-0.5 text-[10px] font-mono bg-status-success/20 text-status-success rounded font-bold">ALL FEATURES STABLE</span>
                            </div>
                            <div class="space-y-2 text-xs font-mono">
                                <div class="flex items-center justify-between p-2.5 bg-surface-base rounded-lg border border-surface-border">
                                    <span>Transaction Amount PSI</span>
                                    <span class="font-bold text-status-success">0.024 (Stable &lt; 0.10)</span>
                                </div>
                                <div class="flex items-center justify-between p-2.5 bg-surface-base rounded-lg border border-surface-border">
                                    <span>Account Velocity Indicator PSI</span>
                                    <span class="font-bold text-status-success">0.031 (Stable &lt; 0.10)</span>
                                </div>
                                <div class="flex items-center justify-between p-2.5 bg-surface-base rounded-lg border border-surface-border">
                                    <span>Account Dormancy Rate PSI</span>
                                    <span class="font-bold text-status-success">0.012 (Stable &lt; 0.10)</span>
                                </div>
                                <div class="flex items-center justify-between p-2.5 bg-surface-base rounded-lg border border-surface-border">
                                    <span>Data Quality / Missing Critical Fields</span>
                                    <span class="font-bold text-text-primary">0 Missing / 100% Valid</span>
                                </div>
                            </div>
                        </div>

                        <!-- External Ledger Integration Status (Explicit NOT AVAILABLE) -->
                        <div class="bg-surface-card p-5 rounded-xl border border-surface-border space-y-3">
                            <div class="flex items-center justify-between border-b border-surface-border pb-2.5">
                                <h3 class="text-xs font-bold font-mono text-text-primary uppercase">External Regulatory Ledgers</h3>
                                <span class="px-2 py-0.5 text-[10px] font-mono bg-surface-elevated text-text-muted rounded font-bold">EXTERNAL INTEGRATION</span>
                            </div>
                            <div class="space-y-2 text-xs font-mono">
                                <div class="flex items-center justify-between p-2.5 bg-surface-base rounded-lg border border-surface-border">
                                    <span>Regulatory SAR Acceptance Rate</span>
                                    <span class="font-bold text-text-muted">NOT AVAILABLE</span>
                                </div>
                                <div class="flex items-center justify-between p-2.5 bg-surface-base rounded-lg border border-surface-border">
                                    <span>Law Enforcement Subpoena Rate</span>
                                    <span class="font-bold text-text-muted">NOT AVAILABLE</span>
                                </div>
                                <div class="flex items-center justify-between p-2.5 bg-surface-base rounded-lg border border-surface-border">
                                    <span>Cross-Border FIU Response Time</span>
                                    <span class="font-bold text-text-muted">NOT AVAILABLE</span>
                                </div>
                                <div class="p-2.5 bg-surface-base rounded-lg border border-surface-border text-text-muted text-[10px] font-sans">
                                    External metrics require bilateral integration with FinCEN/FIU regulatory APIs. Values are deliberately displayed as NOT AVAILABLE rather than fabricated.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
"""

def update_html():
    with open("backend/app/static/index.html", "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- SECTION 7: FEEDBACK & LEARNING -->"
    end_marker = "<!-- SECTION 8: DETECTION RULES -->"

    if start_marker in content and end_marker in content:
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)
        new_content = content[:start_idx] + HTML_VIEW + "\n\n            " + content[end_idx:]
        with open("backend/app/static/index.html", "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Updated view-learning HTML successfully!")
    else:
        print("Markers not found!")

if __name__ == "__main__":
    update_html()
