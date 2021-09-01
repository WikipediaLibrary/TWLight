from html.parser import HTMLParser


class MyCollectionsAccessParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        self.hrefs = []
        self.href = None
        super().__init__()

    def return_data(self):
        return self.hrefs

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for i, attr in enumerate(attrs):
                prev_attr = None
                if 0 <= i - 1 < len(attrs):
                    prev_attr = attrs[i - 1]
                if (
                    attr[0] == "class"
                    and attr[1] == "btn btn-sm access-apply-button"
                    and prev_attr
                    and prev_attr[0] == "href"
                ):
                    self.href = prev_attr[1]

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.hrefs.append(self.href)
            self.href = None


class MyAppsWithdrawParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        self.forms = []
        self.form = {}
        super().__init__()

    def return_data(self):
        return self.forms

    def handle_starttag(self, tag, attrs):
        if tag == "form":
            for attr in attrs:
                if attr[0] == "action":
                    self.form["action"] = attr[1]

        if tag == "input" and "action" in self.form:
            for i, attr in enumerate(attrs):
                next_attr = None
                if 0 <= i + 1 < len(attrs):
                    next_attr = attrs[i + 1]
                if (
                    attr[0] == "name"
                    and attr[1] == "csrfmiddlewaretoken"
                    and next_attr
                    and next_attr[0] == "value"
                ):
                    self.form["csrfmiddlewaretoken"] = next_attr[1]
                if (
                    attr[0] == "type"
                    and attr[1] == "submit"
                    and next_attr
                    and next_attr[0] == "value"
                    and next_attr[1] == "Withdraw"
                ):
                    self.form["submit"] = next_attr[1]

    def handle_endtag(self, tag):
        if tag == "form":
            if all(
                key in self.form
                for key in (
                    "action",
                    "csrfmiddlewaretoken",
                    "submit",
                )
            ):
                self.forms.append(self.form)
            self.form = {}
