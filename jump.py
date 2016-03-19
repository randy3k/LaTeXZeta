import sublime
import sublime_plugin
import os
import subprocess
import time
from . misc import get_tex_root
import sys

if sys.platform == "win32":
    from winreg import OpenKey, QueryValueEx, HKEY_LOCAL_MACHINE, KEY_READ


def SumatraPDF():
    try:
        akey = OpenKey(HKEY_LOCAL_MACHINE,
                       "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\SumatraPDF.exe",
                       0, KEY_READ)
        path = QueryValueEx(akey, "")[0]
    except:
        print("Cannot find SumatraPDF from registry. Check if SumatraPDF has been installed!")
        return "SumatraPDF.exe"
    return path


class LatexPlusJumpToPdfCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        view = self.view
        point = view.sel()[0].end() if len(view.sel()) > 0 else 0
        if not view.score_selector(point, "text.tex.latex"):
            return

        self.settings = sublime.load_settings('LaTeX-Plus.sublime-settings')

        bring_forward = args["bring_forward"] if "bring_forward" in args else False
        forward_sync = args["forward_sync"] if "forward_sync" in args else False

        srcfile = self.view.file_name()
        tex_root = get_tex_root(self.view)

        pdffile = os.path.splitext(tex_root)[0] + '.pdf'

        (line, col) = self.view.rowcol(self.view.sel()[0].end())
        line += 1

        plat = sublime.platform()
        if plat == 'osx':
            # osx_settings = self.settings.get("osx")

            args = ['osascript']
            apple_script = ('tell application "Skim"\n'
                                'if ' + str(bring_forward)+' then activate\n'
                                'open POSIX file "' + pdffile + '"\n'
                                'revert front document\n'
                                'if ' + str(forward_sync)+' then\n'
                                    'tell front document to go to TeX line ' + str(line) +
                                    ' from POSIX file "' + srcfile + '"\n'
                                'end if\n'
                            'end tell\n')
            args.extend(['-e', apple_script])
            subprocess.Popen(args)

        elif plat == 'windows':
            # hide console
            windows_settings = self.settings.get("windows")

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            tasks = subprocess.check_output(["tasklist"], startupinfo=startupinfo)
            sumatra_is_running = "SumatraPDF.exe" in tasks.decode('utf-8', 'ignore')
            try:
                sumatrapdf = windows_settings["sumatrapdf"] \
                    if "sumatrapdf" in windows_settings else SumatraPDF()
                if not sumatra_is_running:
                    print("SumatraPDF not running, launch it")
                    subprocess.Popen([sumatrapdf, pdffile])
                    if not sumatra_is_running:
                        time.sleep(1)
                elif bring_forward:
                    subprocess.Popen([sumatrapdf, "-reuse-instance", pdffile])
            except:
                print("Cannot launch SumatraPDF!")
                return

            if forward_sync:
                subprocess.Popen([sumatrapdf, "-reuse-instance", "-forward-search",
                                  srcfile, str(line), pdffile])

        elif plat == 'linux':

            linux_settings = self.settings.get("linux")
            viewer = linux_settings.get("viewer", "evince")

            if viewer == "okular":
                if forward_sync:
                    args = ["okular", "-unique", "%s#src:%s %s" % (pdffile, line, srcfile)]
                else:
                    args = ["okular", "-unique", pdffile]
                print("about to run okular with %s" % ' '.join(args))
                subprocess.Popen(args)
            elif viewer == "zathura":
                if forward_sync:
                    dest = str(line) + ":" + str(col) + ":" + srcfile
                    args = ["zathura", "--synctex-forward", dest, pdffile]
                else:
                    sb_binary = linux_settings.get("sublime", "subl")
                    args = ["zathura", "-s", "-x",
                            sb_binary + " %{input}:%{line}", pdffile]
                print("about to run zathura with %s" % ' '.join(args))
                subprocess.Popen(args)
            else:
                evince_sync = sublime.load_resource("Packages/LaTeX-Plus/evince_sync")
                tasks = subprocess.check_output(['ps', 'xw'])

                subl = linux_settings["sublime"] if "sublime" in linux_settings else "subl"
                evince_is_running = "evince " + pdffile in str(tasks, encoding='utf8')
                if bring_forward or not evince_is_running:
                    subprocess.Popen(["python", "-c", evince_sync, "open", pdffile,
                                      subl + ' "%f:%l"'])
                    if not evince_is_running:
                        time.sleep(1)

                if forward_sync:
                    subprocess.Popen(["python", "-c", evince_sync, "forward", pdffile,
                                      str(line), srcfile])

    def is_enabled(self):
        view = self.view
        point = view.sel()[0].end() if len(view.sel()) > 0 else 0
        return view.score_selector(point, "text.tex.latex") > 0

    def is_visible(self):
        view = self.view
        point = view.sel()[0].end() if len(view.sel()) > 0 else 0
        return view.score_selector(point, "text.tex.latex") > 0
