from django.core.management.base import BaseCommand

from TWLight.resources.models import Partner


class Command(BaseCommand):
    def handle(self, *args, **options):
        partner_24 = Partner.objects.get(pk=24, company_name="AAAS")
        partner_24.new_tags = {
            "tags": [
                "life-sciences_tag",
                "physical-sciences_tag",
                "health-sciences_tag",
                "earth-sciences_tag",
            ]
        }
        partner_24.save()
        partner_49 = Partner.objects.get(pk=49, company_name="Adam Matthew")
        partner_49.new_tags = {"tags": ["culture_tag", "history_tag"]}
        partner_49.save()
        partner_101 = Partner.objects.get(pk=101, company_name="Al Manhal")
        partner_101.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_101.save()
        partner_60 = Partner.objects.get(pk=60, company_name="Alexander Street Press")
        partner_60.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_60.save()
        partner_84 = Partner.objects.get(
            pk=84, company_name="American National Biography Online"
        )
        partner_84.new_tags = {"tags": ["history_tag"]}
        partner_84.save()
        partner_62 = Partner.objects.get(
            pk=62, company_name="American Psychiatric Association"
        )
        partner_62.new_tags = {"tags": ["health-sciences_tag"]}
        partner_62.save()
        partner_48 = Partner.objects.get(
            pk=48, company_name="American Psychological Association"
        )
        partner_48.new_tags = {"tags": ["social-sciences_tag"]}
        partner_48.save()
        partner_102 = Partner.objects.get(pk=102, company_name="Ancestry")
        partner_102.new_tags = {"tags": ["history_tag"]}
        partner_102.save()
        partner_32 = Partner.objects.get(pk=32, company_name="Annual Reviews")
        partner_32.new_tags = {"tags": ["life-sciences_tag", "health-sciences_tag"]}
        partner_32.save()
        partner_11 = Partner.objects.get(pk=11, company_name="ASHA")
        partner_11.new_tags = {"tags": ["health-sciences_tag"]}
        partner_11.save()
        partner_47 = Partner.objects.get(pk=47, company_name="Baylor University Press")
        partner_47.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_47.save()
        partner_73 = Partner.objects.get(pk=73, company_name="Berg Fashion Library")
        partner_73.new_tags = {"tags": ["culture_tag"]}
        partner_73.save()
        partner_63 = Partner.objects.get(pk=63, company_name="BioOne")
        partner_63.new_tags = {"tags": ["life-sciences_tag"]}
        partner_63.save()
        partner_61 = Partner.even_not_available.get(pk=61, company_name="Bloomsbury")
        partner_61.new_tags = {"tags": ["culture_tag", "history_tag"]}
        partner_61.save()
        partner_31 = Partner.objects.get(pk=31, company_name="BMJ")
        partner_31.new_tags = {"tags": ["health-sciences_tag"]}
        partner_31.save()
        partner_59 = Partner.even_not_available.get(pk=59, company_name="Brill")
        partner_59.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_59.save()
        partner_14 = Partner.even_not_available.get(
            pk=14, company_name="British Newspaper Archive"
        )
        partner_14.new_tags = {"tags": ["history_tag"]}
        partner_14.save()
        partner_46 = Partner.objects.get(pk=46, company_name="Cairn")
        partner_46.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_46.save()
        partner_58 = Partner.objects.get(
            pk=58, company_name="Cambridge University Press"
        )
        partner_58.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_58.save()
        partner_64 = Partner.objects.get(pk=64, company_name="CEEOL")
        partner_64.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_64.save()
        partner_79 = Partner.objects.get(pk=79, company_name="Civilica")
        partner_79.new_tags = {"tags": ["physical-sciences_tag", "life-sciences_tag"]}
        partner_79.save()
        partner_15 = Partner.objects.get(pk=15, company_name="Cochrane")
        partner_15.new_tags = {"tags": ["health-sciences_tag"]}
        partner_15.save()
        partner_105 = Partner.objects.get(pk=105, company_name="De Gruyter")
        partner_105.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_105.save()
        partner_83 = Partner.objects.get(pk=83, company_name="Die Zeit")
        partner_83.new_tags = {"tags": ["culture_tag", "business-and-economics_tag"]}
        partner_83.save()
        partner_74 = Partner.objects.get(pk=74, company_name="Drama Online")
        partner_74.new_tags = {"tags": ["culture_tag", "languages-and-literature_tag"]}
        partner_74.save()
        partner_57 = Partner.objects.get(pk=57, company_name="EBSCO")
        partner_57.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_57.save()
        partner_71 = Partner.objects.get(
            pk=71, company_name="Economic & Political Weekly"
        )
        partner_71.new_tags = {
            "tags": ["social-sciences_tag", "business-and-economics_tag"]
        }
        partner_71.save()
        partner_45 = Partner.objects.get(
            pk=45, company_name="Edinburgh University Press"
        )
        partner_45.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_45.save()
        partner_9 = Partner.objects.get(pk=9, company_name="EDP Sciences")
        partner_9.new_tags = {
            "tags": ["physical-sciences_tag", "life-sciences_tag", "technology_tag"]
        }
        partner_9.save()
        partner_85 = Partner.objects.get(pk=85, company_name="Electronic Enlightenment")
        partner_85.new_tags = {"tags": ["history_tag"]}
        partner_85.save()
        partner_23 = Partner.even_not_available.get(
            pk=23, company_name="Elsevier ScienceDirect"
        )
        partner_23.new_tags = {
            "tags": [
                "life-sciences_tag",
                "health-sciences_tag",
                "physical-sciences_tag",
            ]
        }
        partner_23.save()
        partner_56 = Partner.objects.get(pk=56, company_name="Emerald")
        partner_56.new_tags = {
            "tags": [
                "education_tag",
                "technology_tag",
                "business-and-economics_tag",
                "social-sciences_tag",
            ]
        }
        partner_56.save()
        partner_44 = Partner.objects.get(pk=44, company_name="Érudit")
        partner_44.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_44.save()
        partner_43 = Partner.objects.get(pk=43, company_name="Fold3")
        partner_43.new_tags = {"tags": ["history_tag"]}
        partner_43.save()
        partner_8 = Partner.objects.get(pk=8, company_name="Foreign Affairs")
        partner_8.new_tags = {"tags": ["social-sciences_tag"]}
        partner_8.save()
        partner_22 = Partner.objects.get(pk=22, company_name="Future Science Group")
        partner_22.new_tags = {
            "tags": [
                "life-sciences_tag",
                "health-sciences_tag",
                "physical-sciences_tag",
            ]
        }
        partner_22.save()
        partner_55 = Partner.objects.get(pk=55, company_name="Gale")
        partner_55.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_55.save()
        partner_33 = Partner.objects.get(pk=33, company_name="HeinOnline")
        partner_33.new_tags = {"tags": ["law_tag"]}
        partner_33.save()
        partner_29 = Partner.even_not_available.get(pk=29, company_name="HighBeam")
        partner_29.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_29.save()
        partner_78 = Partner.objects.get(pk=78, company_name="ICE Publishing")
        partner_78.new_tags = {"tags": ["physical-sciences_tag", "technology_tag"]}
        partner_78.save()
        partner_42 = Partner.even_not_available.get(
            pk=42, company_name="International Monetary Fund"
        )
        partner_42.new_tags = {"tags": ["business-and-economics_tag"]}
        partner_42.save()
        partner_68 = Partner.objects.get(pk=68, company_name="Invaluable")
        partner_68.new_tags = {"tags": ["art_tag"]}
        partner_68.save()
        partner_77 = Partner.objects.get(pk=77, company_name="IWA Publishing")
        partner_77.new_tags = {"tags": ["earth-sciences_tag"]}
        partner_77.save()
        partner_54 = Partner.objects.get(pk=54, company_name="JSTOR")
        partner_54.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_54.save()
        partner_28 = Partner.even_not_available.get(pk=28, company_name="Keesings")
        partner_28.new_tags = {"tags": ["history_tag"]}
        partner_28.save()
        partner_72 = Partner.objects.get(pk=72, company_name="Kinige")
        partner_72.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_72.save()
        partner_18 = Partner.objects.get(pk=18, company_name="L'Harmattan")
        partner_18.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_18.save()
        partner_41 = Partner.objects.get(pk=41, company_name="Loeb Classical Library")
        partner_41.new_tags = {
            "tags": [
                "history_tag",
                "philosophy-and-religion_tag",
                "languages-and-literature_tag",
            ]
        }
        partner_41.save()
        partner_80 = Partner.objects.get(pk=80, company_name="Magiran")
        partner_80.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_80.save()
        partner_16 = Partner.objects.get(pk=16, company_name="McFarland")
        partner_16.new_tags = {
            "tags": [
                "culture_tag",
                "history_tag",
                "languages-and-literature_tag",
                "social-sciences_tag",
            ]
        }
        partner_16.save()
        partner_40 = Partner.objects.get(pk=40, company_name="Miramar")
        partner_40.new_tags = {"tags": ["history_tag"]}
        partner_40.save()
        partner_53 = Partner.objects.get(pk=53, company_name="MIT")
        partner_53.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_53.save()
        partner_27 = Partner.objects.get(pk=27, company_name="NewspaperARCHIVE.com")
        partner_27.new_tags = {"tags": ["history_tag", "culture_tag"]}
        partner_27.save()
        partner_26 = Partner.objects.get(pk=26, company_name="Newspapers.com")
        partner_26.new_tags = {"tags": ["history_tag", "culture_tag"]}
        partner_26.save()
        partner_106 = Partner.objects.get(pk=106, company_name="Nomos")
        partner_106.new_tags = {"tags": ["law_tag", "social-sciences_tag"]}
        partner_106.save()
        partner_81 = Partner.objects.get(pk=81, company_name="Noormags")
        partner_81.new_tags = {
            "tags": ["social-sciences_tag", "philosophy-and-religion_tag"]
        }
        partner_81.save()
        partner_17 = Partner.objects.get(pk=17, company_name="Numérique Premium")
        partner_17.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_17.save()
        partner_13 = Partner.objects.get(pk=13, company_name="OpenEdition")
        partner_13.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_13.save()
        partner_86 = Partner.objects.get(pk=86, company_name="Oxford Art Online")
        partner_86.new_tags = {"tags": ["art_tag"]}
        partner_86.save()
        partner_87 = Partner.objects.get(
            pk=87, company_name="Oxford Bibliographies Online"
        )
        partner_87.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_87.save()
        partner_88 = Partner.objects.get(
            pk=88, company_name="Oxford Dictionary of National Biography"
        )
        partner_88.new_tags = {"tags": ["history_tag"]}
        partner_88.save()
        partner_89 = Partner.objects.get(pk=89, company_name="Oxford Handbooks Online")
        partner_89.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_89.save()
        partner_93 = Partner.objects.get(pk=93, company_name="Oxford Journals")
        partner_93.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_93.save()
        partner_99 = Partner.objects.get(pk=99, company_name="Oxford Law")
        partner_99.new_tags = {"tags": ["law_tag"]}
        partner_99.save()
        partner_90 = Partner.objects.get(pk=90, company_name="Oxford Music Online")
        partner_90.new_tags = {"tags": ["music_tag"]}
        partner_90.save()
        partner_91 = Partner.objects.get(pk=91, company_name="Oxford Reference Online")
        partner_91.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_91.save()
        partner_92 = Partner.objects.get(
            pk=92, company_name="Oxford Scholarship Online"
        )
        partner_92.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_92.save()
        partner_52 = Partner.even_not_available.get(
            pk=52, company_name="Oxford University Press"
        )
        partner_52.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_52.save()
        partner_39 = Partner.objects.get(pk=39, company_name="Past Masters")
        partner_39.new_tags = {
            "tags": ["philosophy-and-religion_tag", "languages-and-literature_tag"]
        }
        partner_39.save()
        partner_51 = Partner.even_not_available.get(pk=51, company_name="Pelican Books")
        partner_51.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_51.save()
        partner_104 = Partner.objects.get(pk=104, company_name="PNAS")
        partner_104.new_tags = {
            "tags": [
                "physical-sciences_tag",
                "life-sciences_tag",
                "social-sciences_tag",
            ]
        }
        partner_104.save()
        partner_38 = Partner.objects.get(pk=38, company_name="Project MUSE")
        partner_38.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_38.save()
        partner_82 = Partner.objects.get(pk=82, company_name="ProQuest")
        partner_82.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_82.save()
        partner_25 = Partner.even_not_available.get(pk=25, company_name="Questia")
        partner_25.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_25.save()
        partner_100 = Partner.objects.get(
            pk=100,
            company_name="Répertoire International de Littérature Musicale (RILM)",
        )
        partner_100.new_tags = {"tags": ["music_tag"]}
        partner_100.save()
        partner_37 = Partner.objects.get(pk=37, company_name="RIPM")
        partner_37.new_tags = {"tags": ["music_tag"]}
        partner_37.save()
        partner_69 = Partner.objects.get(pk=69, company_name="Rock's Backpages")
        partner_69.new_tags = {"tags": ["music_tag"]}
        partner_69.save()
        partner_30 = Partner.objects.get(
            pk=30, company_name="Royal Pharmaceutical Society"
        )
        partner_30.new_tags = {"tags": ["health-sciences_tag"]}
        partner_30.save()
        partner_20 = Partner.objects.get(pk=20, company_name="Royal Society")
        partner_20.new_tags = {"tags": ["physical-sciences_tag", "life-sciences_tag"]}
        partner_20.save()
        partner_21 = Partner.objects.get(
            pk=21, company_name="Royal Society of Chemistry (RSC Gold)"
        )
        partner_21.new_tags = {"tags": ["physical-sciences_tag"]}
        partner_21.save()
        partner_50 = Partner.objects.get(pk=50, company_name="Sabinet")
        partner_50.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_50.save()
        partner_36 = Partner.even_not_available.get(pk=36, company_name="SAGE Stats")
        partner_36.new_tags = {"tags": ["social-sciences_tag"]}
        partner_36.save()
        partner_67 = Partner.objects.get(pk=67, company_name="Springer Nature")
        partner_67.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_67.save()
        partner_103 = Partner.objects.get(pk=103, company_name="Taxmann")
        partner_103.new_tags = {"tags": ["business-and-economics_tag"]}
        partner_103.save()
        partner_10 = Partner.objects.get(pk=10, company_name="Taylor & Francis")
        partner_10.new_tags = {"tags": ["multidisciplinary_tag"]}
        partner_10.save()
        partner_70 = Partner.objects.get(pk=70, company_name="Termsoup")
        partner_70.new_tags = {"tags": ["languages-and-literature_tag"]}
        partner_70.save()
        partner_12 = Partner.objects.get(pk=12, company_name="Tilastopaja")
        partner_12.new_tags = {"tags": ["culture_tag"]}
        partner_12.save()
        partner_75 = Partner.even_not_available.get(pk=75, company_name="Whitaker's")
        partner_75.new_tags = {"tags": ["history_tag"]}
        partner_75.save()
        partner_76 = Partner.objects.get(pk=76, company_name="Who's Who")
        partner_76.new_tags = {"tags": ["history_tag"]}
        partner_76.save()
        partner_35 = Partner.objects.get(pk=35, company_name="Women Writers Online")
        partner_35.new_tags = {"tags": ["languages-and-literature_tag"]}
        partner_35.save()
        partner_34 = Partner.objects.get(pk=34, company_name="World Bank")
        partner_34.new_tags = {"tags": ["business-and-economics_tag"]}
        partner_34.save()
        partner_19 = Partner.objects.get(pk=19, company_name="World Scientific")
        partner_19.new_tags = {
            "tags": [
                "life-sciences_tag",
                "health-sciences_tag",
                "physical-sciences_tag",
            ]
        }
        partner_19.save()
