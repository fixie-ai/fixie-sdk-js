# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['llamalabs', 'llamalabs.agents', 'llamalabs.client']

package_data = \
{'': ['*']}

install_requires = \
['PyYAML>=6.0,<7.0',
 'click>=8.1.3,<9.0.0',
 'fastapi[all]>=0.89.1,<0.90.0',
 'gql[all]>=3.4.0,<4.0.0',
 'pillow>=9.0.1,<10.0.0',
 'prompt-toolkit>=3.0.31,<4.0.0',
 'pydantic>=1.4.0,<2.0.0',
 'requests>=2.28.1,<3.0.0',
 'rich>=12.6.0,<13.0.0']

entry_points = \
{'console_scripts': ['llamalabs = llamalabs.client.console:cli']}

setup_kwargs = {
    'name': 'llamalabs',
    'version': '0.1.0',
    'description': 'SDK for the Llama Labs platform. See: https://llamalabs.ai',
    'long_description': 'None',
    'author': 'LlamaLabs.ai Team',
    'author_email': 'founders@fixie.ai',
    'maintainer': 'None',
    'maintainer_email': 'None',
    'url': 'None',
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'entry_points': entry_points,
    'python_requires': '>=3.9,<4.0',
}


setup(**setup_kwargs)

