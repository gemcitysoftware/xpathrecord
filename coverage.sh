#!/bin/sh
# Requires Ned Batchelder's coverage.py
# http://nedbatchelder.com/code/coverage/

outdir="./coverage"

test -d $outdir && rm -rf $outdir

coverage -e
coverage -x runtest.py
coverage -b -d $outdir
