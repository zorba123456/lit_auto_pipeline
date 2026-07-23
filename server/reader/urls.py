"""Reader app URL routing."""
from django.urls import path, register_converter
from . import views


class ArticleKeyConverter:
    regex = '[a-f0-9]{64}'
    def to_python(self, value):
        return value
    def to_url(self, value):
        return value

register_converter(ArticleKeyConverter, 'key')

urlpatterns = [
    path('', views.feed, name='reader-feed'),
    path('feed', views.feed, name='reader-feed-alt'),
    path('feed/rows', views.feed_rows, name='reader-rows'),
    path('article/<key:article_key>', views.article_detail, name='article-detail'),
]
