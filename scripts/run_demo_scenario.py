import os
import sys
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.services.transaction_simulator import simulation_service
from app.core.guards import check_demo_environment_guard

def main():
    check_demo_environment_guard("Demo scenario execution")
    parser = argparse.ArgumentParser(description="SentinelFlow AI Demo Scenario Runner")
    parser.add_argument("--scenario", choices=["rapid_movement", "connected_network", "legitimate_unusual", "all"], default="rapid_movement", help="Named scenario to execute")
    args = parser.parse_args()
    
    print(f"Triggering deterministic scenario: {args.scenario}...")
    if args.scenario == "all":
        for sc in ["rapid_movement", "connected_network", "legitimate_unusual"]:
            res = simulation_service.run_named_scenario(sc)
            print(f"Scenario {sc}: Injected {res.get('events_created', 0)} events.")
    else:
        res = simulation_service.run_named_scenario(args.scenario)
        print(f"Scenario {args.scenario} executed successfully! Events created: {res.get('events_created', 0)}")
        print(f"Results summary: {res}")

if __name__ == "__main__":
    main()
