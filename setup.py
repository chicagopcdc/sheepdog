from setuptools import setup

setup(
    name='sheepdog',
    version='0.2.0',
    description='Flask blueprint for herding data submissions',
    url='https://github.com/uc-cdis/sheepdog',
    license='Apache',
    packages=[
        'sheepdog',
        'sheepdog.auth',
        'sheepdog.blueprint',
        'sheepdog.blueprint.routes',
        'sheepdog.blueprint.routes.views',
        'sheepdog.blueprint.routes.views.program',
        'sheepdog.transactions',
        'sheepdog.transactions.close',
        'sheepdog.transactions.deletion',
        'sheepdog.transactions.release',
        'sheepdog.transactions.review',
        'sheepdog.transactions.submission',
        'sheepdog.transactions.upload',
        'sheepdog.utils',
        'sheepdog.utils.transforms',
    ],
    install_requires=[
        'boto==2.46.1',
        'psycopg2==2.7.3.2',
        'cryptography==2.1.2',
        'Flask-Cors==1.9.0',
        'Flask-SQLAlchemy-Session==1.1',
        'Flask==0.10.1',
        'fuzzywuzzy==0.6.1',
        'graphene==0.10.2',
        'jsonschema==2.5.1',
        'lxml==3.8.0',
        'PyYAML==3.11',
        'requests==2.7',
        'setuptools==36.3.0',
        'simplejson==3.8.1',
        'sqlalchemy==0.9.9',
        'cdis_oauth2client',
        'cdispyutils',
        'datamodelutils',
        'dictionaryutils',
        # 'gdcdatamodel',
        # 'gdcdictionary',
        'indexclient',
        'psqlgraph',
        'signpost',
        'userdatamodel',
    ],
    dependency_links=[
        'git+https://git@github.com/uc-cdis/userdatamodel.git@cb7143c709a1173c84de4577d3e866318a2cc834#egg=userdatamodel', # OK
        'git+https://git@github.com/uc-cdis/cdis_oauth2client.git@0.1.2#egg=cdis_oauth2client', # OK
        'git+https://git@github.com/NCI-GDC/psqlgraph.git@1.2.0#egg=psqlgraph', # OK
        'git+https://git@github.com/uc-cdis/cdis-python-utils.git@0.2.2#egg=cdispyutils', # OK?
        'git+https://git@github.com/uc-cdis/dictionaryutils.git@1.1.0#egg=dictionaryutils', # OK
        'git+https://git@github.com/NCI-GDC/signpost.git@c8e2aa5ff572c808cba9b522b64f7b497e79c524#egg=signpost', # OK
        'git+https://git@github.com/uc-cdis/datamodelutils.git@0.2.0#egg=datamodelutils', # OK
        'git+https://git@github.com/uc-cdis/indexclient.git@d49134f4626b69a8ef02c189ed0047ad1a635cb0#egg=indexclient', # OK
    ],
)
