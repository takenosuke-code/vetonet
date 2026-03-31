"""
VetoNet CLI - Verify AI agent transactions from the command line.

Usage:
    vetonet --intent "$50 Amazon Gift Card" --payload '{"item_description": "..."}'
    vetonet -i "$50 Amazon Gift Card" -p @payload.json --provider groq
"""

import argparse
import json
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        description="VetoNet - Semantic Firewall for AI Agent Transactions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vetonet -i "$50 Amazon Gift Card" -p '{"item_description": "Amazon Card", "unit_price": 50, "vendor": "amazon.com"}'
  vetonet -i "$50 Amazon Gift Card" -p @payload.json --provider groq --api-key $GROQ_API_KEY
  vetonet -i "$50 Amazon Gift Card" -p @payload.json --json
        """,
    )

    parser.add_argument(
        "--intent", "-i",
        required=True,
        help="User intent (natural language string)",
    )

    parser.add_argument(
        "--payload", "-p",
        required=True,
        help="Transaction payload (JSON string or @filename for file)",
    )

    parser.add_argument(
        "--provider",
        default="ollama",
        choices=["ollama", "groq", "anthropic", "openai", "none"],
        help="LLM provider (default: ollama)",
    )

    parser.add_argument(
        "--api-key",
        help="API key for hosted providers (or use env var)",
    )

    parser.add_argument(
        "--model",
        help="Override default model for provider",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 0.1.4",
    )

    args = parser.parse_args()

    # Parse payload
    payload_str = args.payload
    if payload_str.startswith("@"):
        # Read from file
        filepath = payload_str[1:]
        try:
            with open(filepath) as f:
                payload = json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {filepath}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Parse as JSON string
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON payload: {e}", file=sys.stderr)
            sys.exit(1)

    # Get API key from args or environment
    api_key = args.api_key
    if not api_key and args.provider in ["groq", "anthropic", "openai"]:
        env_var = f"{args.provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            print(
                f"Error: {args.provider} requires API key. "
                f"Use --api-key or set {env_var} environment variable.",
                file=sys.stderr
            )
            sys.exit(1)

    # Run VetoNet
    try:
        from vetonet import VetoNet

        veto = VetoNet(
            provider=args.provider,
            model=args.model,
            api_key=api_key,
        )

        result = veto.verify(args.intent, payload)

        if args.json:
            # Output as JSON
            output = {
                "approved": result.approved,
                "reason": result.reason,
                "checks": [
                    {
                        "name": c.name,
                        "passed": c.passed,
                        "reason": c.reason,
                    }
                    for c in result.checks
                ],
            }
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            status = "APPROVED" if result.approved else "BLOCKED"
            symbol = "✓" if result.approved else "✗"
            print(f"{symbol} {status}: {result.reason}")

            if not result.approved:
                print("\nFailed checks:")
                for check in result.checks:
                    if not check.passed:
                        print(f"  - {check.name}: {check.reason}")

        sys.exit(0 if result.approved else 1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
