import sys
import yaml

partner_pk = sys.argv[1]

with open('/var/www/html/TWLight/TWLight/resources/fixtures/partners/{id}.yaml'.format(id=partner_pk)) as fixture:
     yaml_py_obj = yaml.safe_load(fixture)

for key, value in yaml_py_obj[0].iteritems():
    if key == 'fields':
        for key1, value1 in value.iteritems():
            if key1.startswith('send_instructions') and yaml_py_obj[0][key][key1] is not None:
                yaml_py_obj[0][key][key1] = None
            elif key1 == 'coordinator' and yaml_py_obj[0][key][key1] is not None:
                yaml_py_obj[0][key][key1] = None

with open('/var/www/html/TWLight/TWLight/resources/fixtures/partners/{id}.yaml'.format(id=partner_pk), 'w') as fixture:
    yaml.dump(yaml_py_obj, fixture)