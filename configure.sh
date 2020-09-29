#!/bin/sh

PYTHON_PATH=$( which python3 || which python || which python2 || echo 0 )
SYSTEM=$( uname -s )

if [ "$PYTHON_PATH" = "0" ]; then
	echo "No python detected! Please ensure it is installed in \$PATH"
	exit 1
fi

if [ $SYSTEM = "FreeBSD" ]
then
	INSTALL_OS="install-bsd"
elif [ $SYSTEM = "Linux" ]
then
	INSTALL_OS="install-linux"
else
	echo "Unrecognized system. Aborting."
	exit 1
fi

cat Makefile.in | sed "s|##PYTHON_PATH##|${PYTHON_PATH}|" | sed "s|##INSTALL_OS##|${INSTALL_OS}|" > Makefile
cat pgmon.rc.in | sed "s|##PYTHON_PATH##|${PYTHON_PATH}|" > pgmon.rc

