"""
Interactive operator console for the ICSC plant.
Delegates to cli.operator.main for clean control interface without prompt-interrupting alerts.
Security alerts are monitored on the Security Dashboard (python -m cli.monitor).
"""

from cli.operator import main

if __name__ == "__main__":
    main()
