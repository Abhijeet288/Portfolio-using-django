import re
import requests

from django.core.cache import cache


SKIP_PATHS = ['/static/', '/favicon', '/admin/jsi18n/', '/__debug__/']

LANG_COLORS = {
    'JavaScript': '#f7df1e', 'Python': '#3b82f6', 'TypeScript': '#3178c6',
    'HTML': '#e44d26', 'CSS': '#264de4', 'Java': '#b07219', 'C++': '#f34b7d',
    'Ruby': '#cc342d', 'Go': '#00add8', 'Rust': '#dea584', 'Swift': '#fa7343',
    'Kotlin': '#7f52ff', 'Dart': '#00b4ab', 'Shell': '#89e051',
}


class VisitorLogMiddleware:
    """Logs unique page visits with geo-location and device info."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip static/admin paths
        path = request.path
        if any(path.startswith(s) for s in SKIP_PATHS):
            return self.get_response(request)

        # Only log GET requests to the main page
        if request.method == 'GET' and path in ('/', ''):
            self._log_visitor(request)

        return self.get_response(request)

    def _log_visitor(self, request):
        try:
            from Base.models import VisitorLog

            ip = self._get_ip(request)
            ua = request.META.get('HTTP_USER_AGENT', '')
            referrer = request.META.get('HTTP_REFERER', '')[:500]

            # Avoid duplicate logs: same IP within 30 minutes
            rate_key = f"visitor_log_{ip}"
            if cache.get(rate_key):
                return
            cache.set(rate_key, True, 1800)

            browser, os_name, device = self._parse_ua(ua)

            # Geo lookup (non-blocking, cached)
            country, city, region = self._get_geo(ip)

            VisitorLog.objects.create(
                ip_address=ip,
                country=country,
                city=city,
                region=region,
                user_agent=ua[:500],
                browser=browser,
                os=os_name,
                device=device,
                page=request.path,
                referrer=referrer,
            )
        except Exception:
            pass  # Never break the site due to logging errors

    def _get_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _parse_ua(self, ua):
        ua_lower = ua.lower()

        # Browser
        if 'edg/' in ua_lower:           browser = 'Edge'
        elif 'opr/' in ua_lower:          browser = 'Opera'
        elif 'chrome' in ua_lower:        browser = 'Chrome'
        elif 'firefox' in ua_lower:       browser = 'Firefox'
        elif 'safari' in ua_lower:        browser = 'Safari'
        else:                              browser = 'Other'

        # OS
        if 'windows' in ua_lower:         os_name = 'Windows'
        elif 'mac os' in ua_lower:        os_name = 'macOS'
        elif 'linux' in ua_lower:         os_name = 'Linux'
        elif 'android' in ua_lower:       os_name = 'Android'
        elif 'iphone' in ua_lower or 'ipad' in ua_lower:
                                           os_name = 'iOS'
        else:                              os_name = 'Other'

        # Device
        if any(m in ua_lower for m in ['mobile', 'android', 'iphone']):
            device = 'Mobile'
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            device = 'Tablet'
        else:
            device = 'Desktop'

        return browser, os_name, device

    def _get_geo(self, ip):
        if not ip or ip in ('127.0.0.1', 'localhost', '::1'):
            return 'Local', 'Local', 'Local'

        cache_key = f"geo_{ip}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            resp = requests.get(f'http://ip-api.com/json/{ip}?fields=country,city,regionName', timeout=3)
            data = resp.json()
            result = (
                data.get('country', ''),
                data.get('city', ''),
                data.get('regionName', ''),
            )
            cache.set(cache_key, result, 86400)  # cache 24 hrs
            return result
        except Exception:
            return '', '', ''
