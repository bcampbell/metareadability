import unittest
import site
import subprocess
import os


here = os.path.dirname(os.path.abspath(__file__))

class TestFailsafes(unittest.TestCase):

    def setUp(self):
        pass

    def runTest(self):
        """ check that the failsafe set of articles give the expected results """
        cmd = "%s failsafes/*.csv" % (os.path.join(here,'checkarticles'),)
        process = subprocess.Popen(cmd, cwd=here,shell=True)#, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        self.assertEqual(process.returncode, 0)


foo = TestFailsafes()
foo.runTest()

