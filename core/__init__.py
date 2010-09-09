"""Core Web Support for Minor.

This package contains...

standardControllers -- Basic .psp parsers and error handling
inputControllers -- Simple encapsulation for reading <form/> input
tableControllers -- Basic table controller and properity list
baseControllers -- Basic page frame with nav, header and footer
testControllers -- Collection of self tests and debugging controllers
environment -- For setting up temp paths and logger
utils -- Logger and collection of other handy to have functions
"""

__all__ = [
	'standardControllers',
	'inputControllers',
	'tableControllers',
	'baseControllers',
	'testControllers',
	'environment',
	'utils',
]

__version__ = '$Revision: 893 $'.split()[-2:][0]

