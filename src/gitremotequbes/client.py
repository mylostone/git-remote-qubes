import argparse
import pipes
import subprocess
import sys
import urlparse

import gitremotequbes.copier


def get_main_parser():
    p = argparse.ArgumentParser()
    p.add_argument("name", metavar="NAME")
    p.add_argument("url", metavar="URL")
    return p


def main():
    p = get_main_parser()
    args = p.parse_args()
    url = urlparse.urlparse(args.url)
    assert url.scheme == "qubes"

    vm = subprocess.Popen(
        ["/usr/lib/qubes/qrexec-client-vm",
         url.netloc,
         "ruddo.Git"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    cmd = sys.stdin.readline()
    assert cmd == "capabilities\n"
    sys.stdout.write("connect\n\n")

    quotedargs = " ".join(pipes.quote(x) for x in [args.name, url.path])
    quotedlen = len(quotedargs)
    vm.stdin.write("%s\n" % quotedlen + quotedargs)

    while True:
        for f in sys.stdin, vm.stdin, sys.stdout, vm.stdout:
            gitremotequbes.copier.b(f)
        cmd = sys.stdin.readline()

        if not cmd:
            print >> sys.stderr, "local: no more commands, exiting"
            return 0
        elif cmd.startswith("connect "):
            print >> sys.stderr, "local: asked to run %r" % (cmd,)
            vm.stdin.write(cmd)
            reply = vm.stdout.readline()
            assert reply == "\n", "local: wrong reply %r" % reply
            sys.stdout.write(reply)

            gitremotequbes.copier.copy({
                sys.stdin: vm.stdin,
                vm.stdout: sys.stdout,
            }, eager=False, closefds=False)

            ret = vm.wait()
            if ret != 0:
                print >> sys.stderr, \
                    "local: remote side running %r exited with %s" % (cmd, ret)
                return ret
            else:
                print >> sys.stderr, \
                    "local: remote side running %r exited normally" % (cmd,)
        else:
            assert 0, "local: invalid command %r" % cmd
            return 127
