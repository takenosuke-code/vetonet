#!/usr/bin/env python3
"""
VetoNet MVP - Semantic Firewall for AI Agent Transactions

Usage:
    python main.py                    # Run test suite
    python main.py --prompt "..."     # Test with custom prompt
    python main.py --interactive      # Interactive mode
"""

import argparse
import sys
from typing import NoReturn

from vetonet import VetoEngine, IntentNormalizer, VetoResult
from vetonet.models import VetoStatus
from vetonet.llm.client import create_client
from vetonet.config import DEFAULT_LLM_CONFIG, DEFAULT_VETO_CONFIG
from tests.scenarios import get_default_scenarios, TestScenario


# ============================================================================
# Output Formatting
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")


def print_subheader(text: str) -> None:
    """Print a subsection header."""
    print(f"\n{Colors.DIM}{'-' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.DIM}{'-' * 60}{Colors.RESET}")


def print_result(result: VetoResult, expected: VetoStatus | None = None) -> None:
    """Print a veto result with formatting."""
    if result.approved:
        status_color = Colors.GREEN
        icon = "[+]"
    else:
        status_color = Colors.RED
        icon = "[x]"

    print(f"  Result: {status_color}{icon} {result.status.value}{Colors.RESET}")
    print(f"  Reason: {result.reason}")

    if expected is not None:
        test_passed = result.status == expected
        test_color = Colors.GREEN if test_passed else Colors.RED
        test_status = "PASS" if test_passed else "FAIL"
        print(f"  Expected: {expected.value} | Test: {test_color}{test_status}{Colors.RESET}")


def print_scenario(scenario: TestScenario) -> None:
    """Print scenario details."""
    print(f"  {Colors.DIM}Description:{Colors.RESET} {scenario.description}")
    print(f"  {Colors.DIM}Intent:{Colors.RESET} category={scenario.anchor.item_category}, "
          f"max=${scenario.anchor.max_price}, qty={scenario.anchor.quantity}, "
          f"recurring={scenario.anchor.is_recurring}")

    # Build payload info
    payload = scenario.payload
    payload_info = f"item=\"{payload.item_description}\", "
    payload_info += f"${payload.unit_price:.2f} x {payload.quantity}"
    if payload.fees:
        payload_info += f" + fees(${payload.total_fees:.2f})"
    payload_info += f" = ${payload.total_price:.2f}"
    payload_info += f", vendor={payload.vendor}"
    if payload.is_recurring:
        payload_info += f" {Colors.YELLOW}[RECURRING]{Colors.RESET}"

    print(f"  {Colors.DIM}Payload:{Colors.RESET} {payload_info}")


# ============================================================================
# Test Runner
# ============================================================================

def run_test_suite(user_prompt: str = "Buy me a $50 Amazon Gift Card") -> bool:
    """
    Run the full test suite with default scenarios.

    Returns True if all tests pass.
    """
    print_header("VetoNet MVP - Semantic Firewall Test Suite")
    print(f"{Colors.DIM}Powered by LOCAL AI (Ollama + Qwen) - No data leaves your device{Colors.RESET}")

    # Initialize components
    llm_client = create_client(DEFAULT_LLM_CONFIG)
    normalizer = IntentNormalizer(llm_client)
    engine = VetoEngine(
        veto_config=DEFAULT_VETO_CONFIG,
        llm_client=llm_client,
    )

    # Normalize intent
    print(f"\n{Colors.BLUE}Normalizing intent...{Colors.RESET}")
    print(f"  User prompt: \"{user_prompt}\"")

    try:
        anchor = normalizer.normalize(user_prompt)
        print(f"  {Colors.GREEN}Intent locked:{Colors.RESET}")
        print(f"    category: {anchor.item_category}")
        print(f"    max_price: ${anchor.max_price}")
        print(f"    currency: {anchor.currency}")
        print(f"    constraints: {anchor.core_constraints}")
    except Exception as e:
        print(f"  {Colors.RED}ERROR:{Colors.RESET} Failed to normalize intent: {e}")
        print(f"\n  Make sure Ollama is running: ollama serve")
        return False

    # Run scenarios
    scenarios = get_default_scenarios(anchor)
    results: list[bool] = []

    for i, scenario in enumerate(scenarios, 1):
        print_subheader(f"Test {i}: {scenario.name}")
        print_scenario(scenario)

        result = engine.check(scenario.anchor, scenario.payload)
        print_result(result, scenario.expected_status)

        results.append(result.status == scenario.expected_status)

    # Summary
    print_header("Summary")
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"{Colors.GREEN}Results: {passed}/{total} tests passed{Colors.RESET}")
        print(f"\n{Colors.GREEN}{Colors.BOLD}THESIS VALIDATED:{Colors.RESET} Intent-locking + drift-detection works!")
        print(f"{Colors.DIM}100% local AI - No data sent to cloud{Colors.RESET}")
    else:
        print(f"{Colors.RED}Results: {passed}/{total} tests passed{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Some tests failed - review output above{Colors.RESET}")

    return passed == total


