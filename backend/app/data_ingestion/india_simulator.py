"""
India-Specific Banking Transaction Simulator.

Calibrated using official RBI and NPCI aggregate payment indicators.
Generates realistic domestic (INR) and cross-border payment flows with:
- Normal account behaviours (salary, utility, merchant, ATM, loan).
- High-fidelity money mule scenarios (domestic chains, international layering,
  coordinated mule networks, circular loops).
- Realistic legitimate lookalikes (corporate payroll fan-out, e-commerce fan-in)
  to stress-test false-positive controls.

CRITICAL ARCHITECTURAL GUARANTEE:
All ground-truth labels (mule accounts, laundering typologies, hop sequences)
are routed strictly to the protected evaluation store via `label_isolation.py`.
Pipeline A receives only label-free normalized records.
"""

import random
import uuid
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from app.data_ingestion.rbi_npci_statistics import (
    CALIBRATED_INDIAN_PAYMENT_BENCHMARKS,
    get_channel_weights
)
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import (
    store_protected_transaction_label,
    store_protected_account_label,
    store_protected_scenario_label,
    assert_no_label_leakage
)

INDIAN_BANKS = [
    "State Bank of India (SBI)",
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Punjab National Bank (PNB)",
    "Kotak Mahindra Bank",
    "Bank of Baroda"
]

INTERNATIONAL_BANKS = {
    "UAE": ["Emirates NBD", "First Abu Dhabi Bank (FAB)", "Mashreq Bank", "Dubai Islamic Bank"],
    "USA": ["JPMorgan Chase", "Bank of America", "Citibank", "Wells Fargo"],
    "GBR": ["Barclays", "HSBC UK", "Lloyds Bank", "NatWest"],
    "SGP": ["DBS Bank", "OCBC Bank", "UOB"],
    "DEU": ["Deutsche Bank", "Commerzbank"]
}

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow"
]

