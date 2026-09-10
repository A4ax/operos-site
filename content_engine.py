#!/usr/bin/env python3
"""
Operos Content Engine
Automated AI content generation and publishing system
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.engine import main

if __name__ == '__main__':
    asyncio.run(main())
