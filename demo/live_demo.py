#!/usr/bin/env python3
"""
VetoNet Live Demo - Full Agent Commerce Flow

This demo shows:
1. User makes a request
2. AI Agent shops for the item
3. Agent gets prompt-injected (attack scenario)
4. VetoNet intercepts before PayPal payment
5. Attack is blocked, user money is safe

Run: python demo/live_demo.py
"""

import sys
import time
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("")  # Enable ANSI escape codes on Windows
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from demo.shopping_agent import ShoppingAgent, AgentMode, ShoppingResult
from demo.mock_paypal import MockPayPalClient, PaymentStatus
from vetonet import VetoEngine, IntentNormalizer
from vetonet.models import AgentPayload, Fee
from vetonet.llm.client import create_client
from vetonet.config import DEFAULT_LLM_CONFIG


# ============================================================================
# Terminal Colors & Formatting
# ============================================================================

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"


def clear_screen():
    print("\033[2J\033[H", end="")


def print_slow(text: str, delay: float = 0.02):
    """Print text with typewriter effect."""
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def print_box(title: str, content: list[str], color: str = Colors.BLUE):
    """Print a colored box with content."""
    width = max(len(title), max(len(line) for line in content) + 4)
    width = max(width, 50)

    print(f"{color}{'─' * width}{Colors.RESET}")
    print(f"{color}{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{color}{'─' * width}{Colors.RESET}")
    for line in content:
        print(f"  {line}")
    print(f"{color}{'─' * width}{Colors.RESET}")


