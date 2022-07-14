# Code obtained from:
# https://hakibenita.com/timing-tests-in-python-for-fun-and-profit

import time
import unittest
from unittest import TextTestRunner
from unittest.runner import TextTestResult

from django.test.runner import DiscoverRunner

SLOW_TEST_THRESHOLD = 0.2


class TimeLoggingTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_timings = []

    def startTest(self, test):
        self._test_started_at = time.time()
        super().startTest(test)

    def addSuccess(self, test):
        elapsed = time.time() - self._test_started_at
        name = self.getDescription(test)
        self.test_timings.append((name, elapsed))
        super().addSuccess(test)

    def getTestTimings(self):
        return self.test_timings


class TimeLoggingTextTestRunner(TextTestRunner):
    def __init__(self, slow_test_threshold=SLOW_TEST_THRESHOLD, *args, **kwargs):
        self.slow_test_threshold = slow_test_threshold
        self.resultclass = TimeLoggingTestResult
        return super().__init__(*args, **kwargs)

    def run(self, test):
        result = super().run(test)

        self.stream.writeln("\nSlow Tests (>{:.03}s):".format(self.slow_test_threshold))
        for name, elapsed in result.getTestTimings():
            if elapsed > self.slow_test_threshold:
                self.stream.writeln("({:.03}s) {}".format(elapsed, name))

        return result


class TimeLoggingTestRunner(DiscoverRunner):
    test_runner = TimeLoggingTextTestRunner
