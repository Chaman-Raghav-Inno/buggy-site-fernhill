"""Fernhill's server-side planted bugs stay planted (BUGS.md) and nothing it serves gives them away."""

import datetime as dt
import http.cookiejar
import json
import re
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

import pytest

from fernhill import data, server


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, base: str):
        self.base = base
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect())

    def request(self, path: str, body=None) -> tuple[int, bytes, dict]:
        payload = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=payload, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as err:
            return err.code, err.read(), dict(err.headers)

    def get(self, path: str, **query):
        status, raw, _ = self.request(path + ("?" + urlencode(query) if query else ""))
        return status, json.loads(raw)

    def post(self, path: str, body: dict | None = None):
        status, raw, _ = self.request(path, body or {})
        return status, json.loads(raw)

    def login(self, who: str) -> int:
        return self.post("/api/login", {"email": f"{who}@fernhill.test", "password": data.PASSWORD})[0]


@pytest.fixture
def base_url():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(server.Store()))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture
def sara(base_url):
    c = Client(base_url)
    assert c.login("sara") == 200
    return c


@pytest.fixture
def visitor(base_url):
    return Client(base_url)


def titles(result: dict) -> list[str]:
    return [c["title"] for c in result["courses"]]


def test_pages_and_access(visitor):
    for path in ("/", "/course", "/help", "/login"):
        assert visitor.request(path)[0] == 200, path
    status, _, headers = visitor.request("/dashboard")
    assert status == 302 and headers["Location"] == "/login?next=%2Fdashboard"
    assert visitor.request("/nope")[0] == 404 and visitor.request("/healthz")[1] == b"ok"
    assert visitor.post("/api/login", {"email": "sara@fernhill.test", "password": "x"})[0] == 401
    ian = Client(visitor.base)
    ian.login("ian")
    assert ian.request("/learn")[0] == 403 and ian.request("/teach")[0] == 200


def test_answer_key_is_never_served_or_hinted(visitor):
    for path in ("/BUGS.md", "/static/../BUGS.md", "/server.py", "/data.py"):
        assert visitor.request(path)[0] == 404, path
    for folder in (server.STATIC_DIR, server.PAGES_DIR):
        for f in folder.iterdir():
            assert not re.search(r"bug|planted", f.read_text(), re.I), f.name


def test_catalog(visitor):
    assert titles(visitor.get("/api/courses", q="espanol")[1]) == []  # BUG-01
    assert titles(visitor.get("/api/courses", q="Español")[1]) == ["Español para viajeros"]
    first = visitor.get("/api/courses")[1]
    assert first["total"] == 13 and len(first["courses"]) == server.PAGE_SIZE == 6  # BUG-02: the page asks for 5


def test_enrolment_rules(sara):
    assert sara.post("/api/courses/4/enroll")[1]["enrolled"] == 31  # BUG-05: 30 seats
    course = sara.post("/api/courses/2/enroll")[1]
    assert course["enrolled_me"] and not course["prereq"]["met"]  # BUG-06


def test_progress_counts_a_lesson_twice(sara):  # BUG-09
    assert sara.get("/api/courses/1")[1]["progress"] == 58
    done = sara.post("/api/progress", {"lesson": 101, "done": True})[1]
    assert done["progress"] == 67 and len(done["done"]) == 7


def test_quiz_marking():
    quiz = data.QUIZ_2
    right = server.Store.right
    assert right(quiz[1], [0])  # BUG-14
    assert not right(quiz[2], "3.0")  # BUG-15
    assert not right(quiz[3], "Def ")  # BUG-16
    assert right(quiz[3], "def") and right(quiz[2], "3")


