# Code obtained from:
# https://hakibenita.com/timing-tests-in-python-for-fun-and-profit

import time
from unittest import TextTestRunner
from unittest.runner import TextTestResult

from django.test.runner import DiscoverRunner

SLOW_TEST_THRESHOLD = 1.5


class TimeLoggingTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_timings = []

    def startTest(self, test):
        self._test_started_at = time.time()
        super().startTest(test)

    def stopTest(self, test):
        self._test_ended_at = time.time()
        elapsed = round(self._test_ended_at - self._test_started_at, 5)
        name = self.getDescription(test)
        self.test_timings.append((name, elapsed))
        super().stopTest(test)

    def getTestTimings(self):
        return self.test_timings


class TimeLoggingTextTestRunner(TextTestRunner):
    def __init__(self, slow_test_threshold=SLOW_TEST_THRESHOLD, *args, **kwargs):
        self.slow_test_threshold = slow_test_threshold
        self.resultclass = TimeLoggingTestResult
        return super().__init__(*args, **kwargs)

    def run(self, test):
        result = super().run(test)

        timings = result.getTestTimings()
        timings_sorted = sorted(timings, key=lambda y: y[1], reverse=True)

        self.stream.writeln("\nSlow tests (>{:.05}s):".format(self.slow_test_threshold))
        slow_test_count = 0
        for name, elapsed in timings_sorted:
            if elapsed > self.slow_test_threshold:
                slow_test_count += 1
                self.stream.writeln("({:.05}s) {}".format(elapsed, name))
        self.stream.writeln(
            "\nFound {} slow tests (>{:.05}s) out of {}.\n".format(
                slow_test_count, self.slow_test_threshold, len(timings_sorted)
            )
        )

        return result


class TimeLoggingTestRunner(DiscoverRunner):
    test_runner = TimeLoggingTextTestRunner