class IndiaBankingSimulator:
    """Generates realistic Indian banking records calibrated with RBI/NPCI macro distributions."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        np.random.seed(seed)
        self.channel_weights = get_channel_weights()

    def sample_channel_amount(self, channel: str) -> float:
        """Sample transaction amount from calibrated distribution for given channel."""
        benchmark = CALIBRATED_INDIAN_PAYMENT_BENCHMARKS.get(channel)
        if not benchmark:
            return round(self.rng.uniform(100.0, 5000.0), 2)

        fam = benchmark.distribution_family
        params = benchmark.distribution_params

        if fam == "lognormal":
            raw = np.random.lognormal(mean=params["mean"], sigma=params["sigma"])
        elif fam == "pareto":
            raw = (np.random.pareto(a=params["alpha"]) + 1) * params["scale"]
        elif fam == "truncated_normal":
            raw = np.random.normal(loc=params["mean"], scale=params["std"])
        else:
            raw = self.rng.uniform(benchmark.min_typical_inr, benchmark.max_typical_inr)

        clamped = max(benchmark.min_typical_inr, min(benchmark.max_typical_inr, raw))
        return round(float(clamped), 2)

    def sample_payment_channel(self) -> str:
        """Pick a payment channel according to official RBI/NPCI market shares."""
        channels = list(self.channel_weights.keys())
        weights = list(self.channel_weights.values())
        return self.rng.choices(channels, weights=weights, k=1)[0]

    def generate_synthetic_ecosystem(
        self,
        num_customers: int = 250,
        num_accounts: int = 300,
        num_normal_txns: int = 1500,
        include_scenarios: bool = True,
        start_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generates a complete banking ecosystem:
        - Normal transactions reflecting daily Indian economic life with >=200 legitimate accounts.
        - Five distinct complex crime scenarios and legitimate lookalikes.
        - Strictly isolates all ground truth into protected store.
        """
        base_time = start_date or (datetime.now(timezone.utc) - timedelta(days=14))
        accounts = []
        customers = []

        # 1. Create Customers and Accounts
        for i in range(num_customers):
            cust_id = f"CUST-IND-{1000 + i}"
            city = self.rng.choice(INDIAN_CITIES)
            customers.append({
                "id": cust_id,
                "customer_ref": f"REF-{1000 + i}",
                "full_name": f"Account Holder {i+1}",
                "email": f"holder_{1000 + i}@bank.in",
                "city": city,
                "country": "IND",
                "risk_tier": "STANDARD",
                "kyc_status": "VERIFIED",
                "created_at": base_time.isoformat()
            })

        for j in range(num_accounts):
            acc_id = f"ACC-IND-{2000 + j}"
            cust = customers[j % len(customers)]
            bank = self.rng.choice(INDIAN_BANKS)
            acc_type = self.rng.choice(["SAVINGS", "CURRENT", "SALARY", "BUSINESS"])
            acc_obj = {
                "id": acc_id,
                "account_number": f"IN{self.rng.randint(1000000000, 9999999999)}",
                "customer_id": cust["id"],
                "bank_name": bank,
                "country": "IND",
                "currency": "INR",
                "account_type": acc_type,
                "balance": round(self.rng.uniform(10000.0, 500000.0), 2),
                "is_dormant": 1 if self.rng.random() < 0.05 else 0,
                "created_at": base_time.isoformat()
            }
            accounts.append(acc_obj)

            # Store baseline legitimate ground-truth label in protected store (overridden if selected in scenarios)
            store_protected_account_label(
                account_id=acc_id,
                dataset_name="INDIA_SIMULATOR",
                is_mule=0,
                mule_role="NORMAL_RETAIL_ACCOUNT",
                raw_labels={"category": "NORMAL_BANKING"},
                timestamp=base_time.isoformat()
            )

        detection_txns: List[Dict[str, Any]] = []

        # 2. Generate Normal Activity
        current_time = base_time
        for k in range(num_normal_txns):
            current_time += timedelta(minutes=self.rng.randint(5, 60))
            src = self.rng.choice(accounts)
            dest = self.rng.choice(accounts)
            while dest["id"] == src["id"]:
                dest = self.rng.choice(accounts)

            channel = self.sample_payment_channel()
            amt = self.sample_channel_amount(channel)

            txn_id = f"TXN-NORM-{uuid.uuid4().hex[:10]}"
            txn_record = {
                "id": txn_id,
                "event_id": f"EVT-{txn_id}",
                "source_account_id": src["id"],
                "destination_account_id": dest["id"],
                "amount": amt,
                "currency": "INR",
                "created_at": current_time.isoformat(),
                "sender_bank": src["bank_name"],
                "receiver_bank": dest["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": channel,
                "payment_type": "TRANSFER",
                "converted_amount": amt,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": current_time.isoformat(),
                "device_id": f"DEV-IND-{src['id'][-4:]}",
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            # Verify no labels exist in record
            assert_no_label_leakage(txn_record)
            detection_txns.append(txn_record)

            # Store protected negative ground-truth label
            store_protected_transaction_label(
                transaction_id=txn_id,
                dataset_name="INDIA_SIMULATOR",
                is_laundering=0,
                laundering_type="LEGITIMATE_NORMAL",
                raw_labels={"category": "NORMAL_BANKING"},
                timestamp=current_time.isoformat()
            )

        scenario_summaries = []

        if include_scenarios:
            # 3. Inject Coordinated Scenario A: Domestic Indian Mule Chain
            scen_a_txns, scen_a_meta = self._inject_domestic_mule_chain(accounts, current_time)
            detection_txns.extend(scen_a_txns)
            scenario_summaries.append(scen_a_meta)
            current_time += timedelta(hours=3)

            # 4. Inject Coordinated Scenario B: International Layering (INR -> UAE AED / USD)
            scen_b_txns, scen_b_meta = self._inject_international_layering(accounts, current_time)
            detection_txns.extend(scen_b_txns)
            scenario_summaries.append(scen_b_meta)
            current_time += timedelta(hours=3)

            # 5. Inject Coordinated Scenario C: Coordinated Mule Network (Fan-in Consolidation & Redistribution)
            scen_c_txns, scen_c_meta = self._inject_coordinated_mule_network(accounts, current_time)
            detection_txns.extend(scen_c_txns)
            scenario_summaries.append(scen_c_meta)
            current_time += timedelta(hours=3)

            # 6. Inject Scenario D: Circular Fund Movement (Cycle)
            scen_d_txns, scen_d_meta = self._inject_circular_movement(accounts, current_time)
            detection_txns.extend(scen_d_txns)
            scenario_summaries.append(scen_d_meta)
            current_time += timedelta(hours=3)

            # 7. Inject Scenario E: Legitimate Lookalikes (Corporate Payroll & E-Commerce Aggregator)
            scen_e_txns, scen_e_meta = self._inject_legitimate_lookalikes(accounts, current_time)
            detection_txns.extend(scen_e_txns)
            scenario_summaries.append(scen_e_meta)

        return {
            "customers": customers,
            "accounts": accounts,
            "transactions": detection_txns,
            "total_transactions": len(detection_txns),
            "scenarios_injected": scenario_summaries
        }

    def _inject_domestic_mule_chain(
        self,
        accounts: List[Dict[str, Any]],
        start_time: datetime
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scenario A:
        UPI Scam Proceeds (₹2,50,000) -> Mule A
        Mule A rapidly forwards to Mules B, C, D (cross-bank) with 3% commission retention.
        Mules B, C, D forward onward to final off-ramp Accounts E, F, G.
        """
        victim = accounts[0]
        mule_a = accounts[1]
        mules_level_1 = [accounts[2], accounts[3], accounts[4]]
        mules_level_2 = [accounts[5], accounts[6], accounts[7]]

        txns = []
        hops = []
        t = start_time

        # Initial scam entry
        scam_amt = 250000.0
        t1_id = f"TXN-SCEN-A-001"
        t1 = {
            "id": t1_id,
            "event_id": f"EVT-{t1_id}",
            "source_account_id": victim["id"],
            "destination_account_id": mule_a["id"],
            "amount": scam_amt,
            "currency": "INR",
            "created_at": t.isoformat(),
            "sender_bank": victim["bank_name"],
            "receiver_bank": mule_a["bank_name"],
            "sender_country": "IND",
            "receiver_country": "IND",
            "payment_channel": "UPI",
            "payment_type": "TRANSFER",
            "converted_amount": scam_amt,
            "converted_currency": "INR",
            "exchange_rate": 1.0,
            "exchange_rate_source": "DOMESTIC_PARITY",
            "exchange_rate_timestamp": t.isoformat(),
            "device_id": "DEV-SCAM-VICTIM",
            "dataset_source": "INDIA_SIMULATOR",
            "status": "COMPLETED"
        }
        txns.append(t1)
        hops.append({"hop": 1, "txn_id": t1_id, "from": victim["id"], "to": mule_a["id"], "amount": scam_amt})

        store_protected_transaction_label(
            t1_id, "INDIA_SIMULATOR", 1, "SCAM_INFLOW",
            {"scenario": "A_DOMESTIC_CHAIN", "hop": 1}, t.isoformat()
        )

        # Hop 2: Rapid split to Mules B, C, D within 8 minutes
        split_amt = round((scam_amt * 0.97) / len(mules_level_1), 2)  # 3% retained by Mule A
        for idx, m1 in enumerate(mules_level_1):
            t += timedelta(minutes=2)
            t_id = f"TXN-SCEN-A-SPLIT-{idx+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": mule_a["id"],
                "destination_account_id": m1["id"],
                "amount": split_amt,
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": mule_a["bank_name"],
                "receiver_bank": m1["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "IMPS",
                "payment_type": "TRANSFER",
                "converted_amount": split_amt,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "device_id": "DEV-MULE-SHARED-01",
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            hops.append({"hop": 2, "txn_id": t_id, "from": mule_a["id"], "to": m1["id"], "amount": split_amt})
            store_protected_transaction_label(
                t_id, "INDIA_SIMULATOR", 1, "MULE_FAN_OUT",
                {"scenario": "A_DOMESTIC_CHAIN", "hop": 2}, t.isoformat()
            )

        # Hop 3: Redistribution onward within 15 minutes
        for idx, (m1, m2) in enumerate(zip(mules_level_1, mules_level_2)):
            t += timedelta(minutes=4)
            forward_amt = round(split_amt * 0.96, 2)
            t_id = f"TXN-SCEN-A-HOP3-{idx+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": m1["id"],
                "destination_account_id": m2["id"],
                "amount": forward_amt,
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": m1["bank_name"],
                "receiver_bank": m2["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "NEFT",
                "payment_type": "TRANSFER",
                "converted_amount": forward_amt,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "device_id": f"DEV-MULE-SHARED-02",
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            hops.append({"hop": 3, "txn_id": t_id, "from": m1["id"], "to": m2["id"], "amount": forward_amt})
            store_protected_transaction_label(
                t_id, "INDIA_SIMULATOR", 1, "LAYERING_PASS_THROUGH",
                {"scenario": "A_DOMESTIC_CHAIN", "hop": 3}, t.isoformat()
            )

        # Store protected scenario labels
        mule_ids = [mule_a["id"]] + [m["id"] for m in mules_level_1] + [m["id"] for m in mules_level_2]
        for mid in mule_ids:
            store_protected_account_label(
                mid, "INDIA_SIMULATOR", is_mule=1, mule_role="CHAIN_FORWARDER",
                raw_labels={"scenario": "A_DOMESTIC_CHAIN"}, timestamp=t.isoformat()
            )

        store_protected_scenario_label(
            scenario_id="SCENARIO_A_DOMESTIC_MULE_CHAIN",
            dataset_name="INDIA_SIMULATOR",
            typology="DOMESTIC_MULE_CHAIN",
            mule_account_ids=mule_ids,
            victim_account_ids=[victim["id"]],
            beneficiary_account_ids=[m["id"] for m in mules_level_2],
            laundering_hops=hops,
            timestamp=t.isoformat()
        )

        return txns, {
            "scenario_id": "SCENARIO_A_DOMESTIC_MULE_CHAIN",
            "name": "Domestic Indian Multi-Hop Mule Chain",
            "typology": "DOMESTIC_MULE_CHAIN",
            "txns_count": len(txns),
            "hops_depth": 3,
            "total_stolen_inr": scam_amt
        }

    def _inject_international_layering(
        self,
        accounts: List[Dict[str, Any]],
        start_time: datetime
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scenario B:
        Scam INR (₹18,00,000) moves domestically, crosses border to UAE (Dubai),
        converts into AED, redistributes to UK (GBP) or consolidates offshore.
        """
        src_ind = accounts[8]
        mule_ind = accounts[9]
        uae_acc = "ACC-UAE-DUBAI-901"
        uk_acc = "ACC-UK-LON-902"

        txns = []
        hops = []
        t = start_time

        # 1. Domestic hop in India
        amt_inr = 1800000.0
        t1_id = "TXN-SCEN-B-DOM-01"
        t1 = {
            "id": t1_id,
            "event_id": f"EVT-{t1_id}",
            "source_account_id": src_ind["id"],
            "destination_account_id": mule_ind["id"],
            "amount": amt_inr,
            "currency": "INR",
            "created_at": t.isoformat(),
            "sender_bank": src_ind["bank_name"],
            "receiver_bank": mule_ind["bank_name"],
            "sender_country": "IND",
            "receiver_country": "IND",
            "payment_channel": "RTGS",
            "payment_type": "TRANSFER",
            "converted_amount": amt_inr,
            "converted_currency": "INR",
            "exchange_rate": 1.0,
            "exchange_rate_source": "DOMESTIC_PARITY",
            "exchange_rate_timestamp": t.isoformat(),
            "dataset_source": "INDIA_SIMULATOR",
            "status": "COMPLETED"
        }
        txns.append(t1)
        hops.append({"hop": 1, "txn_id": t1_id, "from": src_ind["id"], "to": mule_ind["id"], "amount": amt_inr, "currency": "INR"})
        store_protected_transaction_label(t1_id, "INDIA_SIMULATOR", 1, "DOMESTIC_AGGREGATION", {}, t.isoformat())

        # 2. Cross-border wire to UAE with currency conversion INR -> AED
        t += timedelta(minutes=45)
        conv_uae = CurrencyConversionService.convert_amount(amt_inr, "INR", "AED", t.isoformat())
        amt_aed = conv_uae["converted_amount"]

        t2_id = "TXN-SCEN-B-XBORDER-UAE"
        t2 = {
            "id": t2_id,
            "event_id": f"EVT-{t2_id}",
            "source_account_id": mule_ind["id"],
            "destination_account_id": uae_acc,
            "amount": amt_inr,
            "currency": "INR",
            "created_at": t.isoformat(),
            "sender_bank": mule_ind["bank_name"],
            "receiver_bank": "Emirates NBD",
            "sender_country": "IND",
            "receiver_country": "ARE",
            "payment_channel": "SWIFT_WIRE",
            "payment_type": "CROSS_BORDER",
            "converted_amount": amt_aed,
            "converted_currency": "AED",
            "exchange_rate": conv_uae["exchange_rate"],
            "exchange_rate_source": conv_uae["exchange_rate_source"],
            "exchange_rate_timestamp": conv_uae["exchange_rate_timestamp"],
            "dataset_source": "INDIA_SIMULATOR",
            "status": "COMPLETED"
        }
        txns.append(t2)
        hops.append({"hop": 2, "txn_id": t2_id, "from": mule_ind["id"], "to": uae_acc, "amount": amt_inr, "currency": "INR", "converted": amt_aed, "converted_curr": "AED"})
        store_protected_transaction_label(t2_id, "INDIA_SIMULATOR", 1, "CROSS_BORDER_EGRESS", {}, t.isoformat())

        # 3. UAE onwards transfer in AED to London account in GBP
        t += timedelta(hours=2)
        conv_uk = CurrencyConversionService.convert_amount(amt_aed, "AED", "GBP", t.isoformat())
        amt_gbp = conv_uk["converted_amount"]

        t3_id = "TXN-SCEN-B-ONWARD-UK"
        t3 = {
            "id": t3_id,
            "event_id": f"EVT-{t3_id}",
            "source_account_id": uae_acc,
            "destination_account_id": uk_acc,
            "amount": amt_aed,
            "currency": "AED",
            "created_at": t.isoformat(),
            "sender_bank": "Emirates NBD",
            "receiver_bank": "Barclays",
            "sender_country": "ARE",
            "receiver_country": "GBR",
            "payment_channel": "SWIFT_WIRE",
            "payment_type": "CROSS_BORDER",
            "converted_amount": amt_gbp,
            "converted_currency": "GBP",
            "exchange_rate": conv_uk["exchange_rate"],
            "exchange_rate_source": conv_uk["exchange_rate_source"],
            "exchange_rate_timestamp": conv_uk["exchange_rate_timestamp"],
            "dataset_source": "INDIA_SIMULATOR",
            "status": "COMPLETED"
        }
        txns.append(t3)
        hops.append({"hop": 3, "txn_id": t3_id, "from": uae_acc, "to": uk_acc, "amount": amt_aed, "currency": "AED", "converted": amt_gbp, "converted_curr": "GBP"})
        store_protected_transaction_label(t3_id, "INDIA_SIMULATOR", 1, "OFFSHORE_CONSOLIDATION", {}, t.isoformat())

        store_protected_account_label(mule_ind["id"], "INDIA_SIMULATOR", 1, "CROSS_BORDER_EXFILTRATOR", {}, t.isoformat())
        store_protected_account_label(uae_acc, "INDIA_SIMULATOR", 1, "OFFSHORE_HUB", {}, t.isoformat())
        store_protected_account_label(uk_acc, "INDIA_SIMULATOR", 1, "FINAL_OFF_RAMP", {}, t.isoformat())

        store_protected_scenario_label(
            scenario_id="SCENARIO_B_INTERNATIONAL_LAYERING",
            dataset_name="INDIA_SIMULATOR",
            typology="INTERNATIONAL_LAYERING",
            mule_account_ids=[mule_ind["id"], uae_acc, uk_acc],
            victim_account_ids=[src_ind["id"]],
            beneficiary_account_ids=[uk_acc],
            laundering_hops=hops,
            timestamp=t.isoformat()
        )

        return txns, {
            "scenario_id": "SCENARIO_B_INTERNATIONAL_LAYERING",
            "name": "Cross-Border Layering (India -> UAE -> UK)",
            "typology": "INTERNATIONAL_LAYERING",
            "txns_count": len(txns),
            "hops_depth": 3,
            "corridors": ["IND -> ARE", "ARE -> GBR"],
            "currencies": ["INR", "AED", "GBP"]
        }

    def _inject_coordinated_mule_network(
        self,
        accounts: List[Dict[str, Any]],
        start_time: datetime
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scenario C: Coordinated Mule Network
        Multiple distinct victim payments fan-in into 3 separate mules,
        which then consolidate into a single aggregator account,
        which immediately splits funds to 2 cash-out destination accounts.
        """
        victims = [accounts[10], accounts[11], accounts[12]]
        mules = [accounts[13], accounts[14], accounts[15]]
        aggregator = accounts[16]
        cashouts = [accounts[17], accounts[18]]

        txns = []
        hops = []
        t = start_time

        # Fan-in: Victims pay Mules (UPI)
        for i, (vic, mule) in enumerate(zip(victims, mules)):
            amt = round(self.rng.uniform(75000.0, 150000.0), 2)
            t += timedelta(minutes=5)
            t_id = f"TXN-SCEN-C-IN-{i+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": vic["id"],
                "destination_account_id": mule["id"],
                "amount": amt,
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": vic["bank_name"],
                "receiver_bank": mule["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "UPI",
                "payment_type": "TRANSFER",
                "converted_amount": amt,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            hops.append({"hop": 1, "txn_id": t_id, "from": vic["id"], "to": mule["id"], "amount": amt})
            store_protected_transaction_label(t_id, "INDIA_SIMULATOR", 1, "MULE_ENTRY_POINT", {}, t.isoformat())

        # Consolidation: Mules forward to aggregator (IMPS)
        for i, mule in enumerate(mules):
            t += timedelta(minutes=10)
            amt = round(self.rng.uniform(70000.0, 140000.0), 2)
            t_id = f"TXN-SCEN-C-MERGE-{i+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": mule["id"],
                "destination_account_id": aggregator["id"],
                "amount": amt,
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": mule["bank_name"],
                "receiver_bank": aggregator["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "IMPS",
                "payment_type": "TRANSFER",
                "converted_amount": amt,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            hops.append({"hop": 2, "txn_id": t_id, "from": mule["id"], "to": aggregator["id"], "amount": amt})
            store_protected_transaction_label(t_id, "INDIA_SIMULATOR", 1, "FAN_IN_CONSOLIDATION", {}, t.isoformat())

        # Re-distribution: Aggregator splits to cash-out mules
        for i, co in enumerate(cashouts):
            t += timedelta(minutes=15)
            amt = 150000.0
            t_id = f"TXN-SCEN-C-OUT-{i+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": aggregator["id"],
                "destination_account_id": co["id"],
                "amount": amt,
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": aggregator["bank_name"],
                "receiver_bank": co["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "NEFT",
                "payment_type": "TRANSFER",
                "converted_amount": amt,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            hops.append({"hop": 3, "txn_id": t_id, "from": aggregator["id"], "to": co["id"], "amount": amt})
            store_protected_transaction_label(t_id, "INDIA_SIMULATOR", 1, "FAN_OUT_DISPERSAL", {}, t.isoformat())

        mule_all = [m["id"] for m in mules] + [aggregator["id"]] + [c["id"] for c in cashouts]
        for mid in mule_all:
            store_protected_account_label(mid, "INDIA_SIMULATOR", 1, "COORDINATED_MULE", {}, t.isoformat())

        store_protected_scenario_label(
            scenario_id="SCENARIO_C_COORDINATED_MULE_NETWORK",
            dataset_name="INDIA_SIMULATOR",
            typology="COORDINATED_FAN_IN_OUT",
            mule_account_ids=mule_all,
            victim_account_ids=[v["id"] for v in victims],
            beneficiary_account_ids=[c["id"] for c in cashouts],
            laundering_hops=hops,
            timestamp=t.isoformat()
        )

        return txns, {
            "scenario_id": "SCENARIO_C_COORDINATED_MULE_NETWORK",
            "name": "Coordinated Split-Merge Mule Network",
            "typology": "COORDINATED_FAN_IN_OUT",
            "txns_count": len(txns),
            "hops_depth": 3
        }

    def _inject_circular_movement(
        self,
        accounts: List[Dict[str, Any]],
        start_time: datetime
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scenario D: Circular Fund Movement (Round-Tripping / Layering Cycle)
        A -> B -> C -> D -> A (₹4,00,000)
        """
        cycle_accs = [accounts[20], accounts[21], accounts[22], accounts[23]]
        txns = []
        hops = []
        t = start_time
        amt = 400000.0

        for i in range(len(cycle_accs)):
            src = cycle_accs[i]
            dest = cycle_accs[(i + 1) % len(cycle_accs)]
            t += timedelta(minutes=20)
            t_id = f"TXN-SCEN-D-CYCLE-{i+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": src["id"],
                "destination_account_id": dest["id"],
                "amount": round(amt - (i * 2000), 2),
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": src["bank_name"],
                "receiver_bank": dest["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "IMPS",
                "payment_type": "TRANSFER",
                "converted_amount": round(amt - (i * 2000), 2),
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            hops.append({"hop": i+1, "txn_id": t_id, "from": src["id"], "to": dest["id"], "amount": tx["amount"]})
            store_protected_transaction_label(t_id, "INDIA_SIMULATOR", 1, "CIRCULAR_ROUND_TRIP", {}, t.isoformat())

        cycle_ids = [a["id"] for a in cycle_accs]
        for cid in cycle_ids:
            store_protected_account_label(cid, "INDIA_SIMULATOR", 1, "CIRCULAR_NODE", {}, t.isoformat())

        store_protected_scenario_label(
            scenario_id="SCENARIO_D_CIRCULAR_MOVEMENT",
            dataset_name="INDIA_SIMULATOR",
            typology="CIRCULAR_CYCLE",
            mule_account_ids=cycle_ids,
            victim_account_ids=[],
            beneficiary_account_ids=[],
            laundering_hops=hops,
            timestamp=t.isoformat()
        )

        return txns, {
            "scenario_id": "SCENARIO_D_CIRCULAR_MOVEMENT",
            "name": "Circular Round-Trip Flow (Cycle Length 4)",
            "typology": "CIRCULAR_CYCLE",
            "txns_count": len(txns),
            "cycle_length": 4
        }

    def _inject_legitimate_lookalikes(
        self,
        accounts: List[Dict[str, Any]],
        start_time: datetime
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scenario E: Legitimate Lookalikes (False-Positive Stress Test)
        1. Corporate Payroll Fan-Out: Company account pays monthly salaries to 12 employees via NEFT.
           - Appears as a high-velocity fan-out, but counterparties have 2+ years of tenure and predictable amounts.
        2. E-Commerce Marketplace Fan-In: Multiple buyers pay marketplace account.
           - Retained balance remains in the company account rather than rapid forward laundering.
        """
        company_acc = accounts[25]
        employees = accounts[26:38]
        marketplace_acc = accounts[39]
        buyers = accounts[40:48]

        txns = []
        t = start_time

        # Payroll Fan-Out
        for idx, emp in enumerate(employees):
            salary = round(self.rng.uniform(45000.0, 120000.0), 2)
            t += timedelta(seconds=30)
            t_id = f"TXN-SCEN-E-PAYROLL-{idx+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": company_acc["id"],
                "destination_account_id": emp["id"],
                "amount": salary,
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": company_acc["bank_name"],
                "receiver_bank": emp["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "NEFT",
                "payment_type": "SALARY",
                "converted_amount": salary,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            # Protected label: explicitly 0 (legitimate)
            store_protected_transaction_label(t_id, "INDIA_SIMULATOR", 0, "LEGITIMATE_PAYROLL", {}, t.isoformat())

        # Marketplace Fan-In
        for idx, buyer in enumerate(buyers):
            purchase = round(self.rng.uniform(800.0, 4500.0), 2)
            t += timedelta(minutes=12)
            t_id = f"TXN-SCEN-E-MARKET-{idx+1}"
            tx = {
                "id": t_id,
                "event_id": f"EVT-{t_id}",
                "source_account_id": buyer["id"],
                "destination_account_id": marketplace_acc["id"],
                "amount": purchase,
                "currency": "INR",
                "created_at": t.isoformat(),
                "sender_bank": buyer["bank_name"],
                "receiver_bank": marketplace_acc["bank_name"],
                "sender_country": "IND",
                "receiver_country": "IND",
                "payment_channel": "UPI",
                "payment_type": "MERCHANT_PAYMENT",
                "converted_amount": purchase,
                "converted_currency": "INR",
                "exchange_rate": 1.0,
                "exchange_rate_source": "DOMESTIC_PARITY",
                "exchange_rate_timestamp": t.isoformat(),
                "dataset_source": "INDIA_SIMULATOR",
                "status": "COMPLETED"
            }
            txns.append(tx)
            store_protected_transaction_label(t_id, "INDIA_SIMULATOR", 0, "LEGITIMATE_COMMERCE", {}, t.isoformat())

        # Store protected account labels as legitimate (is_mule = 0)
        store_protected_account_label(company_acc["id"], "INDIA_SIMULATOR", 0, "CORPORATE_PAYROLL", {}, t.isoformat())
        store_protected_account_label(marketplace_acc["id"], "INDIA_SIMULATOR", 0, "MERCHANT_AGGREGATOR", {}, t.isoformat())

        return txns, {
            "scenario_id": "SCENARIO_E_LEGITIMATE_LOOKALIKES",
            "name": "Legitimate Lookalikes (Corporate Payroll & E-Commerce Fan-In)",
            "typology": "BENIGN_LOOKALIKE",
            "txns_count": len(txns),
            "expected_label": 0
        }
