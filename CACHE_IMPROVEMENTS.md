# WebSocket Cache Management Improvements

## Overview
This document outlines the improvements made to the WebSocket cache management system in the Golden Horde Django application.

## Issues Identified

### 1. Missing TTL (Time To Live)
- **Problem**: Cache entries were set without expiration times
- **Impact**: Memory leaks and stale data accumulation
- **Solution**: Added configurable TTL with support for long-running connections

### 2. No Error Handling
- **Problem**: Cache operations could fail silently
- **Impact**: Unpredictable behavior and difficult debugging
- **Solution**: Added comprehensive try-catch blocks with logging

### 3. Inconsistent Cache Key Management
- **Problem**: Cache keys were hardcoded throughout the code
- **Impact**: Difficult to maintain and prone to typos
- **Solution**: Created centralized `CacheManager` utility class

### 4. Missing Cache Configuration
- **Problem**: No proper Redis connection settings
- **Impact**: Poor performance and connection issues
- **Solution**: Added comprehensive Redis configuration

### 5. Long-Running Connection Support
- **Problem**: Fixed 1-hour TTL would break long-running connections
- **Impact**: Users couldn't stay connected for extended periods
- **Solution**: Implemented TTL extension on ping and configurable timeouts

## Improvements Made

### 1. CacheManager Utility Class
```python
class CacheManager:
    # Configurable TTL settings
    DEFAULT_WS_TTL = 3600  # 1 hour default
    EXTENDED_WS_TTL = 86400  # 24 hours for long connections
    
    @staticmethod
    def get_user_channel_key(username)
    @staticmethod
    def set_user_channel(username, channel_name, timeout=None)
    @staticmethod
    def get_user_channel(username)
    @staticmethod
    def delete_user_channel(username)
    @staticmethod
    def extend_user_channel_ttl(username, timeout=None)  # NEW
    @staticmethod
    def set_user_tent(username, tent_id, timeout=None)
    @staticmethod
    def get_user_tent(username)
    @staticmethod
    def extend_user_tent_ttl(username, timeout=None)  # NEW
```

### 2. Enhanced Settings Configuration

#### WebSocket Cache Configuration
```python
# Configurable TTL settings via environment variables
WS_CACHE_TTL = env.int('WS_CACHE_TTL', default=3600)  # 1 hour default
WS_CACHE_EXTENDED_TTL = env.int('WS_CACHE_EXTENDED_TTL', default=86400)  # 24 hours
```

#### Development Environment
```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
        "TIMEOUT": 3600,  # 1 hour default timeout
        "OPTIONS": {
            "MAX_ENTRIES": 1000,  # Maximum number of entries
        }
    }
}
```

#### Production Environment
```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": cache_redis_host,
        "TIMEOUT": 3600,  # 1 hour default timeout
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,  # Don't crash if Redis is down
        }
    }
}
```

### 3. Improved Channel Layers Configuration
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [channel_layers_redist_host],
            "capacity": 1500,  # Maximum messages in channel layer
            "expiry": 3600,  # Message expiry in seconds
            "group_expiry": 86400,  # Group expiry in seconds (24 hours)
            "channel_capacity": {
                "http.request": 100,
                "http.response!*": 100,
                "websocket.send!*": 100,
            },
        },
    },
}
```

### 4. Enhanced Consumer Error Handling
- Added logging for all cache operations
- Graceful handling of cache failures
- Better error messages for users
- **NEW**: TTL extension on ping for long-running connections

### 5. Cache Cleanup Management Command
Created `cleanup_websocket_cache.py` management command:
```bash
# Show what would be cleaned
python manage.py cleanup_websocket_cache --dry-run --verbose

# Actually clean the cache
python manage.py cleanup_websocket_cache --verbose
```

## Cache Keys Used

### WebSocket Channel Tracking
- **Key Pattern**: `ws_channel_{username}`
- **Value**: WebSocket channel name
- **TTL**: 24 hours (extendable on ping)
- **Purpose**: Track which channel a user is connected to

### User Tent Association
- **Key Pattern**: `ws_tent_{username}`
- **Value**: Tent ID
- **TTL**: 24 hours (extendable on ping)
- **Purpose**: Track which tent a user is currently in

## TTL System Explained

### Why We Need Both Settings and Consumer TTL

1. **Settings TIMEOUT (3600 seconds)**:
   - Default fallback timeout for cache operations
   - Used when no explicit timeout is provided
   - Example: `cache.set("key", "value")` uses this default

2. **Consumer TTL (explicitly set)**:
   - Overrides the default timeout
   - Ensures consistent behavior
   - Example: `cache.set("key", "value", timeout=86400)`

### Long-Running Connection Support

**Problem**: Users need to stay connected for several hours, but 1-hour TTL would break connections.

**Solution**: 
1. **Extended Initial TTL**: Set 24-hour TTL on connection
2. **Ping-Based Extension**: Each ping extends the TTL
3. **Configurable Timeouts**: Adjust via environment variables

```python
# On connection - set extended TTL
CacheManager.set_user_channel(username, channel_name, timeout=CacheManager.EXTENDED_WS_TTL)

# On ping - extend TTL
CacheManager.extend_user_channel_ttl(username)
CacheManager.extend_user_tent_ttl(username)
```

### Environment Variables

```bash
# Default TTL (1 hour)
WS_CACHE_TTL=3600

# Extended TTL for long connections (24 hours)
WS_CACHE_EXTENDED_TTL=86400

# For very long sessions (7 days)
WS_CACHE_EXTENDED_TTL=604800
```

## Best Practices Implemented

1. **Configurable TTL**: Environment variables control timeouts
2. **Long-Running Support**: Users can stay connected for extended periods
3. **Automatic Extension**: Active users' TTL extends on ping
4. **Graceful Degradation**: System works even if cache fails
5. **Comprehensive Logging**: All operations are logged
6. **Centralized Management**: All cache operations go through CacheManager
7. **Cleanup Tools**: Management command for manual cache cleanup

## Monitoring and Maintenance

### Regular Tasks
1. Monitor cache hit/miss ratios
2. Check for memory usage in Redis
3. Run cleanup command periodically
4. Review logs for cache errors
5. Monitor long-running connections

### Performance Considerations
1. Cache entries expire automatically after configured time
2. Active users' TTL extends on each ping
3. Redis connection pooling prevents connection exhaustion
4. Compression reduces memory usage
5. Timeout settings prevent hanging connections

## Testing

Run the test script to verify TTL behavior:
```bash
python test_cache_ttl.py
```

This demonstrates:
- Initial cache setup with extended TTL
- TTL extension on ping
- Cache persistence for long-running connections

## Future Improvements

1. **Cache Warming**: Pre-populate cache for frequently accessed data
2. **Metrics**: Add cache performance metrics
3. **Distributed Locking**: Implement proper locking for concurrent operations
4. **Cache Invalidation**: Smart invalidation based on data changes
5. **Connection Analytics**: Track connection duration and patterns 