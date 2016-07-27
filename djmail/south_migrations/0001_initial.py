# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Message'
        db.create_table('djmail_message', (
            ('uuid', self.gf('django.db.models.fields.CharField')(default='e4fca98e-8cff-11e4-92de-70188bfc3fc1', max_length=40, primary_key=True)),
            ('from_email', self.gf('django.db.models.fields.CharField')(max_length=1024, blank=True)),
            ('to_email', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('body_text', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('body_html', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=1024, blank=True)),
            ('data', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('retry_count', self.gf('django.db.models.fields.SmallIntegerField')(default=-1)),
            ('status', self.gf('django.db.models.fields.SmallIntegerField')(default=10)),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=50)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('sent_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('exception', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('djmail', ['Message'])

    def backwards(self, orm):
        # Deleting model 'Message'
        db.delete_table('djmail_message')

    models = {
        'djmail.message': {
            'Meta': {'ordering': "[u'created_at']", 'object_name': 'Message'},
            'body_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'body_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'exception': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '50'}),
            'retry_count': ('django.db.models.fields.SmallIntegerField', [], {'default': '-1'}),
            'sent_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '10'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'e4fd26de-8cff-11e4-92de-70188bfc3fc1'", 'max_length': '40', 'primary_key': 'True'})
        }
    }

    complete_apps = ['djmail']
