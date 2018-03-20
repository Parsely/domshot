import errno
import datetime as dt
import os
import random
import simplejson

from jinja2 import Environment, PackageLoader

try:
    import numpy as np
except ImportError:
    np = None


def js_escape(value):
    return value.replace('"', '\\"').replace('\n', '\\n')


def get_tmp_file_path():
    # This could use some love (to avoid concurrent processes overriding this
    # tmpfile).  However, for some reason mkstemp() did not work (as phantomjs
    # does not seem to be able to write to the file that way).
    return '/tmp/tmp_domshot_%d.png' % random.randint(1000, 1000000)


def to_json(data):
    def dthandler(obj):
        if np and isinstance(obj, np.ndarray):
            return [dthandler(rec) for rec in obj.tolist()]
        if np and isinstance(obj, np.generic):
            return np.asscalar(obj)
        if isinstance(obj, dt.datetime):
            return obj.isoformat()
        if isinstance(obj, dt.date):
            return obj.strftime("%Y-%m-%d")
        if isinstance(obj, dt.time):
            return obj.strftime("%H:%M:%S")

        return obj

    return simplejson.dumps(data, default=dthandler)


class DOMShot(object):
    def __init__(self):
        self.css = ''
        self.js = ''
        self.body = ''
        self._script = None
        self.width = 800
        self.height = 600
        self.env = {}

    def set_clip(self, tup):
        self.width, self.height = tup

    def get_clip(self):
        return self.width, self.height

    clip = property(get_clip, set_clip)

    def load_files(self, *files):
        for file in files:
            self.load_file(file)

    @staticmethod
    def get_file_contents(filename, encoding='utf-8'):
        with open(filename, 'r') as f:
            return f.read().decode(encoding)

    @staticmethod
    def get_file_bytes(filename):
        with open(filename, 'rb') as f:
            return f.read()

    def load_file(self, filename):
        if filename.endswith('.css'):
            self.load_css(self.get_file_contents(filename))
        elif filename.endswith('.js'):
            self.load_js(self.get_file_contents(filename))
        elif filename.endswith('.html'):
            # Don't append, overwrite
            self.load_html(self.get_file_contents(filename))
        else:
            raise ValueError('Unknown file type.')

    def load_html(self, html_body):
        self.body = html_body

    def load_css(self, css_contents):
        self.css += '\n' + css_contents

    def load_js(self, js_contents):
        self.js += '\n' + js_contents

    def generate_script(self):
        env = Environment(loader=PackageLoader('domshot', 'templates'))
        env.filters['js_escape'] = js_escape

        # First, write out all global vars
        foreword = []
        for key, val in list(self.env.items()):
            foreword.append('var %s = %s;\n' % (key, to_json(val)))

        template = env.get_template('render.jinja.js')

        self._tmpfile = get_tmp_file_path()
        self._script = template.render(
                css=self.css,
                body=self.body,
                foreword=''.join(foreword),
                inline_js=self.js,
                tmpfile=self._tmpfile,
                clip=self.clip)

    @property
    def script(self):
        if self._script is None:
            self.generate_script()
        return self._script

    def _filter_stdout(self, stdout):
        """This is quite a hack to ignore warnings that we know of, but fail
        on all other occassions (which probably are real PhantomJS warnings or
        errors.
        """
        def is_important_line(line):
            warnings_to_ignore = [
                'Unable to load library icui18n',
            ]
            for warning in warnings_to_ignore:
                if warning in line:
                    return False
            return True

        return [line for line in stdout.strip().split('\n')
                if line and is_important_line(line)]

    def _run(self, stdin):
        from subprocess import Popen, PIPE, STDOUT
        p = Popen(['phantomjs', '/dev/stdin'], stdin=PIPE, stdout=PIPE,
                stderr=STDOUT)
        stdout, _ = p.communicate(stdin)
        stdout = self._filter_stdout(stdout)
        if stdout:
            raise RuntimeError('Unexpected error while running phantomjs:\n%s'
                    % '\n'.join(stdout))

    def render(self, filename=None):
        try:
            self._run(self.script.encode('utf-8'))
            png_content = self.get_file_bytes(self._tmpfile)
        finally:
            try:
                if hasattr(self, "_tmpfile"):
                    os.unlink(self._tmpfile)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    # It's OK if the file does not exist
                    pass
        if filename:
            with open(filename, 'wb') as f:
                f.write(png_content)
        else:
            return png_content


if __name__ == '__main__':
    ds = DOMShot()
    ds.load_files('example/style.css', 'example/jquery.min.js',
            'example/d3.v2.min.js')
    ds.load_js("""
        $('body').append('ohai, world');
    """)
    ds.render('output.png')
