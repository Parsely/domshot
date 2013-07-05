var page = require('webpage').create()

// Set up logging, so we can see JS errors in the browser
page.onError = function (msg, trace) {
    console.log(msg);
    trace.forEach(function(item) {
        console.log('  ', item.file, ':', item.line);
    })
}

// Allow console.log statements in the browser to trickle down to the console
page.onConsoleMessage = function (msg) {
    console.log(msg);
}

// Set viewport before loading content
page.viewportSize = { width: {{ clip[0] }}, height: {{ clip[1] }} }

page.content = "\
        <html>\
            <head>\
            <style type=text/css>\
            {{ css|js_escape|safe }}\
            </style>\
            </head>\
            {{ body|js_escape|safe or "<body></body>" }}\
        </html>\
        "

page.clipRect = { top: 0, left: 0, width: {{ clip[0] }}, height: {{ clip[1] }} }

page.evaluate(function () {
    {{ foreword|safe }}
    {{ inline_js|safe }}
})
page.render("{{ tmpfile|js_escape|safe }}")
phantom.exit(0)