def test_attempts(sara):
    perfect = [q["answer"] if q["type"] != "number" else str(q["answer"]) for q in data.QUIZ_2]
    for answers in (perfect, [], []):
        status, started = sara.post("/api/quizzes/2/start")
        assert status == 200  # BUG-18: the third attempt is allowed
        sara.post("/api/quizzes/2/submit", {"attempt": started["attempt"], "answers": answers})
    assert sara.post("/api/quizzes/2/start")[0] == 409
    quiz2 = next(i for i in sara.get("/api/grades/1")[1]["items"] if i["title"].startswith("Quiz 2"))
    assert quiz2["status"] == "0 / 9"  # BUG-19: the last attempt, not the best


def test_gradebook(sara):
    g = sara.get("/api/grades/1")[1]
    items = {i["title"]: i for i in g["items"]}
    assert items["Quiz 3: Practice on syntax"].get("dropped")  # BUG-28: 90% dropped, 60% kept
    assert items["Shopping list program"]["pct"] == 0.0  # BUG-29
    assert items["Temperature converter"]["status"] == "2.4 / 10"  # BUG-25: 7 days late, capped would be 4
    assert g["overall"] == 28.0  # BUG-27: weighted 40/60 it is 60


def test_resubmit_wipes_the_grade(sara):  # BUG-24
    a = sara.post("/api/assignments/1/submit", {"file": "converter.py", "size": 900})[1]
    assert a["submission"]["score"] is None


def test_certificates(sara):
    photo = sara.get("/api/certificates/8")[1]
    issued = dt.datetime.fromisoformat(photo["date"])
    enrolled = dt.datetime.now(dt.UTC) - dt.timedelta(days=40)  # finished 5 days ago
    assert photo["eligible"] and abs(issued - enrolled) < dt.timedelta(minutes=5)  # BUG-31
    for lesson in (108, 109, 110, 111):
        sara.post("/api/progress", {"lesson": lesson, "done": True})
    cert = sara.get("/api/certificates/1")[1]
    assert cert["progress"] == 92 and cert["grade"] < server.PASS_MARK and cert["eligible"]  # BUG-30


def test_forum(sara):
    p1 = [t["id"] for t in sara.get("/api/forum/1", page=1)[1]["threads"]]
    p2 = [t["id"] for t in sara.get("/api/forum/1", page=2)[1]["threads"]]
    assert p1[-1] == p2[0]  # BUG-32
    sara.post("/api/posts/1/like")
    assert sara.post("/api/posts/1/like")[1]["likes"] == 2  # BUG-33
    sara.post("/api/threads/13/reply", {"body": "Same here."})
    listed = next(t for t in sara.get("/api/forum/1")[1]["threads"] if t["id"] == 13)
    assert listed["reply_count"] == 0  # BUG-34
    assert sara.post("/api/threads/13/reply", {"body": "x" * 1001})[0] == 400
    assert sara.post("/api/posts/1/edit", {"body": "x" * 1500})[1]["body"] == "x" * 1500  # BUG-35


def test_instructor(base_url):
    ian = Client(base_url)
    ian.login("ian")
    queue = ian.get("/api/teach")[1]["queue"]
    a2 = [q for q in queue if q["assignment_id"] == 2]
    assert ian.post("/api/teach/grade", {"submission": a2[0]["id"], "score": 15})[0] == 200  # BUG-40
    assert ian.post("/api/teach/grade", {"submission": a2[0]["id"], "score": -1})[0] == 400
    released = ian.post("/api/teach/release", {"assignment": 2})[1]["queue"]
    assert [q["score"] for q in released if q["assignment_id"] == 2][1:] == [0, 0, 0, 0]  # BUG-39
    status, raw, headers = ian.request("/api/teach/roster/1.csv")
    pat = next(line for line in raw.decode().splitlines() if line.startswith("Pat"))
    assert headers["Content-Type"].startswith("text/csv") and len(pat.split(",")) == 4  # BUG-38


def test_bad_requests(sara):
    assert sara.get("/api/courses/999")[0] == 404
    assert sara.get("/api/quizzes/1")[0] == 404
    assert sara.get("/api/lessons/160")[0] == 403
    assert sara.post("/api/assignments/1/submit", {"file": "notes.exe"})[0] == 400