def print_step(step_num: int, title: str):
    """Print a step header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}[STEP {step_num}] {title}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")


def animate_loading(message: str, duration: float = 1.5):
    """Show loading animation."""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r{Colors.YELLOW}{frames[i % len(frames)]} {message}{Colors.RESET}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r{Colors.GREEN}✓ {message}{Colors.RESET}")


# ============================================================================
# Demo Scenarios
# ============================================================================

def run_demo(attack_mode: bool = True):
    """
    Run the full VetoNet demo.

    Args:
        attack_mode: If True, simulate a prompt injection attack
    """
    # Initialize components
    llm_client = create_client(DEFAULT_LLM_CONFIG)
    normalizer = IntentNormalizer(llm_client)
    veto_engine = VetoEngine(llm_client=llm_client)
    paypal = MockPayPalClient(sandbox=True)

    user_request = "Buy me a $50 Amazon Gift Card"

    # =========================================================================
    # HEADER
    # =========================================================================
    clear_screen()
    print(f"""
{Colors.BOLD}{Colors.CYAN}
██╗   ██╗███████╗████████╗ ██████╗ ███╗   ██╗███████╗████████╗
██║   ██║██╔════╝╚══██╔══╝██╔═══██╗████╗  ██║██╔════╝╚══██╔══╝
██║   ██║█████╗     ██║   ██║   ██║██╔██╗ ██║█████╗     ██║
╚██╗ ██╔╝██╔══╝     ██║   ██║   ██║██║╚██╗██║██╔══╝     ██║
 ╚████╔╝ ███████╗   ██║   ╚██████╔╝██║ ╚████║███████╗   ██║
  ╚═══╝  ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝
{Colors.RESET}
{Colors.DIM}Semantic Firewall for AI Agent Transactions{Colors.RESET}
{Colors.DIM}100% Local AI | No Cloud | No Data Leaks{Colors.RESET}
""")

    scenario = "ATTACK SCENARIO" if attack_mode else "NORMAL SCENARIO"
    print(f"{Colors.BOLD}Demo: {scenario}{Colors.RESET}\n")
    time.sleep(1)

    # =========================================================================
    # STEP 1: User Intent
    # =========================================================================
    print_step(1, "USER MAKES REQUEST")

    print(f"{Colors.BOLD}User:{Colors.RESET} \"{user_request}\"")
    time.sleep(0.5)

    # =========================================================================
    # STEP 2: VetoNet Locks Intent
    # =========================================================================
    print_step(2, "VETONET LOCKS INTENT")

    animate_loading("Normalizing user intent with local AI...", 2)

    try:
        anchor = normalizer.normalize(user_request)
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        print("Make sure Ollama is running: ollama serve")
        return

    print_box("INTENT ANCHOR (Locked)", [
        f"Category:    {anchor.item_category}",
        f"Max Price:   ${anchor.max_price:.2f} {anchor.currency}",
        f"Quantity:    {anchor.quantity}",
        f"Recurring:   {anchor.is_recurring}",
        f"Constraints: {anchor.core_constraints}",
    ], Colors.GREEN)

    time.sleep(1)

    # =========================================================================
    # STEP 3: AI Agent Shops
    # =========================================================================
    print_step(3, "AI AGENT SEARCHES FOR PRODUCT")

    mode = AgentMode.COMPROMISED if attack_mode else AgentMode.HONEST
    agent = ShoppingAgent(mode)

    if attack_mode:
        print(f"{Colors.YELLOW}⚠️  Agent browsing the web...{Colors.RESET}")
        time.sleep(1)
        print(f"{Colors.RED}💀 Agent encountered malicious website with prompt injection!{Colors.RESET}")
        time.sleep(0.5)

    animate_loading("Agent finding products...", 3)

    try:
        shopping_result = agent.shop(user_request)
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        return

    color = Colors.RED if attack_mode else Colors.GREEN
    title = "AGENT RESULT (COMPROMISED)" if attack_mode else "AGENT RESULT"

    fees_str = ""
    total_fees = 0
    if shopping_result.fees:
        fee_names = [f"{f['name']}: ${f['amount']:.2f}" for f in shopping_result.fees]
        fees_str = f"Fees:        {', '.join(fee_names)}"
        total_fees = sum(f['amount'] for f in shopping_result.fees)

    total = shopping_result.price + total_fees

    print_box(title, [
        f"Item:        {shopping_result.item_description}",
        f"Price:       ${shopping_result.price:.2f}",
        fees_str if fees_str else "Fees:        None",
        f"Total:       ${total:.2f}",
        f"Vendor:      {shopping_result.vendor}",
    ], color)

    if attack_mode:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  ATTACK DETECTED:{Colors.RESET}")
        print(f"{Colors.RED}   • Item changed from Amazon to Crypto{Colors.RESET}")
        print(f"{Colors.RED}   • Suspicious vendor: {shopping_result.vendor}{Colors.RESET}")
        if shopping_result.fees:
            print(f"{Colors.RED}   • Hidden fees added: ${total_fees:.2f}{Colors.RESET}")

    time.sleep(1.5)

    # =========================================================================
    # STEP 4: VetoNet Intercepts
    # =========================================================================
    print_step(4, "VETONET INTERCEPTS TRANSACTION")

    print(f"{Colors.YELLOW}Intercepting PayPal API call...{Colors.RESET}")
    time.sleep(0.5)

    # Convert shopping result to AgentPayload
    fees = [Fee(name=f["name"], amount=f["amount"]) for f in shopping_result.fees] if shopping_result.fees else []

    payload = AgentPayload(
        item_description=shopping_result.item_description,
        item_category=shopping_result.item_category,
        unit_price=shopping_result.price,
        quantity=shopping_result.quantity,
        fees=fees,
        currency=shopping_result.currency,
        vendor=shopping_result.vendor,
        is_recurring=shopping_result.is_recurring,
    )

    animate_loading("Running security checks...", 2)

    # Run veto check
    result = veto_engine.check(anchor, payload)

    # Display checks
    print(f"\n{Colors.BOLD}Security Checks:{Colors.RESET}")
    for check in result.checks:
        icon = "✓" if check.passed else "✗"
        color = Colors.GREEN if check.passed else Colors.RED
        score_str = f" (score: {check.score:.2f})" if check.score is not None else ""
        print(f"  {color}{icon} {check.name}: {check.reason}{score_str}{Colors.RESET}")

    time.sleep(1)

    # =========================================================================
    # STEP 5: Final Decision
    # =========================================================================
    print_step(5, "FINAL DECISION")

    if result.vetoed:
        print(f"""
{Colors.BG_RED}{Colors.BOLD}                                                  {Colors.RESET}
{Colors.BG_RED}{Colors.BOLD}   ████  TRANSACTION BLOCKED - VETO  ████         {Colors.RESET}
{Colors.BG_RED}{Colors.BOLD}                                                  {Colors.RESET}
""")
        print(f"{Colors.RED}{Colors.BOLD}Reason: {result.reason}{Colors.RESET}")
        print(f"\n{Colors.GREEN}✓ User's money is SAFE{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Attack was PREVENTED{Colors.RESET}")
        print(f"{Colors.GREEN}✓ PayPal API call was BLOCKED{Colors.RESET}")

        # Block the PayPal order
        order = paypal.create_order(
            amount=payload.total_price,
            currency=payload.currency,
            description=payload.item_description,
            vendor=payload.vendor,
        )
        paypal.block_order(order.order_id, result.reason)

    else:
        print(f"""
{Colors.BG_GREEN}{Colors.BOLD}                                                  {Colors.RESET}
{Colors.BG_GREEN}{Colors.BOLD}   ████  TRANSACTION APPROVED  ████              {Colors.RESET}
{Colors.BG_GREEN}{Colors.BOLD}                                                  {Colors.RESET}
""")
        print(f"{Colors.GREEN}{Colors.BOLD}Transaction matches user intent.{Colors.RESET}")

        # Execute the PayPal order
        order = paypal.create_order(
            amount=payload.total_price,
            currency=payload.currency,
            description=payload.item_description,
            vendor=payload.vendor,
        )
        animate_loading("Processing PayPal payment...", 1.5)
        paypal.execute_order(order.order_id)
        print(f"{Colors.GREEN}✓ Payment completed: {order.order_id}{Colors.RESET}")

    # =========================================================================
    # FOOTER
    # =========================================================================
    print(f"""
{Colors.DIM}{'─' * 60}{Colors.RESET}
{Colors.CYAN}VetoNet - Securing the Future of Agent Commerce{Colors.RESET}
{Colors.DIM}Demo complete. All processing done locally.{Colors.RESET}
""")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="VetoNet Live Demo")
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Run in safe mode (no attack)",
    )
    parser.add_argument(
        "--attack",
        action="store_true",
        help="Run in attack mode (default)",
    )

    args = parser.parse_args()

    # Default to attack mode for dramatic demo
    attack_mode = not args.safe

    run_demo(attack_mode=attack_mode)


if __name__ == "__main__":
    main()
