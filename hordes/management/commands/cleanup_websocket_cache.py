import logging
from django.core.management.base import BaseCommand
from django.core.cache import cache

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up stale WebSocket cache entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']

        if verbose:
            self.stdout.write("Starting WebSocket cache cleanup...")

        # Get all cache keys (this is Redis-specific)
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'scan_iter'):
            # Redis backend
            keys_to_check = []
            for key in cache._cache.scan_iter(match="ws_*"):
                keys_to_check.append(key.decode('utf-8'))
        else:
            # For other backends, we can't easily scan all keys
            self.stdout.write(
                self.style.WARNING(
                    "Cache backend doesn't support key scanning. "
                    "Cleanup will be limited."
                )
            )
            return

        if verbose:
            self.stdout.write(f"Found {len(keys_to_check)} WebSocket-related cache keys")

        cleaned_count = 0
        for key in keys_to_check:
            if key.startswith('ws_channel_') or key.startswith('ws_tent_'):
                if dry_run:
                    self.stdout.write(f"Would clean: {key}")
                else:
                    try:
                        cache.delete(key)
                        cleaned_count += 1
                        if verbose:
                            self.stdout.write(f"Cleaned: {key}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to clean {key}: {e}")
                        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Would clean {cleaned_count} cache entries")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully cleaned {cleaned_count} cache entries")
            )
