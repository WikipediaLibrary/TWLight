| Name                                                                                          |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|---------------------------------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| TWLight/applications/forms.py                                                                 |      148 |      108 |       24 |        0 |     23% |70-71, 93-117, 128-130, 137-144, 147-151, 154-159, 163-164, 167-184, 187-228, 247-297, 302-356 |
| TWLight/applications/helpers.py                                                               |       54 |       26 |       18 |        0 |     39% |130-148, 156-158, 162-168, 172-187, 195-221 |
| TWLight/applications/management/commands/applications\_example\_data.py                       |      104 |      104 |       34 |        0 |      0% |     1-226 |
| TWLight/applications/management/commands/notify\_applicants\_tou\_changes.py                  |       20 |       20 |        4 |        0 |      0% |      1-57 |
| TWLight/applications/management/commands/send\_coordinator\_reminders.py                      |       22 |       22 |        4 |        0 |      0% |      1-79 |
| TWLight/applications/migrations/0001\_initial\_squashed\_0029\_remove\_application\_hidden.py |       17 |        6 |        4 |        0 |     52% |     19-25 |
| TWLight/applications/models.py                                                                |      137 |       68 |       22 |        0 |     43% |27, 148, 151, 154-161, 174, 183-217, 236-239, 242-248, 251-255, 258-263, 266-274, 277-282, 290-299, 307-333, 339-346, 353-359, 366, 374 |
| TWLight/applications/signals.py                                                               |      101 |       70 |       36 |        0 |     23% |51-61, 75-81, 98-127, 135-214, 223-253 |
| TWLight/applications/templates/applications/application\_evaluation.html                      |      170 |      170 |        0 |        0 |      0% |     1-348 |
| TWLight/applications/templates/applications/application\_list.html                            |      233 |      233 |        0 |        0 |      0% |     1-255 |
| TWLight/applications/templates/applications/application\_list\_include.html                   |       64 |       64 |        0 |        0 |      0% |      1-65 |
| TWLight/applications/templates/applications/application\_list\_reviewable\_include.html       |      101 |      101 |        0 |        0 |      0% |     1-102 |
| TWLight/applications/templates/applications/apply.html                                        |       15 |       15 |        0 |        0 |      0% |      1-22 |
| TWLight/applications/templates/applications/confirm\_renewal.html                             |       18 |       18 |        0 |        0 |      0% |      1-25 |
| TWLight/applications/templates/applications/request\_for\_application.html                    |       29 |       29 |        0 |        0 |      0% |      1-77 |
| TWLight/applications/templates/applications/send.html                                         |       22 |       22 |        0 |        0 |      0% |      1-26 |
| TWLight/applications/templates/applications/send\_partner.html                                |       58 |       58 |        0 |        0 |      0% |     1-202 |
| TWLight/applications/templatetags/urlencode.py                                                |        7 |        2 |        0 |        0 |     71% |     13-14 |
| TWLight/applications/templatetags/version\_tags.py                                            |       17 |       10 |        0 |        0 |     41% |10-14, 19-23 |
| TWLight/applications/tests.py                                                                 |     1581 |     1392 |       76 |        0 |     11% |66, 111, 130-131, 138-139, 147-149, 158-159, 169-188, 195-196, 206-218, 229-269, 276-303, 310-345, 351-384, 388-394, 397-399, 406-413, 422-426, 435-465, 479-508, 516-582, 588-635, 639-642, 650-683, 686-717, 722-723, 726-730, 733-734, 737-739, 744-745, 748-752, 757-776, 781-785, 790-792, 797-801, 806-835, 845-879, 892-905, 911-939, 948-976, 985-1017, 1023-1031, 1034-1042, 1056-1066, 1072-1080, 1086-1096, 1102-1110, 1116-1126, 1132-1140, 1146-1156, 1162-1170, 1176-1186, 1192-1200, 1203-1209, 1212-1229, 1232-1249, 1252-1269, 1272-1307, 1310-1333, 1336-1359, 1373-1443, 1448-1466, 1469-1485, 1490-1504, 1507-1530, 1533-1588, 1592-1635, 1638-1651, 1656-1663, 1666-1672, 1675-1682, 1686-1692, 1695-1708, 1711-1725, 1730-1746, 1749-1759, 1764-1816, 1819-1855, 1858-1860, 1867-1896, 1909-1929, 1933-1950, 1956-1996, 2000-2001, 2004-2021, 2028-2050, 2057-2128, 2131-2176, 2182-2201, 2204-2223, 2226-2240, 2243-2259, 2264-2284, 2287-2300, 2307-2332, 2339-2358, 2366-2385, 2390-2403, 2407-2432, 2435-2512, 2520-2542, 2548-2562, 2565-2579, 2585-2615, 2624-2670, 2678-2743, 2747-2748, 2752-2775, 2785-2822, 2826-2859, 2862-2878, 2881-2950, 2953-2974, 2977-2998, 3003-3028, 3033-3066, 3074-3119, 3123-3124, 3128-3143, 3147-3155, 3164-3200, 3205-3218, 3222-3245, 3251-3284, 3289-3317, 3323-3344, 3347-3373, 3380-3390, 3396-3404 |
| TWLight/applications/views.py                                                                 |      606 |      495 |      178 |        0 |     14% |76-94, 100-120, 132-156, 159-174, 194-211, 218-226, 230-289, 308, 327-332, 335-339, 357-383, 386-392, 407-413, 420-428, 431, 444-511, 519-554, 565-590, 593-606, 611-622, 634-640, 645-652, 660-666, 676-684, 693-700, 705-712, 720-726, 746-806, 809-844, 847-896, 899-910, 917-1060, 1070-1084, 1092-1099, 1102-1137, 1140-1256, 1275-1298, 1301-1326, 1329-1331, 1335-1341, 1345-1349, 1352-1370, 1373-1411 |
| TWLight/collectedstatic/admin/img/README.txt                                                  |        7 |        7 |        0 |        0 |      0% |       1-7 |
| TWLight/collectedstatic/admin/js/vendor/jquery/LICENSE.txt                                    |       20 |       20 |        0 |        0 |      0% |      1-20 |
| TWLight/collectedstatic/admin/js/vendor/xregexp/LICENSE.txt                                   |       21 |       21 |        0 |        0 |      0% |      1-21 |
| TWLight/comments/\_\_init\_\_.py                                                              |        3 |        2 |        0 |        0 |     33% |       2-4 |
| TWLight/comments/forms.py                                                                     |       10 |       10 |        0 |        0 |      0% |      1-26 |
| TWLight/common/middleware/cache.py                                                            |       10 |       10 |        2 |        0 |      0% |      1-17 |
| TWLight/crons.py                                                                              |       72 |       72 |        0 |        0 |      0% |     1-102 |
| TWLight/emails/backends/mediawiki.py                                                          |      157 |      157 |       46 |        0 |      0% |     5-290 |
| TWLight/emails/forms.py                                                                       |       22 |       22 |        0 |        0 |      0% |      1-38 |
| TWLight/emails/models.py                                                                      |       37 |       20 |        4 |        0 |     41% |14, 17-18, 21-22, 27-46, 51, 54, 57, 60 |
| TWLight/emails/tasks.py                                                                       |      226 |      157 |       58 |        0 |     24% |114-159, 168-179, 195-222, 226-230, 239-361, 368-394, 401-428, 435-462, 475-515, 526-543, 552-561, 566-573 |
| TWLight/emails/templates/emails/access\_code\_email-body-html.html                            |       13 |       13 |        0 |        0 |      0% |      1-14 |
| TWLight/emails/templates/emails/access\_code\_email-body-text.html                            |        8 |        8 |        0 |        0 |      0% |       1-8 |
| TWLight/emails/templates/emails/access\_code\_email-subject.html                              |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/approval\_notification-body-html.html                         |       13 |       13 |        0 |        0 |      0% |      1-14 |
| TWLight/emails/templates/emails/approval\_notification-body-text.html                         |       16 |       16 |        0 |        0 |      0% |      1-16 |
| TWLight/emails/templates/emails/approval\_notification-subject.html                           |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/block\_hash\_changed-body-html.html                           |       11 |       11 |        0 |        0 |      0% |      1-11 |
| TWLight/emails/templates/emails/block\_hash\_changed-body-text.html                           |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/block\_hash\_changed-subject.html                             |        1 |        1 |        0 |        0 |      0% |         1 |
| TWLight/emails/templates/emails/comment\_notification\_coordinator-body-html.html             |       12 |       12 |        0 |        0 |      0% |      1-13 |
| TWLight/emails/templates/emails/comment\_notification\_coordinator-body-text.html             |       13 |       13 |        0 |        0 |      0% |      1-13 |
| TWLight/emails/templates/emails/comment\_notification\_coordinator-subject.html               |        3 |        3 |        0 |        0 |      0% |       1-3 |
| TWLight/emails/templates/emails/comment\_notification\_editors-body-html.html                 |       12 |       12 |        0 |        0 |      0% |      1-13 |
| TWLight/emails/templates/emails/comment\_notification\_editors-body-text.html                 |       13 |       13 |        0 |        0 |      0% |      1-13 |
| TWLight/emails/templates/emails/comment\_notification\_editors-subject.html                   |        3 |        3 |        0 |        0 |      0% |       1-3 |
| TWLight/emails/templates/emails/comment\_notification\_others-body-html.html                  |       14 |       14 |        0 |        0 |      0% |      1-15 |
| TWLight/emails/templates/emails/comment\_notification\_others-body-text.html                  |       10 |       10 |        0 |        0 |      0% |      1-10 |
| TWLight/emails/templates/emails/comment\_notification\_others-subject.html                    |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/coordinator\_reminder\_notification-body-html.html            |       41 |       41 |        0 |        0 |      0% |      1-46 |
| TWLight/emails/templates/emails/coordinator\_reminder\_notification-body-text.html            |       42 |       42 |        0 |        0 |      0% |      1-46 |
| TWLight/emails/templates/emails/coordinator\_reminder\_notification-subject.html              |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/rejection\_notification-body-html.html                        |       13 |       13 |        0 |        0 |      0% |      1-14 |
| TWLight/emails/templates/emails/rejection\_notification-body-text.html                        |       13 |       13 |        0 |        0 |      0% |      1-13 |
| TWLight/emails/templates/emails/rejection\_notification-subject.html                          |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/survey\_active\_user-body-html.html                           |       22 |       22 |        0 |        0 |      0% |      1-23 |
| TWLight/emails/templates/emails/survey\_active\_user-body-text.html                           |       25 |       25 |        0 |        0 |      0% |      1-25 |
| TWLight/emails/templates/emails/survey\_active\_user-subject.html                             |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/test-body-html.html                                           |        1 |        1 |        0 |        0 |      0% |         1 |
| TWLight/emails/templates/emails/test-body-text.html                                           |        1 |        1 |        0 |        0 |      0% |         1 |
| TWLight/emails/templates/emails/test-subject.html                                             |        1 |        1 |        0 |        0 |      0% |         1 |
| TWLight/emails/templates/emails/user\_renewal\_notice-body-html.html                          |       13 |       13 |        0 |        0 |      0% |      1-14 |
| TWLight/emails/templates/emails/user\_renewal\_notice-body-text.html                          |       13 |       13 |        0 |        0 |      0% |      1-13 |
| TWLight/emails/templates/emails/user\_renewal\_notice-subject.html                            |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/templates/emails/user\_retrieve\_monthly\_logins-body-html.html                |        9 |        9 |        0 |        0 |      0% |       1-9 |
| TWLight/emails/templates/emails/user\_retrieve\_monthly\_logins-body-text.html                |        3 |        3 |        0 |        0 |      0% |       1-3 |
| TWLight/emails/templates/emails/user\_retrieve\_monthly\_logins-subject.html                  |        1 |        1 |        0 |        0 |      0% |         1 |
| TWLight/emails/templates/emails/waitlist\_notification-body-html.html                         |       14 |       14 |        0 |        0 |      0% |      1-15 |
| TWLight/emails/templates/emails/waitlist\_notification-body-text.html                         |       14 |       14 |        0 |        0 |      0% |      1-14 |
| TWLight/emails/templates/emails/waitlist\_notification-subject.html                           |        4 |        4 |        0 |        0 |      0% |       1-4 |
| TWLight/emails/tests.py                                                                       |      492 |      412 |        0 |        0 |     16% |45-59, 62-74, 77-81, 88-97, 105-115, 123-140, 148-169, 177-184, 192-224, 235-238, 242-245, 250-256, 264-268, 272-275, 279-283, 289-291, 297-299, 305-307, 311-316, 320-332, 340-347, 355-365, 371-386, 393-396, 403-408, 415-419, 426-430, 437-441, 448-466, 476-512, 521-539, 549-586, 596-648, 654-665, 668-717, 730-842, 851-866 |
| TWLight/emails/views.py                                                                       |       36 |       36 |        6 |        0 |      0% |      1-61 |
| TWLight/ezproxy/tests.py                                                                      |       21 |       11 |        2 |        0 |     43% |     24-65 |
| TWLight/ezproxy/views.py                                                                      |       57 |       35 |       16 |        0 |     30% |30-62, 69-99, 114 |
| TWLight/forms.py                                                                              |       34 |       16 |        6 |        0 |     45% |     26-42 |
| TWLight/helpers.py                                                                            |        8 |        4 |        0 |        0 |     50% |      8-12 |
| TWLight/i18n/management/commands/makemessages.py                                              |        5 |        5 |        0 |        0 |      0% |      1-12 |
| TWLight/i18n/urls.py                                                                          |        8 |        3 |        2 |        0 |     50% |     14-16 |
| TWLight/i18n/views.py                                                                         |      109 |       74 |       36 |        0 |     24% |41-77, 82-98, 205-214, 217-230, 238-241, 249-253, 256-266, 269-292, 295, 302-315, 337 |
| TWLight/message\_storage.py                                                                   |        5 |        5 |        0 |        0 |      0% |      1-12 |
| TWLight/resources/admin.py                                                                    |      123 |       61 |       26 |        0 |     42% |54, 61-65, 70, 118-228, 244 |
| TWLight/resources/autocomplete\_light\_registry.py                                            |        7 |        7 |        0 |        0 |      0% |      1-20 |
| TWLight/resources/filters.py                                                                  |       62 |       33 |       16 |        0 |     37% |44-55, 64-68, 94-108, 113-126, 140-143, 150-151 |
| TWLight/resources/forms.py                                                                    |       31 |       16 |        0 |        0 |     48% |16-35, 52-56 |
| TWLight/resources/helpers.py                                                                  |       96 |       64 |       26 |        3 |     30% |11-24, 47-89, 108-119, 145, 170-185, 211->213, 215, 240-247, 254-277, 282-302 |
| TWLight/resources/management/commands/proxy\_waitlist\_disable.py                             |       15 |       15 |        4 |        0 |      0% |      1-27 |
| TWLight/resources/management/commands/resources\_example\_data.py                             |       99 |       99 |       40 |        0 |      0% |     1-212 |
| TWLight/resources/migrations/0001\_initial\_squashed\_0062\_auto\_20190220\_1639.py           |       32 |       17 |        8 |        0 |     38% |25-30, 39-43, 47-53, 57-60 |
| TWLight/resources/migrations/0074\_run\_update\_new\_tags.py                                  |        7 |        1 |        0 |        0 |     86% |         6 |
| TWLight/resources/models.py                                                                   |      220 |       52 |       22 |        0 |     70% |42-43, 83-84, 87, 357, 360-403, 410, 414, 418, 422, 426-440, 444, 451, 456, 460, 471-492, 500, 566, 570, 610, 654, 657, 660 |
| TWLight/resources/signals.py                                                                  |        8 |        1 |        0 |        0 |     88% |        11 |
| TWLight/resources/templates/resources/collection\_tile.html                                   |       63 |       63 |        0 |        0 |      0% |      1-63 |
| TWLight/resources/templates/resources/csv\_form.html                                          |       15 |       15 |        0 |        0 |      0% |      1-17 |
| TWLight/resources/templates/resources/filter\_section.html                                    |       56 |       56 |        0 |        0 |      0% |      1-56 |
| TWLight/resources/templates/resources/merge\_suggestion.html                                  |      155 |      155 |        0 |        0 |      0% |     1-172 |
| TWLight/resources/templates/resources/partner\_detail.html                                    |       41 |       41 |        0 |        0 |      0% |      1-80 |
| TWLight/resources/templates/resources/partner\_detail\_apply.html                             |      173 |      173 |        0 |        0 |      0% |     1-175 |
| TWLight/resources/templates/resources/partner\_detail\_stats.html                             |       65 |       65 |        0 |        0 |      0% |      1-65 |
| TWLight/resources/templates/resources/partner\_detail\_timeline.html                          |      218 |      218 |        0 |        0 |      0% |     1-218 |
| TWLight/resources/templates/resources/partner\_list.html                                      |      112 |      112 |        0 |        0 |      0% |     1-119 |
| TWLight/resources/templates/resources/partner\_users.html                                     |       20 |       20 |        0 |        0 |      0% |      1-91 |
| TWLight/resources/templates/resources/suggest.html                                            |      223 |      223 |        0 |        0 |      0% |     1-232 |
| TWLight/resources/templates/resources/suggestion\_confirm\_delete.html                        |       11 |       11 |        0 |        0 |      0% |      1-14 |
| TWLight/resources/templatetags/twlight\_removetags.py                                         |       12 |        7 |        0 |        0 |     42% |     11-17 |
| TWLight/resources/tests.py                                                                    |      734 |      615 |       32 |        0 |     16% |59-98, 104-113, 119-125, 128, 131-133, 139-155, 159-160, 163-174, 178-189, 196-205, 214-226, 232-243, 252-267, 270-280, 283-296, 299-322, 325-346, 349-370, 377-389, 392-402, 409-418, 428-452, 461-473, 482-483, 489-493, 499-510, 516-530, 538-549, 561-563, 571-586, 594-609, 616-634, 644-674, 680-703, 706-730, 733-754, 760-783, 787-795, 802-817, 824-839, 845-860, 866-931, 935-936, 939-948, 954-965, 975-986, 994-1005, 1013-1024, 1031-1042, 1049-1060, 1068-1079, 1086-1098, 1105-1117, 1124-1134, 1145-1174, 1192-1249, 1257-1277, 1281-1282, 1288-1297, 1303-1318, 1324-1336, 1342-1354, 1360-1396, 1400-1401, 1408-1418, 1426-1458, 1463-1477 |
| TWLight/resources/views.py                                                                    |      279 |      209 |       56 |        0 |     21% |51-70, 79-166, 175-279, 288-310, 313-328, 352-365, 386-395, 402-433, 444-458, 471-485, 489, 492-525, 529-564, 574-580, 588-599, 629-633, 637-639, 646-660, 663-696 |
| TWLight/runner.py                                                                             |       39 |        2 |        4 |        1 |     93% |     49-50 |
| TWLight/settings/base.py                                                                      |      118 |        7 |       16 |        1 |     94% |90-91, 226-237 |
| TWLight/settings/helpers.py                                                                   |       23 |       23 |        8 |        0 |      0% |      1-82 |
| TWLight/settings/heroku.py                                                                    |        7 |        7 |        0 |        0 |      0% |      1-17 |
| TWLight/settings/local.py                                                                     |       10 |        0 |        2 |        1 |     92% |    18->30 |
| TWLight/settings/production.py                                                                |        3 |        3 |        0 |        0 |      0% |      9-14 |
| TWLight/settings/server.py                                                                    |       18 |       18 |        0 |        0 |      0% |      9-43 |
| TWLight/settings/staging.py                                                                   |        3 |        3 |        0 |        0 |      0% |      9-14 |
| TWLight/templates/400.html                                                                    |       22 |       22 |        0 |        0 |      0% |      1-26 |
| TWLight/templates/403.html                                                                    |       22 |       22 |        0 |        0 |      0% |      1-26 |
| TWLight/templates/404.html                                                                    |       22 |       22 |        0 |        0 |      0% |      1-26 |
| TWLight/templates/500/500.html                                                                |       61 |       61 |        0 |        0 |      0% |      1-61 |
| TWLight/templates/about.html                                                                  |       73 |       73 |        0 |        0 |      0% |     1-220 |
| TWLight/templates/accesscode\_changelist.html                                                 |        4 |        4 |        0 |        0 |      0% |       1-6 |
| TWLight/templates/comments/list.html                                                          |       16 |       16 |        0 |        0 |      0% |      1-18 |
| TWLight/templates/contact.html                                                                |       44 |       44 |        0 |        0 |      0% |      1-48 |
| TWLight/templates/eds\_search\_endpoint.html                                                  |       15 |       15 |        0 |        0 |      0% |      1-22 |
| TWLight/templates/header\_partial\_b4.html                                                    |      135 |      135 |        0 |        0 |      0% |     1-135 |
| TWLight/templates/homepage.html                                                               |      367 |      367 |        0 |        0 |      0% |     1-380 |
| TWLight/templates/login\_partial.html                                                         |       91 |       91 |        0 |        0 |      0% |      1-92 |
| TWLight/templates/message\_partial.html                                                       |       44 |       44 |        0 |        0 |      0% |      1-44 |
| TWLight/templates/new\_base.html                                                              |      141 |      141 |        0 |        0 |      0% |     1-141 |
| TWLight/templates/partner\_carousel.html                                                      |       99 |       99 |        0 |        0 |      0% |      1-99 |
| TWLight/templates/registration/login.html                                                     |       20 |       20 |        0 |        0 |      0% |      1-30 |
| TWLight/templates/registration/password\_change\_form.html                                    |       13 |       13 |        0 |        0 |      0% |      1-17 |
| TWLight/templates/registration/password\_reset\_form.html                                     |       18 |       18 |        0 |        0 |      0% |      1-22 |
| TWLight/tests.py                                                                              |      542 |      431 |        2 |        0 |     20% |55-56, 59, 70, 104-108, 112-113, 116-117, 123-133, 139-146, 153-160, 167-175, 182-190, 196-204, 210-217, 224-232, 238-245, 251-259, 265-273, 279-287, 293-301, 307-315, 321-333, 339-346, 352-360, 368-382, 388-402, 408-416, 422-435, 441-452, 458-466, 472-482, 492-497, 506, 517-719, 722-743, 755-759, 766-796, 803-827, 837-869, 877-902, 908-909, 915-916, 924-931, 937-946, 953-958, 966-978, 990-997, 1003-1011, 1018-1032, 1039-1052, 1060-1082, 1091-1114, 1120-1153, 1161-1175, 1183-1199, 1207-1223 |
| TWLight/urls.py                                                                               |       25 |        3 |        2 |        1 |     85% |   107-112 |
| TWLight/users/admin.py                                                                        |       79 |       17 |       12 |        0 |     68% |88-93, 98-105, 110, 137-140, 167 |
| TWLight/users/factories.py                                                                    |       44 |        1 |        0 |        0 |     98% |        77 |
| TWLight/users/forms.py                                                                        |       94 |       51 |        2 |        0 |     45% |30-47, 60-61, 64-65, 76-79, 91-95, 112-134, 149-161, 174-188, 205-222 |
| TWLight/users/groups.py                                                                       |       13 |        6 |        0 |        0 |     54% |28-29, 41-44 |
| TWLight/users/helpers/authorizations.py                                                       |       28 |       21 |       10 |        0 |     18% |18, 40-58, 72-82, 97-110 |
| TWLight/users/helpers/editor\_data.py                                                         |       85 |       64 |       26 |        0 |     19% |27-42, 62-66, 82-109, 126-128, 146-151, 168-171, 199-206, 222-235, 252-260, 294-313 |
| TWLight/users/helpers/validation.py                                                           |       17 |       10 |        8 |        0 |     28% |20-30, 42-49 |
| TWLight/users/management/commands/retrieve\_monthly\_users.py                                 |       21 |       21 |        2 |        0 |      0% |      1-53 |
| TWLight/users/management/commands/survey\_active\_users.py                                    |       52 |       52 |       12 |        0 |      0% |     2-153 |
| TWLight/users/management/commands/test\_email.py                                              |       15 |        8 |        0 |        0 |     47% |14-19, 27-41 |
| TWLight/users/management/commands/update\_twl\_talk\_page.py                                  |       15 |       15 |        2 |        0 |      0% |      1-29 |
| TWLight/users/management/commands/user\_example\_data.py                                      |       45 |       45 |       14 |        0 |      0% |     1-101 |
| TWLight/users/management/commands/user\_renewal\_notice.py                                    |       23 |       23 |        4 |        0 |      0% |      1-73 |
| TWLight/users/management/commands/user\_update\_eligibility.py                                |       45 |       45 |       16 |        0 |      0% |     1-127 |
| TWLight/users/migrations/0001\_squashed\_0037\_auto\_20190117\_1008.py                        |       24 |       11 |        2 |        0 |     50% |19-20, 29-36, 44-45 |
| TWLight/users/migrations/0003\_auto\_20160406\_2128.py                                        |        8 |        2 |        0 |        0 |     75% |     13-14 |
| TWLight/users/migrations/0010\_auto\_20160706\_1439.py                                        |       13 |        7 |        2 |        0 |     40% |     13-20 |
| TWLight/users/migrations/0026\_create\_restricted.py                                          |        8 |        2 |        0 |        0 |     75% |     13-14 |
| TWLight/users/migrations/0048\_reset\_tou\_for\_all\_users.py                                 |       11 |        6 |        4 |        0 |     33% |     10-15 |
| TWLight/users/migrations/0053\_twl\_team\_user.py                                             |        9 |        1 |        0 |        0 |     89% |        10 |
| TWLight/users/migrations/0055\_authorization\_data\_partners\_foreignkey\_to\_manytomany.py   |        9 |        3 |        2 |        0 |     55% |     13-16 |
| TWLight/users/migrations/0057\_expire\_all\_sessions.py                                       |       15 |        6 |        2 |        0 |     53% |     13-21 |
| TWLight/users/migrations/0061\_make\_staff\_superusers\_wp\_eligible.py                       |       10 |        5 |        4 |        0 |     36% |       5-9 |
| TWLight/users/migrations/0062\_delete\_hanging\_userless\_bundle\_auths.py                    |        7 |        2 |        0 |        0 |     71% |       5-6 |
| TWLight/users/migrations/0063\_check\_terms\_and\_bundle\_eligibility.py                      |       10 |        5 |        4 |        0 |     36% |      5-11 |
| TWLight/users/migrations/0066\_move\_editcounts\_to\_log.py                                   |       20 |       15 |        6 |        0 |     19% |      7-25 |
| TWLight/users/migrations/0068\_userprofile\_project\_page\_2021\_notification\_sent.py        |        8 |        2 |        0 |        0 |     75% |       8-9 |
| TWLight/users/migrations/0085\_delete\_duplicate\_bundle\_authorizations.py                   |        8 |        2 |        0 |        0 |     75% |     11-13 |
| TWLight/users/models.py                                                                       |      377 |      227 |       86 |        0 |     32% |89, 101, 104-110, 131-134, 208, 216-222, 232-237, 371-372, 382-385, 395-398, 415-424, 441-450, 468-478, 498-523, 540-566, 580-584, 598-602, 616-620, 635-639, 654-659, 668-671, 678-681, 694-700, 703-704, 719-720, 735-749, 766-794, 853-917, 921, 924, 1022-1040, 1044-1072, 1086-1097, 1104-1118, 1124-1134, 1143-1151, 1158-1169, 1177-1182, 1189-1194, 1205-1213 |
| TWLight/users/oauth.py                                                                        |      299 |      261 |       58 |        0 |     11% |37-58, 62-66, 73-76, 84-85, 103-113, 117-125, 133, 138-153, 157-167, 170-172, 188-222, 225-295, 300-303, 317-434, 443-616 |
| TWLight/users/serializers.py                                                                  |       32 |       11 |        2 |        0 |     62% |     16-33 |
| TWLight/users/signals.py                                                                      |       96 |       68 |       52 |        0 |     19% |35-38, 44, 50, 56-57, 69-94, 105-176, 188-198 |
| TWLight/users/templates/users/authorization\_confirm\_return.html                             |       12 |       12 |        0 |        0 |      0% |      1-16 |
| TWLight/users/templates/users/available\_collection\_tile.html                                |       93 |       93 |        0 |        0 |      0% |      1-93 |
| TWLight/users/templates/users/collections\_section.html                                       |      103 |      103 |        0 |        0 |      0% |     1-103 |
| TWLight/users/templates/users/editor\_detail.html                                             |       60 |       60 |        0 |        0 |      0% |      1-73 |
| TWLight/users/templates/users/editor\_detail\_data.html                                       |      327 |      327 |        0 |        0 |      0% |     1-328 |
| TWLight/users/templates/users/editor\_update.html                                             |        6 |        6 |        0 |        0 |      0% |      1-10 |
| TWLight/users/templates/users/eligibility\_modal.html                                         |       71 |       71 |        0 |        0 |      0% |      1-71 |
| TWLight/users/templates/users/filter\_section.html                                            |       84 |       84 |        0 |        0 |      0% |      1-84 |
| TWLight/users/templates/users/language\_form.html                                             |       30 |       30 |        0 |        0 |      0% |      1-34 |
| TWLight/users/templates/users/my\_applications.html                                           |       48 |       48 |        0 |        0 |      0% |      1-54 |
| TWLight/users/templates/users/preferences.html                                                |      102 |      102 |        0 |        0 |      0% |     1-103 |
| TWLight/users/templates/users/redesigned\_my\_library.html                                    |      240 |      240 |        0 |        0 |      0% |     1-246 |
| TWLight/users/templates/users/restrict\_data.html                                             |       19 |       19 |        0 |        0 |      0% |      1-29 |
| TWLight/users/templates/users/terms.html                                                      |      226 |      226 |        0 |        0 |      0% |     1-427 |
| TWLight/users/templates/users/user\_collection\_tile.html                                     |      167 |      167 |        0 |        0 |      0% |     1-167 |
| TWLight/users/templates/users/user\_confirm\_delete.html                                      |       18 |       18 |        0 |        0 |      0% |      1-23 |
| TWLight/users/templates/users/user\_detail.html                                               |       15 |       15 |        0 |        0 |      0% |      1-25 |
| TWLight/users/templates/users/user\_email\_preferences.html                                   |       28 |       28 |        0 |        0 |      0% |      1-28 |
| TWLight/users/templatetags/twlight\_perms.py                                                  |       30 |       19 |       10 |        0 |     28% |13-21, 27-31, 37-41 |
| TWLight/users/tests.py                                                                        |     1334 |     1174 |        8 |        0 |     12% |106-109, 115-150, 154-163, 169, 175-177, 181-186, 190-196, 200-213, 217-243, 247-252, 256-268, 272-320, 327-344, 347-364, 368-401, 405-458, 464-470, 478-503, 510-523, 528-551, 557-571, 577-600, 606-638, 645-664, 672-681, 687-700, 704-717, 726-736, 744-766, 774-806, 810-832, 838-848, 854-860, 866-872, 879-885, 892-924, 931-949, 956-959, 965-991, 995-996, 999-1000, 1003-1004, 1007-1008, 1011-1012, 1015-1016, 1027-1174, 1186-1214, 1223-1291, 1299-1319, 1326-1352, 1361-1390, 1397-1399, 1406-1416, 1423-1439, 1442-1493, 1502-1560, 1567-1623, 1630-1687, 1694-1710, 1717-1733, 1739-1771, 1789-1803, 1814-1827, 1842-1851, 1863-1866, 1877-1880, 1885-1887, 1892-1893, 1903-1910, 1916-1921, 1929-1933, 1940-1944, 1951-1953, 1961-1972, 1978-1994, 2012-2097, 2107-2125, 2131-2182, 2188-2241, 2247-2274, 2280-2307, 2313-2337, 2344-2373, 2379-2433, 2439-2495, 2501-2529, 2535-2563, 2569-2589, 2597-2612, 2618-2673, 2679-2734, 2740-2795, 2802-2860, 2867-2927, 2935-2940, 2946-2966 |
| TWLight/users/views.py                                                                        |      522 |      378 |      118 |        0 |     22% |82-86, 90-104, 108-118, 129-136, 139-144, 161-201, 204-303, 323-335, 375-386, 392-405, 411-417, 430-432, 435-455, 461-472, 475-494, 509-511, 514-525, 528-541, 544-556, 559, 574, 579-627, 650-653, 660-672, 679-682, 687-713, 730-747, 760-764, 767-774, 790-794, 797-807, 828-836, 853-894, 919-968, 1000-1123, 1149-1246, 1258-1268, 1277-1295 |
| TWLight/view\_mixins.py                                                                       |      146 |       95 |       44 |        0 |     27% |39-42, 46-49, 60-66, 76-82, 86-111, 126-134, 138-148, 162-168, 172, 188-196, 200, 215-223, 236-247, 251-256, 267-290, 294, 305-328, 332, 341-346, 350, 361-364, 374-378 |
| TWLight/views.py                                                                              |      109 |       72 |       22 |        0 |     28% |40-142, 145-149, 162-176, 179-183, 194-207 |
| TWLight/wsgi.py                                                                               |        4 |        4 |        0 |        0 |      0% |     10-16 |
|                                                                                     **TOTAL** | **16029** | **12995** | **1376** |    **7** | **18%** |           |

144 files skipped due to complete coverage.
