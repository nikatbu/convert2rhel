# -*- coding: utf-8 -*-
#
# Copyright(C) 2018 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__metaclass__ = type

import os
import unittest

from collections import namedtuple

from convert2rhel import actions, grub, unit_tests
from convert2rhel.actions.system_checks import efi
from convert2rhel.unit_tests import EFIBootInfoMocked, GetLoggerMocked


def _gen_version(major, minor):
    return namedtuple("Version", ["major", "minor"])(major, minor)


class TestEFIChecks(unittest.TestCase):
    def setUp(self):
        self.efi_action = efi.Efi()

    def _check_efi_detection_log(self, efi_detected=True):
        if efi_detected:
            self.assertNotIn("BIOS detected.", efi.logger.info_msgs)
            self.assertIn("UEFI detected.", efi.logger.info_msgs)
        else:
            self.assertIn("BIOS detected.", efi.logger.info_msgs)
            self.assertNotIn("UEFI detected.", efi.logger.info_msgs)

    def _check_efi_critical(self, error_id, critical_msg):
        self.efi_action.run()
        self.assertEqual(self.efi_action.status, actions.STATUS_CODE["ERROR"])
        self.assertEqual(self.efi_action.error_id, error_id)
        self.assertEqual(self.efi_action.message, critical_msg)
        self._check_efi_detection_log(True)

    @unit_tests.mock(grub, "is_efi", lambda: True)
    @unit_tests.mock(grub, "is_secure_boot", lambda: False)
    @unit_tests.mock(efi.system_info, "arch", "x86_64")
    @unit_tests.mock(efi.system_info, "version", _gen_version(7, 9))
    @unit_tests.mock(efi, "logger", GetLoggerMocked())
    @unit_tests.mock(os.path, "exists", lambda x: not x == "/usr/sbin/efibootmgr")
    @unit_tests.mock(
        grub,
        "EFIBootInfo",
        EFIBootInfoMocked(exception=grub.BootloaderError("errmsg")),
    )
    def test_check_efi_efi_detected_without_efibootmgr(self):
        self._check_efi_critical(
            "EFIBOOTMGR_NOT_FOUND", "Install efibootmgr to continue converting the UEFI-based system."
        )

    @unit_tests.mock(grub, "is_efi", lambda: True)
    @unit_tests.mock(grub, "is_secure_boot", lambda: False)
    @unit_tests.mock(efi.system_info, "arch", "aarch64")
    @unit_tests.mock(efi.system_info, "version", _gen_version(7, 9))
    @unit_tests.mock(efi, "logger", GetLoggerMocked())
    @unit_tests.mock(os.path, "exists", lambda x: x == "/usr/sbin/efibootmgr")
    @unit_tests.mock(
        grub,
        "EFIBootInfo",
        EFIBootInfoMocked(exception=grub.BootloaderError("errmsg")),
    )
    def test_check_efi_efi_detected_non_intel(self):
        self._check_efi_critical("NON_x86_64", "Only x86_64 systems are supported for UEFI conversions.")

    @unit_tests.mock(grub, "is_efi", lambda: True)
    @unit_tests.mock(grub, "is_secure_boot", lambda: True)
    @unit_tests.mock(efi.system_info, "arch", "x86_64")
    @unit_tests.mock(efi.system_info, "version", _gen_version(7, 9))
    @unit_tests.mock(efi, "logger", GetLoggerMocked())
    @unit_tests.mock(os.path, "exists", lambda x: x == "/usr/sbin/efibootmgr")
    @unit_tests.mock(
        grub,
        "EFIBootInfo",
        EFIBootInfoMocked(exception=grub.BootloaderError("errmsg")),
    )
    def test_check_efi_efi_detected_secure_boot(self):
        self._check_efi_critical(
            "SECURE_BOOT_DETECTED",
            "The conversion with secure boot is currently not possible.\n"
            "To disable it, follow the instructions available in this article: https://access.redhat.com/solutions/6753681",
        )
        self.assertIn("Secure boot detected.", efi.logger.info_msgs)

    @unit_tests.mock(grub, "is_efi", lambda: True)
    @unit_tests.mock(grub, "is_secure_boot", lambda: False)
    @unit_tests.mock(efi.system_info, "arch", "x86_64")
    @unit_tests.mock(efi.system_info, "version", _gen_version(7, 9))
    @unit_tests.mock(efi, "logger", GetLoggerMocked())
    @unit_tests.mock(os.path, "exists", lambda x: x == "/usr/sbin/efibootmgr")
    @unit_tests.mock(
        grub,
        "EFIBootInfo",
        EFIBootInfoMocked(exception=grub.BootloaderError("errmsg")),
    )
    def test_check_efi_efi_detected_bootloader_error(self):
        self._check_efi_critical("BOOTLOADER_ERROR", "errmsg")

    @unit_tests.mock(grub, "is_efi", lambda: True)
    @unit_tests.mock(grub, "is_secure_boot", lambda: False)
    @unit_tests.mock(efi.system_info, "arch", "x86_64")
    @unit_tests.mock(efi.system_info, "version", _gen_version(7, 9))
    @unit_tests.mock(efi, "logger", GetLoggerMocked())
    @unit_tests.mock(os.path, "exists", lambda x: x == "/usr/sbin/efibootmgr")
    @unit_tests.mock(grub, "EFIBootInfo", EFIBootInfoMocked(current_bootnum="0002"))
    def test_check_efi_efi_detected_nofile_entry(self):
        self.efi_action.run()
        self._check_efi_detection_log()
        warn_msg = (
            "The current UEFI bootloader '0002' is not referring to any binary UEFI file located on local"
            " EFI System Partition (ESP)."
        )
        self.assertIn(warn_msg, efi.logger.warning_msgs)

    @unit_tests.mock(grub, "is_efi", lambda: True)
    @unit_tests.mock(grub, "is_secure_boot", lambda: False)
    @unit_tests.mock(efi.system_info, "arch", "x86_64")
    @unit_tests.mock(efi.system_info, "version", _gen_version(7, 9))
    @unit_tests.mock(efi, "logger", GetLoggerMocked())
    @unit_tests.mock(os.path, "exists", lambda x: x == "/usr/sbin/efibootmgr")
    @unit_tests.mock(grub, "EFIBootInfo", EFIBootInfoMocked())
    def test_check_efi_efi_detected_ok(self):
        self.efi_action.run()
        self._check_efi_detection_log()
        self.assertEqual(len(efi.logger.warning_msgs), 0)