def run_single_check(user_prompt: str, item: str, price: float, vendor: str) -> None:
    """Run a single check with custom parameters."""
    from vetonet.models import AgentPayload

    print_header("VetoNet - Single Check")

    llm_client = create_client(DEFAULT_LLM_CONFIG)
    normalizer = IntentNormalizer(llm_client)
    engine = VetoEngine(llm_client=llm_client)

    print(f"\n{Colors.BLUE}User Intent:{Colors.RESET} \"{user_prompt}\"")

    try:
        anchor = normalizer.normalize(user_prompt)
        print(f"{Colors.GREEN}Intent locked:{Colors.RESET} {anchor.model_dump_json()}")
    except Exception as e:
        print(f"{Colors.RED}ERROR:{Colors.RESET} {e}")
        return

    payload = AgentPayload(
        item_description=item,
        item_category=anchor.item_category,
        price=price,
        currency=anchor.currency,
        vendor=vendor,
    )

    print(f"\n{Colors.BLUE}Agent Payload:{Colors.RESET}")
    print(f"  Item: {payload.item_description}")
    print(f"  Price: ${payload.price}")
    print(f"  Vendor: {payload.vendor}")

    result = engine.check(anchor, payload)
    print(f"\n{Colors.BLUE}Veto Decision:{Colors.RESET}")
    print_result(result)


def interactive_mode() -> NoReturn:
    """Run VetoNet in interactive mode."""
    from vetonet.models import AgentPayload

    print_header("VetoNet - Interactive Mode")
    print("Type 'quit' to exit\n")

    llm_client = create_client(DEFAULT_LLM_CONFIG)
    normalizer = IntentNormalizer(llm_client)
    engine = VetoEngine(llm_client=llm_client)

    while True:
        try:
            # Get user intent
            print(f"{Colors.BLUE}Enter user intent (or 'quit'):{Colors.RESET}")
            user_prompt = input("> ").strip()

            if user_prompt.lower() == "quit":
                print("Goodbye!")
                sys.exit(0)

            if not user_prompt:
                continue

            # Normalize
            anchor = normalizer.normalize(user_prompt)
            print(f"{Colors.GREEN}Intent locked:{Colors.RESET} {anchor.model_dump_json()}")

            # Get transaction details
            print(f"\n{Colors.BLUE}Enter transaction details:{Colors.RESET}")
            item = input("  Item description: ").strip()
            price = float(input("  Price: $").strip())
            vendor = input("  Vendor: ").strip() or "unknown"

            payload = AgentPayload(
                item_description=item,
                item_category=anchor.item_category,
                price=price,
                currency=anchor.currency,
                vendor=vendor,
            )

            # Check
            result = engine.check(anchor, payload)
            print(f"\n{Colors.BOLD}Decision:{Colors.RESET}")
            print_result(result)
            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"{Colors.RED}Error:{Colors.RESET} {e}\n")


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VetoNet - Semantic Firewall for AI Agent Transactions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              Run test suite
  python main.py --prompt "Buy Nike shoes"    Test with custom prompt
  python main.py --interactive                Interactive mode
        """,
    )

    parser.add_argument(
        "--prompt", "-p",
        type=str,
        help="Custom user prompt to test",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode",
    )

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.prompt:
        run_test_suite(args.prompt)
    else:
        run_test_suite()


if __name__ == "__main__":
    main()
