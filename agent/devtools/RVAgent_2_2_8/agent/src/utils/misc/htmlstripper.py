from HTMLParser import HTMLParser


class BodyHTMLStripper(HTMLParser):
    """
    Helper class to get data *only* in the body of an HTML doc.
    Mac-updates descriptions are HTML encoded so we have to remove them.
    """
    def __init__(self):
        self.reset()
        self.fed = []
        self.begin_body_tag = False

    def handle_data(self, d):
        if self.begin_body_tag:
            self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.begin_body_tag = True

    def handle_endtag(self, tag):
        if tag == 'body':
            self.begin_body_tag = False
