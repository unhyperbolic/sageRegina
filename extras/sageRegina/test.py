#__all__ = ['runTests']

from .. import __dict__ as reginaDict

import sys
import os
import glob
import difflib
from StringIO import StringIO

base_path = os.path.split(__file__)[0]
testsuite_path = os.path.join(base_path, 'testsuite')

def runSource(source):

    original_stdout = sys.stdout
    original_displayhook = sys.displayhook
    original_argv = sys.argv

    fakeout = StringIO()
    
    sys.stdout = fakeout
    sys.displayhook = sys.__displayhook__
    sys.argv = ['regina', testsuite_path]

    try:
        globs = reginaDict.copy()

        class ReginaWrapper:
            pass
        reginaWrapper = ReginaWrapper()
        reginaWrapper.__dict__ = reginaDict.copy()
        globs['regina'] = reginaWrapper

        exception = None
        try:
            exec(source) in globs
        except:
            exception = sys.exc_info()

    finally:
        sys.stdout = original_stdout
        sys.displayhook = original_displayhook
        sys.argv = original_argv

    return fakeout.getvalue(), exception

def runFile(path):
    return runSource(open(path).read())

def findTests():
    search_path = os.path.join(testsuite_path, '*.test')
    return [
        (os.path.splitext(os.path.basename(path))[0], path)
        for path in glob.glob(search_path)]

def runTest(testName, testFile):
    failed = ""
    
    output, exception = runFile(testFile)

    baseline = open(testFile.replace('.test', '.out')).read()

    if testName == 'misc':
        # Last line is about open function which displays
        # differently on different sytems, e.g., something like
        # <boost.python.function at 0x34534345345>
        output   = '\n'.join(  output.split('\n')[:-2])
        baseline = '\n'.join(baseline.split('\n')[:-2])
                           
    if output != baseline:
        failed += "Difference between baseline and putput:\n"
        failed += '\n'.join(
            difflib.context_diff(
                baseline.split('\n'),
                output.split('\n'),
                fromfile = os.path.basename(testFile),
                tofile = 'OUTPUT'))

    if exception:
        failed += "Raised exception: %s" % exception

    return failed

def runTests():
    failedTests = []
    
    for testName, testFile in findTests():
        print "Running test %s:" % (testName + (20 - len(testName)) * " "),
        sys.stdout.flush()

        failureOutput = runTest(testName, testFile)

        if failureOutput:
            failedTests.append(testName)
            print "FAILED!!!"
            print failureOutput
        else:
            print "ok"
    
    if failedTests:
        print "The following %d test(s) failed: %s" % (
            len(failedTests), ', '.join(failedTests))
    else:
        print "All tests passed"

