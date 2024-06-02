from setuptools import setup, find_packages
from pathlib import Path

setup(
	name='netmask',
	version='0.1.0',
	author='Joseph',
	author_email='josephdove@proton.me',
	description='A TCP/UDP self-hostable reverse proxy server that supports IPv4 and IPv6',
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type='text/markdown',
	classifiers=[
		'Programming Language :: Python :: 3.6',
		'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
	],
    packages=find_packages(
        include=[
            "netmask",
            "netmask.*"
        ]
    ),
	entry_points={
		"console_scripts": [
			"netmaskc = netmask.netmaskc:main",
			"netmasks = netmask.netmasks:main",
		]
	},
	python_requires='>=3.6',
)