#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os
import sys
import time
import difflib
import pprint
from typing import Any

sys.path.append(os.path.dirname(__file__))

from felt_tests_thunderbird import FeltTestsThunderbird
from felt_consts import firefox_config

from marionette_driver.errors import UnknownException


def diff(a: Any, b: Any) -> list[str]:
    pp_a = pprint.pformat(a, sort_dicts=True).splitlines()
    pp_b = pprint.pformat(b, sort_dicts=True).splitlines()
    return list(
        difflib.unified_diff(pp_a, pp_b, fromfile="a", tofile="b", lineterm="")
    )


class ThunderbirdPoliciesDifferences(FeltTestsThunderbird):
    def get_policies(self, module):
        with self._child_driver.using_context(self._child_driver.CONTEXT_CHROME):
            return json.loads(self._child_driver.execute_script("""
                const { Policies } = ChromeUtils.importESModule(
                    `resource:///modules/${arguments[0]}/Policies.sys.mjs`
                );
                return JSON.stringify(Policies, (key, val) =>
                    typeof val === 'function' ? val.toString() : val
                );
            """, [module]))

    def test_thunderbird_policies_differences(self):
        self.run_felt_base()
        self.connect_child_browser()

        tbird_policies = self.get_policies("policies")
        browser_policies = self.get_policies("policies_browser")

        differences = {}
        for policy_name in tbird_policies:
            if policy_name == "_cleanup" or policy_name not in browser_policies:
                self._logger.info(f"Skipping {policy_name} policy")
                continue

            same = tbird_policies[policy_name] == browser_policies[policy_name]
            if not same:
                differences[policy_name] = diff(browser_policies[policy_name], tbird_policies[policy_name])

        if len(differences) > 0:
            for policy_name in differences:
                for line in differences[policy_name]:
                    self._logger.info(f"Differences for {policy_name}: {line.strip()}")

        assert len(differences) == 0, f"Policies {differences.keys()} differs from Firefox"
