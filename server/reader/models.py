"""Django models for aes_workflow.db — managed=False."""
from django.db import models


class Entry(models.Model):
    """aes_workflow.db entries 表映射。"""
    article_key = models.CharField(max_length=64, primary_key=True)
    feed_id = models.TextField(blank=True, null=True)
    ingest_source = models.TextField(blank=True, null=True)
    lang = models.TextField(default='en', blank=True, null=True)
    title = models.TextField()
    title_zh_display = models.TextField(blank=True, null=True)
    title_prefix = models.TextField(blank=True, null=True)
    journal = models.TextField(blank=True, null=True)
    authors = models.TextField(blank=True, null=True)
    abstract = models.TextField(blank=True, null=True)
    doi = models.TextField(blank=True, null=True)
    pmid = models.TextField(blank=True, null=True)
    pmcid = models.TextField(blank=True, null=True)
    pii = models.TextField(blank=True, null=True)
    platform = models.TextField(blank=True, null=True)
    platform_id = models.TextField(blank=True, null=True)
    source_url = models.TextField(blank=True, null=True)
    publisher_url = models.TextField(blank=True, null=True)
    issue = models.TextField(blank=True, null=True)
    pages = models.TextField(blank=True, null=True)
    pub_date = models.TextField(blank=True, null=True)
    meta_status = models.TextField(default='meta_pending', blank=True, null=True)
    meta_tier = models.TextField(blank=True, null=True)
    fulltext_status = models.TextField(default='PDF_NONE', blank=True, null=True)
    pdf_path = models.TextField(blank=True, null=True)
    reading_note_status = models.TextField(default='none', blank=True, null=True)
    reading_note_zh = models.TextField(blank=True, null=True)
    doubao_read_url = models.TextField(blank=True, null=True)
    yuanbao_read_url = models.TextField(blank=True, null=True)
    has_video = models.IntegerField(default=0, blank=True, null=True)
    screening_status = models.TextField(blank=True, null=True)
    discovery_type = models.TextField(default='rss_feed', blank=True, null=True)
    wechat_discovery_sources = models.TextField(blank=True, null=True)
    submitter_role = models.TextField(blank=True, null=True)
    review_status = models.TextField(default='auto_approved', blank=True, null=True)
    ingest_at = models.TextField()
    updated_at = models.TextField()

    class Meta:
        db_table = 'entries'
        managed = False


class EntryIdentifier(models.Model):
    id_type = models.TextField()
    id_value = models.TextField()
    article_key = models.ForeignKey(Entry, on_delete=models.CASCADE, db_column='article_key')

    class Meta:
        db_table = 'entry_identifiers'
        managed = False
        unique_together = (('id_type', 'id_value'),)


class IngestLog(models.Model):
    id = models.AutoField(primary_key=True)
    ingest_source = models.TextField(blank=True, null=True)
    feed_file = models.TextField(blank=True, null=True)
    id_type = models.TextField(blank=True, null=True)
    id_value = models.TextField(blank=True, null=True)
    article_key = models.TextField(blank=True, null=True)
    duplicate = models.IntegerField(default=0, blank=True, null=True)
    created_at = models.TextField()

    class Meta:
        db_table = 'ingest_log'
        managed = False
