"""
Clear cached data and force regeneration on next run.
"""

import os

cache_file = 'data_cache.pkl'

if os.path.exists(cache_file):
    os.remove(cache_file)
    print(f"✅ Deleted cache file: {cache_file}")
    print("Next run will regenerate all data from scratch.")
else:
    print(f"ℹ️  No cache file found ({cache_file})")
    print("Data will be generated on next run.")
