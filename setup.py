import os
import setuptools


with open('README.md', 'r') as f:
    long_description = f.read()

setup_kwargs = {
    'name': 'wgtrack',
    'version': '0.1.2',
    'author': 'The Towalink Project',
    'author_email': 'pypi.wgtrack@towalink.net',
    'description': 'wgtrack tracks WireGuard links, exports the status, and updates endpoints as needed',
    'long_description': long_description,
    'long_description_content_type': 'text/markdown',
    'url': 'https://www.towalink.net',
    'packages': setuptools.find_packages('src'),
    'package_dir': {'': 'src'},
    'include_package_data': True,
    'install_requires': [ ],
    'entry_points': '''
        [console_scripts]
        wgtrack=wgtrack:main
    ''',
    'classifiers': [
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Telecommunications Industry',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Networking'
    ],
    'python_requires': '>=3.5',
    'keywords': 'WireGuard monitoring Towalink VPN dyndns NAT-traversal',
    'project_urls': {
        'Repository': 'https://www.github.com/towalink/wgtrack',
    },
}


if __name__ == '__main__':
    setuptools.setup(**setup_kwargs)
