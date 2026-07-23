"""Reader app views — 列表 + 中间页。"""
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.http import HttpResponse

from .models import Entry

PER_PAGE = 50


def feed(request):
    """订阅流列表页（主页面）。"""
    platform_filter = request.GET.get('platform', '').strip()
    discovery_filter = request.GET.get('type', '').strip()
    q = request.GET.get('q', '').strip()

    qs = _build_qs(platform_filter, discovery_filter, q)
    total = qs.count()
    entries = qs.order_by('-ingest_at')[:PER_PAGE]

    stats = _platform_stats()

    return render(request, 'reader/feed.html', {
        'entries': entries,
        'total': total,
        'stats': stats,
        'platform_filter': platform_filter,
        'discovery_filter': discovery_filter,
        'q': q,
        'has_next': len(entries) == PER_PAGE,
        'next_page': 2,
    })


def feed_rows(request):
    """HTMX 行片段 — 用于初始加载和无限滚动。"""
    page = int(request.GET.get('page', 1))
    platform_filter = request.GET.get('platform', '').strip()
    discovery_filter = request.GET.get('type', '').strip()
    q = request.GET.get('q', '').strip()

    qs = _build_qs(platform_filter, discovery_filter, q)
    offset = (page - 1) * PER_PAGE
    entries = qs.order_by('-ingest_at')[offset:offset + PER_PAGE]

    html = render_to_string('reader/_rows.html', {
        'entries': entries,
        'platform_filter': platform_filter,
        'discovery_filter': discovery_filter,
        'q': q,
        'has_next': len(entries) == PER_PAGE,
        'next_page': page + 1,
    })
    return HttpResponse(html)


def article_detail(request, article_key):
    """中间页 — 文章详情。"""
    entry = get_object_or_404(Entry, article_key=article_key)
    import json
    wechat_sources = None
    if entry.wechat_discovery_sources:
        try:
            wechat_sources = json.loads(entry.wechat_discovery_sources)
        except (json.JSONDecodeError, TypeError):
            wechat_sources = None
    return render(request, 'reader/article.html', {
        'entry': entry,
        'wechat_sources': wechat_sources,
    })


def _build_qs(platform_filter, discovery_filter, q):
    qs = Entry.objects.all()
    if platform_filter:
        qs = qs.filter(platform=platform_filter)
    if discovery_filter:
        qs = qs.filter(discovery_type=discovery_filter)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(authors__icontains=q) | Q(journal__icontains=q))
    return qs


def _platform_stats():
    stats = {}
    for row in Entry.objects.values('platform').annotate(cnt=Count('article_key')).order_by('-cnt'):
        stats[row['platform']] = row['cnt']
    return stats
