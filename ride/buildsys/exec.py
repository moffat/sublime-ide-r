import sublime
import sublime_plugin

import os

from ..settings import ride_settings
from ..r import R
from ..utils import find_working_dir, selector_is_active


class RideExecCommand(sublime_plugin.WindowCommand):
    def run(self, selector="", kill=False, **kwargs):
        if kill:
            if ride_settings.get("terminus_exec", False):
                self.window.run_command("terminus_cancel_build")
            else:
                self.window.run_command("exec", {"kill": True})
            return

        if "cmd" in kwargs and kwargs["cmd"]:
            self.window.run_command("ride_exec_core", kwargs)
        elif "cmd" not in kwargs:
            # as a workaround of
            # https://github.com/SublimeTextIssues/Core/issues/3010
            # we pass an empty `text`
            sublime.set_timeout(lambda: self.window.run_command(
                    "show_overlay", {
                        "overlay": "command_palette",
                        "command": "ride_exec_core",
                        "text": ""
                    }), 10)

    def is_enabled(self, selector="", **kwargs):
        return selector_is_active(selector, window=self.window)


class RideExecCoreCommand(sublime_plugin.WindowCommand):
    def run(self, cmd="", env={}, working_dir="", subdir="", **kwargs):
        try:
            cmd = "{package}::{function}({args})".format(**kwargs)
        except KeyError:
            pass

        _kwargs = {}
        _kwargs["cmd"] = [ride_settings.r_binary(), "--quiet", "-e", cmd]
        if not working_dir:
            working_dir = find_working_dir(window=self.window)
        if working_dir and subdir:
            working_dir = os.path.join(working_dir, subdir)
        _kwargs["working_dir"] = working_dir
        _kwargs = sublime.expand_variables(_kwargs, self.window.extract_variables())
        _env = ride_settings.ride_env()
        _env.update(env)
        _kwargs["env"] = _env
        if "file_regex" in kwargs:
            _kwargs["file_regex"] = kwargs["file_regex"]
        if ride_settings.get("terminus_exec", False):
            self.window.run_command("terminus_exec", _kwargs)
        else:
            self.window.run_command("exec", _kwargs)

    def input(self, *args):
        return RideAskPackage()


LISTPACKAGES = "cat(.packages(all.available = TRUE), sep='\\n')"
LISTFUNCTIONS = "cat(paste(getNamespaceExports(asNamespace('{}')), collapse = '\\n'))"


class RideAskPackage(sublime_plugin.ListInputHandler):
    packages = []
    _initial_text = None

    def name(self):
        return "package"

    def initial_text(self):
        if RideAskPackage._initial_text:
            return RideAskPackage._initial_text

    def list_items(self):
        if not self.packages:
            self.packages[:] = R(LISTPACKAGES).strip().split("\n")
        return self.packages

    def confirm(self, text):
        RideAskPackage._initial_text = text

    def cancel(self):
        RideAskPackage._initial_text = None

    def placeholder(self):
        return "package::"

    def description(self, value, text):
        return "{}::".format(value)

    def next_input(self, args):
        return RideAskFunction(args)


class RideAskFunction(sublime_plugin.ListInputHandler):
    exports = {}
    _initial_text = {}
    package = None

    def __init__(self, args):
        package = args["package"]
        self.package = package
        if package not in self.exports:
            self.exports[package] = R(LISTFUNCTIONS.format(package)).strip().split("\n")

    def name(self):
        return "function"

    def initial_text(self):
        if self.package in RideAskFunction._initial_text:
            return RideAskFunction._initial_text[self.package]

    def placeholder(self):
        return "object"

    def confirm(self, text):
        RideAskFunction._initial_text[self.package] = text

    def cancel(self):
        if self.package in RideAskFunction._initial_text:
            del RideAskFunction._initial_text[self.package]

    def list_items(self):
        package = self.package
        if package in self.exports:
            return self.exports[package]

    def next_input(self, args):
        return RideAskArgs(args)


class RideAskArgs(sublime_plugin.TextInputHandler):
    package = None
    function = None
    _initial_text = {}

    def __init__(self, args):
        package = args["package"]
        function = args["function"]
        self.pkgfunc = "{}::{}".format(package, function)

    def name(self):
        return "args"

    def initial_text(self):
        if self.pkgfunc in RideAskArgs._initial_text:
            return RideAskArgs._initial_text[self.pkgfunc]

    def placeholder(self):
        return "args..."

    def preview(self, text):
        return "{}({})".format(self.pkgfunc, text)

    def confirm(self, text):
        RideAskArgs._initial_text[self.pkgfunc] = text

    def cancel(self):
        if self.pkgfunc in RideAskArgs._initial_text:
            del RideAskArgs._initial_text[self.pkgfunc]
