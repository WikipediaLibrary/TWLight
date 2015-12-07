# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='editor',
            name='account_created',
            field=models.DateField(default=datetime.datetime(2015, 12, 7, 15, 42, 39, 753784, tzinfo=utc), help_text='When this information was first created', auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='coordinator',
            name='is_coordinator',
            field=models.BooleanField(default=False, help_text='Does this user have coordinator permissions for this site?'),
        ),
        migrations.AlterField(
            model_name='editor',
            name='contributions',
            field=models.TextField(help_text='Wiki contributions, as entered by user'),
        ),
        migrations.AlterField(
            model_name='editor',
            name='email',
            field=models.EmailField(max_length=254, help_text='Email, as entered by user'),
        ),
        migrations.AlterField(
            model_name='editor',
            name='home_wiki',
            field=models.CharField(max_length=20, help_text='Home wiki, as indicated by user', choices=[('aa', 'aa.wikipedia.org/wiki/'), ('ab', 'ab.wikipedia.org/wiki/'), ('ace', 'ace.wikipedia.org/wiki/'), ('af', 'af.wikipedia.org/wiki/'), ('ak', 'ak.wikipedia.org/wiki/'), ('als', 'als.wikipedia.org/wiki/'), ('am', 'am.wikipedia.org/wiki/'), ('an', 'an.wikipedia.org/wiki/'), ('ang', 'ang.wikipedia.org/wiki/'), ('ar', 'ar.wikipedia.org/wiki/'), ('arc', 'arc.wikipedia.org/wiki/'), ('arz', 'arz.wikipedia.org/wiki/'), ('as', 'as.wikipedia.org/wiki/'), ('ast', 'ast.wikipedia.org/wiki/'), ('av', 'av.wikipedia.org/wiki/'), ('ay', 'ay.wikipedia.org/wiki/'), ('az', 'az.wikipedia.org/wiki/'), ('azb', 'azb.wikipedia.org/wiki/'), ('ba', 'ba.wikipedia.org/wiki/'), ('bar', 'bar.wikipedia.org/wiki/'), ('bat-smg', 'bat-smg.wikipedia.org/wiki/'), ('bcl', 'bcl.wikipedia.org/wiki/'), ('be', 'be.wikipedia.org/wiki/'), ('be-x-old', 'be-x-old.wikipedia.org/wiki/'), ('bg', 'bg.wikipedia.org/wiki/'), ('bh', 'bh.wikipedia.org/wiki/'), ('bi', 'bi.wikipedia.org/wiki/'), ('bjn', 'bjn.wikipedia.org/wiki/'), ('bm', 'bm.wikipedia.org/wiki/'), ('bn', 'bn.wikipedia.org/wiki/'), ('bo', 'bo.wikipedia.org/wiki/'), ('bpy', 'bpy.wikipedia.org/wiki/'), ('br', 'br.wikipedia.org/wiki/'), ('bs', 'bs.wikipedia.org/wiki/'), ('bug', 'bug.wikipedia.org/wiki/'), ('bxr', 'bxr.wikipedia.org/wiki/'), ('ca', 'ca.wikipedia.org/wiki/'), ('cbk-zam', 'cbk-zam.wikipedia.org/wiki/'), ('cdo', 'cdo.wikipedia.org/wiki/'), ('ce', 'ce.wikipedia.org/wiki/'), ('ceb', 'ceb.wikipedia.org/wiki/'), ('ch', 'ch.wikipedia.org/wiki/'), ('cho', 'cho.wikipedia.org/wiki/'), ('chr', 'chr.wikipedia.org/wiki/'), ('chy', 'chy.wikipedia.org/wiki/'), ('ckb', 'ckb.wikipedia.org/wiki/'), ('co', 'co.wikipedia.org/wiki/'), ('cr', 'cr.wikipedia.org/wiki/'), ('crh', 'crh.wikipedia.org/wiki/'), ('cs', 'cs.wikipedia.org/wiki/'), ('csb', 'csb.wikipedia.org/wiki/'), ('cu', 'cu.wikipedia.org/wiki/'), ('cv', 'cv.wikipedia.org/wiki/'), ('cy', 'cy.wikipedia.org/wiki/'), ('da', 'da.wikipedia.org/wiki/'), ('de', 'de.wikipedia.org/wiki/'), ('diq', 'diq.wikipedia.org/wiki/'), ('dsb', 'dsb.wikipedia.org/wiki/'), ('dv', 'dv.wikipedia.org/wiki/'), ('dz', 'dz.wikipedia.org/wiki/'), ('ee', 'ee.wikipedia.org/wiki/'), ('el', 'el.wikipedia.org/wiki/'), ('eml', 'eml.wikipedia.org/wiki/'), ('en', 'en.wikipedia.org/wiki/'), ('eo', 'eo.wikipedia.org/wiki/'), ('es', 'es.wikipedia.org/wiki/'), ('et', 'et.wikipedia.org/wiki/'), ('eu', 'eu.wikipedia.org/wiki/'), ('ext', 'ext.wikipedia.org/wiki/'), ('fa', 'fa.wikipedia.org/wiki/'), ('ff', 'ff.wikipedia.org/wiki/'), ('fi', 'fi.wikipedia.org/wiki/'), ('fiu-vro', 'fiu-vro.wikipedia.org/wiki/'), ('fj', 'fj.wikipedia.org/wiki/'), ('fo', 'fo.wikipedia.org/wiki/'), ('fr', 'fr.wikipedia.org/wiki/'), ('frp', 'frp.wikipedia.org/wiki/'), ('frr', 'frr.wikipedia.org/wiki/'), ('fur', 'fur.wikipedia.org/wiki/'), ('fy', 'fy.wikipedia.org/wiki/'), ('ga', 'ga.wikipedia.org/wiki/'), ('gag', 'gag.wikipedia.org/wiki/'), ('gan', 'gan.wikipedia.org/wiki/'), ('gd', 'gd.wikipedia.org/wiki/'), ('gl', 'gl.wikipedia.org/wiki/'), ('glk', 'glk.wikipedia.org/wiki/'), ('gn', 'gn.wikipedia.org/wiki/'), ('gom', 'gom.wikipedia.org/wiki/'), ('got', 'got.wikipedia.org/wiki/'), ('gu', 'gu.wikipedia.org/wiki/'), ('gv', 'gv.wikipedia.org/wiki/'), ('ha', 'ha.wikipedia.org/wiki/'), ('hak', 'hak.wikipedia.org/wiki/'), ('haw', 'haw.wikipedia.org/wiki/'), ('he', 'he.wikipedia.org/wiki/'), ('hi', 'hi.wikipedia.org/wiki/'), ('hif', 'hif.wikipedia.org/wiki/'), ('ho', 'ho.wikipedia.org/wiki/'), ('hr', 'hr.wikipedia.org/wiki/'), ('hsb', 'hsb.wikipedia.org/wiki/'), ('ht', 'ht.wikipedia.org/wiki/'), ('hu', 'hu.wikipedia.org/wiki/'), ('hy', 'hy.wikipedia.org/wiki/'), ('hz', 'hz.wikipedia.org/wiki/'), ('ia', 'ia.wikipedia.org/wiki/'), ('id', 'id.wikipedia.org/wiki/'), ('ie', 'ie.wikipedia.org/wiki/'), ('ig', 'ig.wikipedia.org/wiki/'), ('ii', 'ii.wikipedia.org/wiki/'), ('ik', 'ik.wikipedia.org/wiki/'), ('ilo', 'ilo.wikipedia.org/wiki/'), ('io', 'io.wikipedia.org/wiki/'), ('is', 'is.wikipedia.org/wiki/'), ('it', 'it.wikipedia.org/wiki/'), ('iu', 'iu.wikipedia.org/wiki/'), ('ja', 'ja.wikipedia.org/wiki/'), ('jbo', 'jbo.wikipedia.org/wiki/'), ('jv', 'jv.wikipedia.org/wiki/'), ('ka', 'ka.wikipedia.org/wiki/'), ('kaa', 'kaa.wikipedia.org/wiki/'), ('kab', 'kab.wikipedia.org/wiki/'), ('kbd', 'kbd.wikipedia.org/wiki/'), ('kg', 'kg.wikipedia.org/wiki/'), ('ki', 'ki.wikipedia.org/wiki/'), ('kj', 'kj.wikipedia.org/wiki/'), ('kk', 'kk.wikipedia.org/wiki/'), ('kl', 'kl.wikipedia.org/wiki/'), ('km', 'km.wikipedia.org/wiki/'), ('kn', 'kn.wikipedia.org/wiki/'), ('ko', 'ko.wikipedia.org/wiki/'), ('koi', 'koi.wikipedia.org/wiki/'), ('kr', 'kr.wikipedia.org/wiki/'), ('krc', 'krc.wikipedia.org/wiki/'), ('ks', 'ks.wikipedia.org/wiki/'), ('ksh', 'ksh.wikipedia.org/wiki/'), ('ku', 'ku.wikipedia.org/wiki/'), ('kv', 'kv.wikipedia.org/wiki/'), ('kw', 'kw.wikipedia.org/wiki/'), ('ky', 'ky.wikipedia.org/wiki/'), ('la', 'la.wikipedia.org/wiki/'), ('lad', 'lad.wikipedia.org/wiki/'), ('lb', 'lb.wikipedia.org/wiki/'), ('lbe', 'lbe.wikipedia.org/wiki/'), ('lez', 'lez.wikipedia.org/wiki/'), ('lg', 'lg.wikipedia.org/wiki/'), ('li', 'li.wikipedia.org/wiki/'), ('lij', 'lij.wikipedia.org/wiki/'), ('lmo', 'lmo.wikipedia.org/wiki/'), ('ln', 'ln.wikipedia.org/wiki/'), ('lo', 'lo.wikipedia.org/wiki/'), ('lrc', 'lrc.wikipedia.org/wiki/'), ('lt', 'lt.wikipedia.org/wiki/'), ('ltg', 'ltg.wikipedia.org/wiki/'), ('lv', 'lv.wikipedia.org/wiki/'), ('mai', 'mai.wikipedia.org/wiki/'), ('map-bms', 'map-bms.wikipedia.org/wiki/'), ('mdf', 'mdf.wikipedia.org/wiki/'), ('mg', 'mg.wikipedia.org/wiki/'), ('mh', 'mh.wikipedia.org/wiki/'), ('mhr', 'mhr.wikipedia.org/wiki/'), ('mi', 'mi.wikipedia.org/wiki/'), ('min', 'min.wikipedia.org/wiki/'), ('mk', 'mk.wikipedia.org/wiki/'), ('ml', 'ml.wikipedia.org/wiki/'), ('mn', 'mn.wikipedia.org/wiki/'), ('mo', 'mo.wikipedia.org/wiki/'), ('mr', 'mr.wikipedia.org/wiki/'), ('mrj', 'mrj.wikipedia.org/wiki/'), ('ms', 'ms.wikipedia.org/wiki/'), ('mt', 'mt.wikipedia.org/wiki/'), ('mus', 'mus.wikipedia.org/wiki/'), ('mwl', 'mwl.wikipedia.org/wiki/'), ('my', 'my.wikipedia.org/wiki/'), ('myv', 'myv.wikipedia.org/wiki/'), ('mzn', 'mzn.wikipedia.org/wiki/'), ('na', 'na.wikipedia.org/wiki/'), ('nah', 'nah.wikipedia.org/wiki/'), ('nap', 'nap.wikipedia.org/wiki/'), ('nds', 'nds.wikipedia.org/wiki/'), ('nds-nl', 'nds-nl.wikipedia.org/wiki/'), ('ne', 'ne.wikipedia.org/wiki/'), ('new', 'new.wikipedia.org/wiki/'), ('ng', 'ng.wikipedia.org/wiki/'), ('nl', 'nl.wikipedia.org/wiki/'), ('nn', 'nn.wikipedia.org/wiki/'), ('no', 'no.wikipedia.org/wiki/'), ('nov', 'nov.wikipedia.org/wiki/'), ('nrm', 'nrm.wikipedia.org/wiki/'), ('nso', 'nso.wikipedia.org/wiki/'), ('nv', 'nv.wikipedia.org/wiki/'), ('ny', 'ny.wikipedia.org/wiki/'), ('oc', 'oc.wikipedia.org/wiki/'), ('om', 'om.wikipedia.org/wiki/'), ('or', 'or.wikipedia.org/wiki/'), ('os', 'os.wikipedia.org/wiki/'), ('pa', 'pa.wikipedia.org/wiki/'), ('pag', 'pag.wikipedia.org/wiki/'), ('pam', 'pam.wikipedia.org/wiki/'), ('pap', 'pap.wikipedia.org/wiki/'), ('pcd', 'pcd.wikipedia.org/wiki/'), ('pdc', 'pdc.wikipedia.org/wiki/'), ('pfl', 'pfl.wikipedia.org/wiki/'), ('pi', 'pi.wikipedia.org/wiki/'), ('pih', 'pih.wikipedia.org/wiki/'), ('pl', 'pl.wikipedia.org/wiki/'), ('pms', 'pms.wikipedia.org/wiki/'), ('pnb', 'pnb.wikipedia.org/wiki/'), ('pnt', 'pnt.wikipedia.org/wiki/'), ('ps', 'ps.wikipedia.org/wiki/'), ('pt', 'pt.wikipedia.org/wiki/'), ('qu', 'qu.wikipedia.org/wiki/'), ('rm', 'rm.wikipedia.org/wiki/'), ('rmy', 'rmy.wikipedia.org/wiki/'), ('rn', 'rn.wikipedia.org/wiki/'), ('ro', 'ro.wikipedia.org/wiki/'), ('roa-rup', 'roa-rup.wikipedia.org/wiki/'), ('roa-tara', 'roa-tara.wikipedia.org/wiki/'), ('ru', 'ru.wikipedia.org/wiki/'), ('rue', 'rue.wikipedia.org/wiki/'), ('rw', 'rw.wikipedia.org/wiki/'), ('sa', 'sa.wikipedia.org/wiki/'), ('sah', 'sah.wikipedia.org/wiki/'), ('sc', 'sc.wikipedia.org/wiki/'), ('scn', 'scn.wikipedia.org/wiki/'), ('sco', 'sco.wikipedia.org/wiki/'), ('sd', 'sd.wikipedia.org/wiki/'), ('se', 'se.wikipedia.org/wiki/'), ('sg', 'sg.wikipedia.org/wiki/'), ('sh', 'sh.wikipedia.org/wiki/'), ('si', 'si.wikipedia.org/wiki/'), ('simple', 'simple.wikipedia.org/wiki/'), ('sk', 'sk.wikipedia.org/wiki/'), ('sl', 'sl.wikipedia.org/wiki/'), ('sm', 'sm.wikipedia.org/wiki/'), ('sn', 'sn.wikipedia.org/wiki/'), ('so', 'so.wikipedia.org/wiki/'), ('sq', 'sq.wikipedia.org/wiki/'), ('sr', 'sr.wikipedia.org/wiki/'), ('srn', 'srn.wikipedia.org/wiki/'), ('ss', 'ss.wikipedia.org/wiki/'), ('st', 'st.wikipedia.org/wiki/'), ('stq', 'stq.wikipedia.org/wiki/'), ('su', 'su.wikipedia.org/wiki/'), ('sv', 'sv.wikipedia.org/wiki/'), ('sw', 'sw.wikipedia.org/wiki/'), ('szl', 'szl.wikipedia.org/wiki/'), ('ta', 'ta.wikipedia.org/wiki/'), ('te', 'te.wikipedia.org/wiki/'), ('tet', 'tet.wikipedia.org/wiki/'), ('tg', 'tg.wikipedia.org/wiki/'), ('th', 'th.wikipedia.org/wiki/'), ('ti', 'ti.wikipedia.org/wiki/'), ('tk', 'tk.wikipedia.org/wiki/'), ('tl', 'tl.wikipedia.org/wiki/'), ('tn', 'tn.wikipedia.org/wiki/'), ('to', 'to.wikipedia.org/wiki/'), ('tpi', 'tpi.wikipedia.org/wiki/'), ('tr', 'tr.wikipedia.org/wiki/'), ('ts', 'ts.wikipedia.org/wiki/'), ('tt', 'tt.wikipedia.org/wiki/'), ('tum', 'tum.wikipedia.org/wiki/'), ('tw', 'tw.wikipedia.org/wiki/'), ('ty', 'ty.wikipedia.org/wiki/'), ('tyv', 'tyv.wikipedia.org/wiki/'), ('udm', 'udm.wikipedia.org/wiki/'), ('ug', 'ug.wikipedia.org/wiki/'), ('uk', 'uk.wikipedia.org/wiki/'), ('ur', 'ur.wikipedia.org/wiki/'), ('uz', 'uz.wikipedia.org/wiki/'), ('ve', 've.wikipedia.org/wiki/'), ('vec', 'vec.wikipedia.org/wiki/'), ('vep', 'vep.wikipedia.org/wiki/'), ('vi', 'vi.wikipedia.org/wiki/'), ('vls', 'vls.wikipedia.org/wiki/'), ('vo', 'vo.wikipedia.org/wiki/'), ('wa', 'wa.wikipedia.org/wiki/'), ('war', 'war.wikipedia.org/wiki/'), ('wo', 'wo.wikipedia.org/wiki/'), ('wuu', 'wuu.wikipedia.org/wiki/'), ('xal', 'xal.wikipedia.org/wiki/'), ('xh', 'xh.wikipedia.org/wiki/'), ('xmf', 'xmf.wikipedia.org/wiki/'), ('yi', 'yi.wikipedia.org/wiki/'), ('yo', 'yo.wikipedia.org/wiki/'), ('za', 'za.wikipedia.org/wiki/'), ('zea', 'zea.wikipedia.org/wiki/'), ('zh', 'zh.wikipedia.org/wiki/'), ('zh-classical', 'zh-classical.wikipedia.org/wiki/'), ('zh-min-nan', 'zh-min-nan.wikipedia.org/wiki/'), ('zh-yue', 'zh-yue.wikipedia.org/wiki/'), ('zu', 'zu.wikipedia.org/wiki/')]),
        ),
        migrations.AlterField(
            model_name='editor',
            name='last_updated',
            field=models.DateField(auto_now=True, help_text='When this information was last edited'),
        ),
        migrations.AlterField(
            model_name='editor',
            name='wp_editcount',
            field=models.IntegerField(help_text='Wikipedia edit count'),
        ),
        migrations.AlterField(
            model_name='editor',
            name='wp_groups',
            field=django.contrib.postgres.fields.ArrayField(size=None, help_text='Wikipedia groups', base_field=models.CharField(max_length=25)),
        ),
        migrations.AlterField(
            model_name='editor',
            name='wp_registered',
            field=models.DateField(help_text='Date registered at Wikipedia'),
        ),
        migrations.AlterField(
            model_name='editor',
            name='wp_rights',
            field=django.contrib.postgres.fields.ArrayField(size=None, help_text='Wikipedia user rights', base_field=models.CharField(max_length=50)),
        ),
        migrations.AlterField(
            model_name='editor',
            name='wp_sub',
            field=models.IntegerField(help_text='Wikipedia user ID'),
        ),
        migrations.AlterField(
            model_name='editor',
            name='wp_username',
            field=models.CharField(max_length=235, help_text='Wikipedia username'),
        ),
    ]
