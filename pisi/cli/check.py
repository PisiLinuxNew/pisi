# -*- coding:utf-8 -*-
#
# Copyright (C) 2005-2011, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

import optparse
import os

import gettext
__trans = gettext.translation('pisi', fallback=True)
_ = __trans.gettext

import pisi.api
import pisi.cli.command as command
import pisi.context as ctx
import pisi.util as util
import pisi.db


usage = _("""Verify installation

Usage: check [<package1> <package2> ... <packagen>]
       check -c <component>
       check -w <path>

<packagei>: package name

A cryptographic checksum is stored for each installed
file. Check command uses the checksums to verify a package.
Just give the names of packages.

If no packages are given, checks all installed packages.
""")




class Check(command.Command, metaclass=command.autocommand):

    __doc__ = usage

    def __init__(self, args):
        super(Check, self).__init__(args)
        self.installdb = pisi.db.installdb.InstallDB()
        self.componentdb = pisi.db.componentdb.ComponentDB()

    name = ("check", None)

    def options(self):
        group = optparse.OptionGroup(self.parser, _("check options"))

        group.add_option("-c", "--component",
                         action="store",
                         default=None,
                         help=_("Check installed packages under "
                                "given component"))

        group.add_option("--config",
                         action="store_true",
                         default=False,
                         help=_("Checks only changed config files of "
                                "the packages"))

        group.add_option("-w", "--write",
                         action="store",
                         default=None,
                         help=_("Broken and Unknown packages write to given file"))
                         # write Broken and Unknown packages to given file

        self.parser.add_option_group(group)

    def run(self):
        self.init(database=True, write=False)

        component = ctx.get_option('component')
        if component:
            installed = pisi.api.list_installed()
            component_pkgs = self.componentdb.get_union_packages(component,
                                                                 walk=True)
            pkgs = list(set(installed) & set(component_pkgs))
        elif self.args:
            pkgs = self.args
        else:
            ctx.ui.info(_('Checking all installed packages') + '\n')
            pkgs = pisi.api.list_installed()

        necessary_permissions = True

        # True if we should also check the configuration files
        check_config = ctx.get_option('config')

        # Line prefix
        prefix = _('Checking integrity of %s')

        write_path = ctx.get_option("write")

        # TODO: bu fonksiyonu iyileştir
        def write_failed_check(path, text):
            if path is None: return
            if not os.path.exists(path):
                try:
                    with open(path,"w") as f:
                        pass
                except:
                    raise _(f"file dont writable: {path}")
                    
            with open(path, "a") as file:
                file.write(text + "\n")
            return True

        # Determine maximum length of messages for proper formatting
        maxpkglen = max([len(_p) for _p in pkgs])

        for pkg in pkgs:
            if self.installdb.has_package(pkg):
                check_results = pisi.api.check(pkg, check_config)
                message = "%s    %s" % ((prefix % pkg),
                                          ' ' * (maxpkglen - len(pkg)))
                ctx.ui.info(message,
                            noln=True)

                if check_results['missing'] or check_results['corrupted'] \
                        or check_results['config']:
                    ctx.ui.info(util.colorize(_("Broken"), 'brightred'))
                    write_failed_check(write_path, message + _("Broken"))
                elif check_results['denied']:
                    # We can't deduce a result when some files
                    # can't be accessed
                    necessary_permissions = False
                    ctx.ui.info(util.colorize(_("Unknown"), 'yellow'))
                    write_failed_check(write_path, message + _("Unknown"))
                else:
                    ctx.ui.info(util.colorize(_("OK"), 'green'))
                    continue

                # Dump per file stuff
                for fpath in check_results['missing']:
                    ctx.ui.info(util.colorize(
                        _("Missing file: /%s") % fpath, 'brightred'))
                    write_failed_check(write_path, _("Missing file: /%s") % fpath)

                for fpath in check_results['denied']:
                    ctx.ui.info(util.colorize(
                        _("Access denied: /%s") % fpath, 'yellow'))
                    write_failed_check(write_path, _("Access denied: /%s") % fpath)

                for fpath in check_results['corrupted']:
                    ctx.ui.info(util.colorize(
                        _("Corrupted file: /%s") % fpath, 'brightyellow'))
                    write_failed_check(write_path, _("Corrupted file: /%s") % fpath)

                for fpath in check_results['config']:
                    ctx.ui.info(util.colorize(
                        _("Modified configuration file: /%s") % fpath,
                        'brightyellow'))

            else:
                # Package is not installed
                ctx.ui.info(_('Package %s not installed') % pkg)

        if not necessary_permissions:
            ctx.ui.info("")
            ctx.ui.warning(_("Pisi was unable to check the integrity of "
                             "packages which contain files that you don't "
                             "have read access.\n"
                             "Running the check under a privileged user "
                             "may help fixing this problem."))
