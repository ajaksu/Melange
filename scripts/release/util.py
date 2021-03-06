# Copyright 2009 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Various utilities.

Current contents:
 - Text colorization using ANSI color codes
 - A class to construct and manage paths under a root path.
 - A helper to manage running subprocesses, wrapping the subprocess module.
"""

__authors__ = [
    # alphabetical order by last name, please
    '"David Anderson" <dave@natulte.net>',
    ]


import os.path
import re
try:
  import cStringIO as StringIO
except ImportError:
  import StringIO
import subprocess
import threading

import error
import log


class Error(error.Error):
  pass


class SubprocessFailed(Error):
  """A subprocess returned a non-zero error code."""
  pass


# The magic escape sequence understood by modern terminal emulators to
# configure fore/background colors and other basic text display
# settings.
_ANSI_ESCAPE = '\x1b[%dm'
_ANSI_ESCAPE_RE = re.compile(r'\x1b\[\d+m')


# Some internal non-color settings that we use.
_RESET = 0  # Reset to terminal defaults.
_BOLD = 1   # Brighter colors.


# ANSI color codes.
RED = 31
GREEN = 32
WHITE = 37


def _ansi_escape(code):
  return _ANSI_ESCAPE % code


def colorize(text, color, bold=False):
  """Colorize some text using ANSI color codes.

  Note that while ANSI color codes look good in a terminal they look
  like noise in log files unless viewed in an ANSI color capable
  viewer (such as 'less -R').

  Args:
    text: The text to colorize.
    color: One of the color symbols from this module.
    bold: If True, make the color brighter.

  Returns:
    The input text string, appropriately sprinkled with color
    codes. Colors are reset to terminal defaults after the input
    text.
  """
  bold = _ansi_escape(_BOLD) if bold else ''
  return '%s%s%s%s' % (bold, _ansi_escape(color),
                       text, _ansi_escape(_RESET))


def decolorize(text):
  """Remove ANSI color codes from text."""
  return _ANSI_ESCAPE_RE.sub('', text)


class Paths(object):
  """A helper to construct and check paths under a given root."""

  def __init__(self, root):
    """Initializer.

    Args:
      root: The root of all paths this instance will consider.
    """
    self._root = os.path.abspath(
      os.path.expandvars(os.path.expanduser(root)))

  def path(self, path=''):
    """Construct and return a path under the path root.

    Args:
      path: The desired path string relative to the root.

    Returns:
      The absolute path corresponding to the relative input path.
    """
    assert not os.path.isabs(path)
    return os.path.abspath(os.path.join(self._root, path))

  def exists(self, path=''):
    """Check for the existence of a path under the path root.

    Does not discriminate on the path type (ie. it could be a
    directory, a file, a symbolic link...), just checks for the
    existence of the path.

    Args:
      path: The path string relative to the root.

    Returns:
      True if the path exists, False otherwise.
    """
    return os.path.exists(self.path(path))


class _PipeAdapter(threading.Thread):
  """A thread that connects one file-like object to another"""
  def __init__(self, pipe, logfile):
    threading.Thread.__init__(self)
    self.pipe, self.logfile = pipe, logfile
    self.setDaemon(True)
    self.start()

  def run(self):
    try:
      while True:
        data = self.pipe.read(512)  # Small to retain interactivity
        if not data:
          return
        self.logfile.write(data)
    except (EOFError, OSError):
      pass


def run(argv, cwd=None, capture=False, split_capture=True, stdin=None):
  """Run the given command and optionally return its output.

  Note that if you set capture=True, the command's output is
  buffered in memory. Output capture should only be used with
  commands that output small amounts of data. O(kB) is fine, O(MB)
  is starting to push it a little.

  Args:
    argv: A list containing the name of the program to run, followed
      by its argument vector.
    cwd: Run the program from this directory.
    capture: If True, capture the program's stdout stream. If False,
      stdout will output to sys.stdout.
    split_capture: If True, return the captured output as a list of
      lines. Else, return as a single unaltered string.
    stdin: The string to feed to the program's stdin stream.

  Returns:
    If capture is True, a string containing the combined
    stdout/stderr output of the program. If capture is False,
    nothing is returned.

  Raises:
    SubprocessFailed: The subprocess exited with a non-zero exit code.
  """
  log.debug(colorize('# ' + ' '.join(argv), WHITE, bold=True))

  process = subprocess.Popen(argv,
                             shell=False,
                             cwd=cwd,
                             stdin=(subprocess.PIPE if stdin else None),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

  # Spin up threads to capture stdout and stderr. Depending on the
  # value of the capture parameter, stdout is pushed either into the
  # log or into a string for processing. stderr always goes
  # into the log.
  #
  # Threads are necessary because all of writing to stdin, reading
  # from stdout and reading from stderr must all happen
  # simultaneously. Otherwise, there is a risk that one of the pipes
  # will fill up, causing the subprocess and us to deadlock. So,
  # threads are used to keep the pipes safely flowing.
  stdout = StringIO.StringIO() if capture else log.FileLikeLogger()
  out_adapter = _PipeAdapter(process.stdout, stdout)
  err_adapter = _PipeAdapter(process.stderr, log.FileLikeLogger())
  
  if stdin:
    process.stdin.write(stdin)

  out_adapter.join()
  err_adapter.join()
  process.wait()

  if process.returncode != 0:
    if capture:
      raise SubprocessFailed('Process %s failed with output: %s' %
                             (argv[0], stdout.getvalue()))
    else:
      raise SubprocessFailed('Process %s failed' % argv[0])

  if capture:
    out = stdout.getvalue()
    stdout.close()

    if split_capture:
      out = out.strip().split('\n')
    return out
