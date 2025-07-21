#!/usr/bin/env python3
"""
Test script to demonstrate WebSocket cache TTL behavior
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goldenhorde.settings')
django.setup()

from django.core.cache import cache
from hordes.consumers import CacheManager

def test_cache_ttl():
    """Test the cache TTL behavior"""
    print("=== WebSocket Cache TTL Test ===\n")
    
    # Test user
    test_user = "test_user_123"
    test_channel = "test_channel_456"
    test_tent = "tent_789"
    
    print(f"1. Setting initial cache entries for user: {test_user}")
    print(f"   - Channel: {test_channel}")
    print(f"   - Tent: {test_tent}")
    print(f"   - Default TTL: {CacheManager.DEFAULT_WS_TTL} seconds ({CacheManager.DEFAULT_WS_TTL/3600:.1f} hours)")
    print(f"   - Extended TTL: {CacheManager.EXTENDED_WS_TTL} seconds ({CacheManager.EXTENDED_WS_TTL/3600:.1f} hours)")
    
    # Set initial cache entries
    CacheManager.set_user_channel(test_user, test_channel, timeout=CacheManager.EXTENDED_WS_TTL)
    CacheManager.set_user_tent(test_user, test_tent, timeout=CacheManager.EXTENDED_WS_TTL)
    
    print("\n2. Verifying cache entries exist:")
    channel = CacheManager.get_user_channel(test_user)
    tent = CacheManager.get_user_tent(test_user)
    print(f"   - Channel in cache: {channel}")
    print(f"   - Tent in cache: {tent}")
    
    print("\n3. Simulating ping (extending TTL):")
    CacheManager.extend_user_channel_ttl(test_user)
    CacheManager.extend_user_tent_ttl(test_user)
    
    print("\n4. Verifying cache entries still exist after ping:")
    channel = CacheManager.get_user_channel(test_user)
    tent = CacheManager.get_user_tent(test_user)
    print(f"   - Channel in cache: {channel}")
    print(f"   - Tent in cache: {tent}")
    
    print("\n5. Cleaning up test data:")
    CacheManager.delete_user_channel(test_user)
    cache.delete(CacheManager.get_user_tent_key(test_user))
    
    print("\n=== Test Complete ===")
    print("\nKey Points:")
    print("- Users can stay connected for up to 24 hours (configurable)")
    print("- Each ping extends the TTL, so active users never get disconnected")
    print("- Inactive users' cache entries expire automatically")
    print("- Settings can be adjusted via environment variables:")
    print("  - WS_CACHE_TTL: Default TTL (default: 3600 seconds)")
    print("  - WS_CACHE_EXTENDED_TTL: Extended TTL (default: 86400 seconds)")

if __name__ == "__main__":
    test_cache_ttl() 