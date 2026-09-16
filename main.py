#!/usr/bin/env python3
"""
Truck Mod Manager - Standalone entry point.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from truck_mod_manager.app import main

if __name__ == "__main__":
    main()
