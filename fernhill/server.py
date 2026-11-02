"""Fernhill Academy: an online-learning site with planted functional bugs, for checking what the AI QA Scanner finds.

The bugs are listed in BUGS.md (the answer key), which is never served. Comments marking a planted bug (BUG-nn)
only appear in server-side code; the pages and scripts the scanner reads carry none.

Each visitor (cookie) gets a private copy of the demo world, kept in memory, so parallel scans never see each
other's changes. Logging in as the student or the instructor in the same browser shares that world.
"""

import datetime as dt
import hmac
import html
import json
import math
import os
import re
import secrets
import threading
import time
from collections import OrderedDict
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from . import data

HERE = Path(__file__).resolve().parent
PAGES_DIR = HERE / "pages"
STATIC_DIR = HERE / "static"
STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"
    ),
}
MAX_BODY = 3 * 1024 * 1024
MAX_SESSIONS = 1500
PAGE_SIZE = 6
FORUM_PAGE = 5
MAX_FILE = 2 * 1024 * 1024
FILE_TYPES = (".pdf", ".txt", ".docx", ".py")
LATE_PER_DAY, LATE_CAP = 0.10, 0.50
WEIGHTS = {"quiz": 0.40, "assignment": 0.60}
PASS_MARK = 70

# path -> (page, title, who may open it)
PAGES = {
    "/": ("catalog", "Courses", None),
    "/course": ("course", "Course", None),
    "/help": ("help", "How grading works", None),
    "/login": ("login", "Log in", None),
    "/dashboard": ("dashboard", "My learning", "student"),
    "/learn": ("learn", "Lesson", "student"),
    "/quiz": ("quiz", "Quiz", "student"),
    "/assignment": ("assignment", "Assignment", "student"),
    "/grades": ("grades", "Grades", "student"),
    "/certificate": ("certificate", "Certificate", "student"),
    "/forum": ("forum", "Discussion", "student"),
    "/thread": ("thread", "Discussion", "student"),
    "/teach": ("teach", "Teaching", "instructor"),
}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _text(body: dict, key: str, limit: int = 200) -> str:
    value = body.get(key, "")
    return value.strip()[:limit] if isinstance(value, str) else ""


def _int(value, message: str, low: int = 0, high: int = 10**9) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, message) from None
    if not low <= n <= high:
        raise ApiError(400, message)
    return n


def iso(ts: int) -> str:
    return dt.datetime.fromtimestamp(ts, dt.UTC).isoformat()


class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.sessions: OrderedDict[str, dict] = OrderedDict()

    def session(self, sid: str | None) -> tuple[str, dict]:
        if sid and sid in self.sessions:
            self.sessions.move_to_end(sid)
            return sid, self.sessions[sid]
        sid = secrets.token_urlsafe(24)
        self.sessions[sid] = {"world": None, "user": None}
        while len(self.sessions) > MAX_SESSIONS:
            self.sessions.popitem(last=False)
        return sid, self.sessions[sid]

    @staticmethod
    def world(sess: dict) -> dict:
        if sess["world"] is None:
            sess["world"] = data.world(time.time())
        return sess["world"]

    def user(self, sess: dict) -> dict | None:
        if sess["user"] is None:
            return None
        return next((u for u in self.world(sess)["users"] if u["id"] == sess["user"]), None)

    def signed_in(self, sess: dict, role: str) -> tuple[dict, dict]:
        user = self.user(sess)
        if not user:
            raise ApiError(401, "Please log in.")
        if user["role"] != role:
            raise ApiError(403, "That is for " + ("students." if role == "student" else "instructors."))
        return self.world(sess), user

    @staticmethod
    def course(w: dict, cid) -> dict:
        found = next((c for c in w["courses"] if c["id"] == cid), None)
        if not found:
            raise ApiError(404, "We couldn't find that course.")
        return found

    @staticmethod
    def lessons(course: dict) -> list[dict]:
        return [lesson for m in course["modules"] for lesson in m["lessons"]]

    def me(self, sess: dict) -> dict:
        user = self.user(sess)
        return {"user": {k: user[k] for k in ("id", "name", "email", "role")} if user else None}

    # catalog and courses

    def card(self, c: dict) -> dict:
        minutes = sum(lesson["minutes"] for lesson in self.lessons(c))
        keys = ("id", "title", "topic", "level", "seats", "enrolled", "rating", "reviews", "summary")
        return {k: c[k] for k in keys} | {"minutes": minutes, "lessons": len(self.lessons(c))}

    def catalog(self, sess: dict, query: dict) -> dict:
        w = self.world(sess)
        arg = {k: (query.get(k) or [""])[0] for k in query}
        q = arg.get("q", "").strip().lower()
        found = []
        for c in w["courses"]:
            if q and q not in c["title"].lower() and q not in c["topic"].lower():  # BUG-01: no accent folding
                continue
            if arg.get("topic") and c["topic"] != arg["topic"]:
                continue
            if arg.get("level") and c["level"] != arg["level"]:
                continue
            found.append(c)
        sort = arg.get("sort") or "popular"
        if sort == "rating":
            found.sort(key=lambda c: (-c["rating"], c["id"]))
        elif sort == "newest":
            found.sort(key=lambda c: -c["published"])
        else:
            found.sort(key=lambda c: (-c["enrolled"], c["id"]))
        offset = _int(arg.get("offset") or 0, "Bad offset.")
        return {"courses": [self.card(c) for c in found[offset : offset + PAGE_SIZE]], "total": len(found)}

    def progress(self, w: dict, course: dict, uid: int) -> int | None:
        e = w["enrollments"].get(course["id"], {}).get(uid)
        if not e:
            return None
        return round(100 * len(e["done"]) / len(self.lessons(course)))

    def course_view(self, sess: dict, cid: int) -> dict:
        w = self.world(sess)
        c = self.course(w, cid)
        user = self.user(sess)
        out = self.card(c) | {"modules": c["modules"], "instructor": next(
            (u["name"] for u in w["users"] if u["id"] == c["instructor"]), "Fernhill staff")}  # fmt: skip
        if c["prereq"]:
            pre = self.course(w, c["prereq"])
            met = bool(user) and self.progress(w, pre, user["id"]) == 100
            out["prereq"] = {"id": pre["id"], "title": pre["title"], "met": met}
        uid = user["id"] if user else None
        e = w["enrollments"].get(cid, {}).get(uid)
        out["enrolled_me"] = bool(e)
        out["progress"] = self.progress(w, c, uid) if e else None
        out["done"] = list(dict.fromkeys(e["done"])) if e else []
        out["last"] = e["last"] if e else None
        quizzes = [q for q in w["quizzes"] if q["course"] == cid]
        out["quizzes"] = [{"id": q["id"], "title": q["title"], "open": bool(q["questions"])} for q in quizzes]
        out["assignments"] = [
            {"id": a["id"], "title": a["title"], "due": iso(a["due"])} for a in w["assignments"] if a["course"] == cid
        ]
        return out

    def enroll(self, sess: dict, cid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        c = self.course(w, cid)
        if user["id"] in w["enrollments"].get(cid, {}):
            raise ApiError(409, "You're already enrolled.")
        # BUG-05: a full course (enrolled == seats) is not refused
        # BUG-06: the prerequisite is not checked
        c["enrolled"] += 1
        w["enrollments"].setdefault(cid, {})[user["id"]] = {"since": int(time.time()), "done": [], "last": None}
        w["enrollments"][cid][user["id"]]["notes"] = {}
        return self.course_view(sess, cid)

    # lessons

    def lesson_ctx(self, w: dict, user: dict, lid: int) -> tuple[dict, dict, dict]:
        for c in w["courses"]:
            for lesson in self.lessons(c):
                if lesson["id"] == lid:
                    e = w["enrollments"].get(c["id"], {}).get(user["id"])
                    if not e:
                        raise ApiError(403, "Enroll in the course to open its lessons.")
                    return c, lesson, e
        raise ApiError(404, "We couldn't find that lesson.")

    def lesson(self, sess: dict, lid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        c, lesson, e = self.lesson_ctx(w, user, lid)
        e["last"] = lid
        return {
            "lesson": lesson,
            "course": {"id": c["id"], "title": c["title"], "modules": c["modules"]},
            "done": list(dict.fromkeys(e["done"])),
            "notes": e["notes"].get(str(lid), ""),
            "progress": self.progress(w, c, user["id"]),
        }

    def mark(self, sess: dict, body: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        c, lesson, e = self.lesson_ctx(w, user, _int(body.get("lesson"), "Choose a lesson."))
        if body.get("done"):
            e["done"].append(lesson["id"])  # BUG-09: a list, so ticking a lesson and then pressing Next counts it twice
            if len(set(e["done"])) == len(self.lessons(c)):
                e.setdefault("finished", int(time.time()))
        elif lesson["id"] in e["done"]:
            e["done"].remove(lesson["id"])
        return {"progress": self.progress(w, c, user["id"]), "done": list(dict.fromkeys(e["done"]))}

    def notes(self, sess: dict, body: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        c, lesson, e = self.lesson_ctx(w, user, _int(body.get("lesson"), "Choose a lesson."))
        e["notes"][str(lesson["id"])] = _text(body, "text", 5000)
        return {"ok": True}

    # quizzes

    def quiz_obj(self, w: dict, qid: int) -> dict:
        q = next((q for q in w["quizzes"] if q["id"] == qid), None)
        if not q or not q["questions"]:
            raise ApiError(404, "We couldn't find that quiz.")
        return q

    def quiz(self, sess: dict, qid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        q = self.quiz_obj(w, qid)
        mine = [a for a in w["attempts"] if a["quiz"] == qid and a["user"] == user["id"] and a.get("finished")]
        questions = [{k: v for k, v in item.items() if k != "answer"} for item in q["questions"]]
        return {
            "id": q["id"],
            "course": q["course"],
            "title": q["title"],
            "minutes": q["minutes"],
            "max_attempts": q["max_attempts"],
            "used": len(mine),
            "attempts": [{"score": a["score"], "total": a["total"]} for a in mine],
            "questions": questions,
        }

    def start(self, sess: dict, qid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        q = self.quiz_obj(w, qid)
        used = sum(1 for a in w["attempts"] if a["quiz"] == qid and a["user"] == user["id"] and a.get("finished"))
        if used > q["max_attempts"]:  # BUG-18: allows one attempt more than the limit
            raise ApiError(409, "You've used all your attempts.")
        attempt = {"id": w["next_id"], "quiz": qid, "user": user["id"], "started": int(time.time())}
        w["next_id"] += 1
        w["attempts"].append(attempt)
        return {"attempt": attempt["id"], "minutes": q["minutes"]}

    @staticmethod
    def right(question: dict, given) -> bool:
        kind, answer = question["type"], question["answer"]
        if kind == "single":
            return isinstance(given, list) and given == answer
        if kind == "multi":
            return isinstance(given, list) and any(g in answer for g in given)  # BUG-14: one right pick is enough
        if kind == "number":
            return str(given).strip() == str(answer)  # BUG-15: "3.0" is not 3
        return given == answer  # BUG-16: should ignore case and surrounding spaces

    def submit(self, sess: dict, qid: int, body: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        q = self.quiz_obj(w, qid)
        aid = _int(body.get("attempt"), "Start the quiz first.")
        attempt = next((a for a in w["attempts"] if a["id"] == aid and a["user"] == user["id"]), None)
        if not attempt or attempt["quiz"] != qid:
            raise ApiError(404, "Start the quiz first.")
        if attempt.get("finished"):
            raise ApiError(409, "This attempt was already submitted.")
        answers = body.get("answers") if isinstance(body.get("answers"), list) else []
        review, score = [], 0
        for i, question in enumerate(q["questions"]):
            given = answers[i] if i < len(answers) else None
            ok = self.right(question, given)
            score += ok
            review.append({"ok": ok, "given": given, "answer": question["answer"]})
        attempt.update(score=score, total=len(q["questions"]), finished=int(time.time()))
        return {"score": score, "total": len(q["questions"]), "review": review}

    # assignments

    def assignment_obj(self, w: dict, aid: int) -> dict:
        a = next((a for a in w["assignments"] if a["id"] == aid), None)
        if not a:
            raise ApiError(404, "We couldn't find that assignment.")
        return a

    @staticmethod
    def days_late(a: dict, sub: dict) -> int:
        return max(0, math.ceil((sub["submitted"] - a["due"]) / data.DAY))

    def graded(self, a: dict, sub: dict) -> float | None:
        """The score after any late penalty, or None if not released."""
        if not sub or not sub["released"] or sub["score"] is None:
            return None
        penalty = LATE_PER_DAY * self.days_late(a, sub)  # BUG-25: the penalty is capped at 50%
        return round(sub["score"] * (1 - penalty), 2)

    def assignment(self, sess: dict, aid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        a = self.assignment_obj(w, aid)
        sub = next((s for s in w["submissions"] if s["assignment"] == aid and s["user"] == user["id"]), None)
        out = {k: a[k] for k in ("id", "course", "title", "points", "brief", "min_words")} | {"due": iso(a["due"])}
        if sub:
            out["submission"] = {
                "submitted": iso(sub["submitted"]),
                "file": sub["file"],
                "size": sub["size"],
                "text": sub["text"],
                "days_late": self.days_late(a, sub),
                "raw": sub["score"] if sub["released"] else None,
                "score": self.graded(a, sub),
            }
        return out

    def hand_in(self, sess: dict, aid: int, body: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        self.assignment_obj(w, aid)  # 404 for unknown ids
        text = body.get("text") if isinstance(body.get("text"), str) else ""
        name = _text(body, "file", 120)
        size = _int(body.get("size") or 0, "Bad file size.")
        if not name and not text.strip():
            raise ApiError(400, "Attach a file or write your answer.")
        if name and not name.lower().endswith(FILE_TYPES):
            raise ApiError(400, "Upload a .pdf, .txt, .docx or .py file.")
        if size > MAX_FILE:
            raise ApiError(400, "Files can be at most 2 MB.")
        sub = next((s for s in w["submissions"] if s["assignment"] == aid and s["user"] == user["id"]), None)
        if not sub:
            sub = {"id": w["next_id"], "assignment": aid, "user": user["id"]}
            w["next_id"] += 1
            w["submissions"].append(sub)
        sub.update(submitted=int(time.time()), file=name, size=size, text=text[:20000])
        sub.update(score=None, released=False)  # BUG-24: a resubmission wipes the grade until regraded
        return self.assignment(sess, aid)

    # grades and certificates

    def gradebook(self, sess: dict, cid: int, uid: int | None = None) -> dict:
        w = self.world(sess)
        if uid is None:
            w, user = self.signed_in(sess, "student")
            uid = user["id"]
        c = self.course(w, cid)
        now = time.time()
        items = []
        quiz_scores = []
        for q in (q for q in w["quizzes"] if q["course"] == cid):
            mine = [a for a in w["attempts"] if a["quiz"] == q["id"] and a["user"] == uid and a.get("finished")]
            if not mine:
                items.append({"kind": "quiz", "title": q["title"], "status": "Not taken", "pct": None})
                continue
            pick = mine[-1]  # BUG-19: the policy is the best attempt
            pct = round(100 * pick["score"] / pick["total"])
            quiz_scores.append(pct)
            items.append({"kind": "quiz", "title": q["title"], "status": f"{pick['score']} / {pick['total']}",
                          "pct": pct})  # fmt: skip
        if len(quiz_scores) > 1:
            dropped = max(quiz_scores)  # BUG-28: the lowest quiz is the one dropped
            for item in items:
                if item["kind"] == "quiz" and item["pct"] == dropped:
                    item["dropped"] = True
                    break
        for a in (a for a in w["assignments"] if a["course"] == cid):
            sub = next((s for s in w["submissions"] if s["assignment"] == a["id"] and s["user"] == uid), None)
            score = self.graded(a, sub)
            if score is not None:
                pct, status = round(100 * score / a["points"], 1), f"{score:g} / {a['points']}"
            elif sub:
                pct, status = 0.0, "Submitted, not graded yet"  # BUG-29: pending work should not count
            elif a["due"] < now:
                pct, status = 0.0, "Missing"
            else:
                pct, status = None, "Not due yet"
            items.append({"kind": "assignment", "title": a["title"], "status": status, "pct": pct})
        counted = [i["pct"] for i in items if i["pct"] is not None and not i.get("dropped")]
        overall = round(sum(counted) / len(counted), 1) if counted else None  # BUG-27: ignores the 40/60 weights
        return {"course": {"id": c["id"], "title": c["title"]}, "items": items, "overall": overall}

    def certificate(self, sess: dict, cid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        c = self.course(w, cid)
        e = w["enrollments"].get(cid, {}).get(user["id"])
        if not e:
            raise ApiError(403, "Enroll in the course first.")
        progress = self.progress(w, c, user["id"])
        grade = self.gradebook(sess, cid)["overall"]
        eligible = progress >= 90  # BUG-30: needs every lesson done and a grade of 70 or more
        return {
            "course": c["title"],
            "name": user["name"],
            "progress": progress,
            "grade": grade,
            "eligible": eligible,
            "date": iso(e["since"]),  # BUG-31: should be the day the course was finished
        }

    # forum

    def forum(self, sess: dict, cid: int, query: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        self.course(w, cid)
        threads = [t for t in w["threads"] if t["course"] == cid]
        page = _int((query.get("page") or ["1"])[0], "Bad page.", 1, 1000)
        start = max(0, (page - 1) * FORUM_PAGE - 1)  # BUG-32: page 2 onwards starts one thread early
        keys = ("id", "title", "author", "created", "likes", "reply_count")
        return {
            "threads": [{k: t[k] for k in keys} for t in threads[start : start + FORUM_PAGE]],
            "page": page,
            "pages": max(1, math.ceil(len(threads) / FORUM_PAGE)),
        }

    def new_thread(self, sess: dict, cid: int, body: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        self.course(w, cid)
        title, text = _text(body, "title", 120), _text(body, "body", 5000)
        if not title or not text:
            raise ApiError(400, "Write a title and a message.")
        if len(text) > 1000:
            raise ApiError(400, "Posts can be at most 1,000 characters.")
        t = {"id": w["next_id"], "course": cid, "title": title, "author": user["name"], "created": int(time.time()),
             "body": text, "likes": 0, "replies": [], "reply_count": 0}  # fmt: skip
        w["next_id"] += 1
        w["threads"].insert(0, t)
        return {"id": t["id"]}

    def thread_obj(self, w: dict, tid: int) -> dict:
        t = next((t for t in w["threads"] if t["id"] == tid), None)
        if not t:
            raise ApiError(404, "We couldn't find that discussion.")
        return t

    def thread(self, sess: dict, tid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        t = self.thread_obj(w, tid)
        return {k: t[k] for k in ("id", "course", "title", "author", "created", "body", "likes", "replies")} | {
            "me": user["name"]
        }

    def reply(self, sess: dict, tid: int, body: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        t = self.thread_obj(w, tid)
        text = _text(body, "body", 5000)
        if not text:
            raise ApiError(400, "Write a reply first.")
        if len(text) > 1000:
            raise ApiError(400, "Posts can be at most 1,000 characters.")
        t["replies"].append({"id": w["next_id"], "author": user["name"], "body": text, "created": int(time.time()),
                             "likes": 0})  # fmt: skip
        w["next_id"] += 1
        # BUG-34: reply_count is not updated
        return self.thread(sess, tid)

    def post_obj(self, w: dict, pid: int) -> tuple[dict, dict]:
        for t in w["threads"]:
            if t["id"] == pid:
                return t, t
            for r in t["replies"]:
                if r["id"] == pid:
                    return t, r
        raise ApiError(404, "We couldn't find that post.")

    def like(self, sess: dict, pid: int) -> dict:
        w, user = self.signed_in(sess, "student")
        t, post = self.post_obj(w, pid)
        post["likes"] += 1  # BUG-33: one like per person
        return self.thread(sess, t["id"])

    def edit(self, sess: dict, pid: int, body: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        t, post = self.post_obj(w, pid)
        if post["author"] != user["name"]:
            raise ApiError(403, "You can only edit your own posts.")
        text = _text(body, "body", 5000)  # BUG-35: edits skip the 1,000-character limit
        if not text:
            raise ApiError(400, "Write something first.")
        post["body"] = text
        return self.thread(sess, t["id"])

    # dashboard

    def dashboard(self, sess: dict) -> dict:
        w, user = self.signed_in(sess, "student")
        mine = []
        for c in w["courses"]:
            e = w["enrollments"].get(c["id"], {}).get(user["id"])
            if not e:
                continue
            first = self.lessons(c)[0]["id"]
            mine.append(self.card(c) | {"progress": self.progress(w, c, user["id"]), "last": e["last"],
                                        "first": first, "grade": self.gradebook(sess, c["id"])["overall"]})  # fmt: skip
        now = time.time()
        due = []
        for a in w["assignments"]:
            if a["due"] < now or user["id"] not in w["enrollments"].get(a["course"], {}):
                continue
            sub = any(s["assignment"] == a["id"] and s["user"] == user["id"] for s in w["submissions"])
            due.append({"id": a["id"], "title": a["title"], "due": iso(a["due"]), "submitted": sub})
        return {"courses": mine, "due": due}

    # teaching

    def teach(self, sess: dict) -> dict:
        w, user = self.signed_in(sess, "instructor")
        names = {s["id"]: s["name"] for s in w["students"]}
        courses = [self.card(c) for c in w["courses"] if c["instructor"] == user["id"]]
        mine = {c["id"] for c in courses}
        queue = []
        for a in w["assignments"]:
            if a["course"] not in mine:
                continue
            for s in w["submissions"]:
                if s["assignment"] == a["id"]:
                    queue.append({"id": s["id"], "assignment": a["title"], "assignment_id": a["id"],
                                  "points": a["points"], "student": names.get(s["user"], "Student"),
                                  "submitted": iso(s["submitted"]), "file": s["file"], "score": s["score"],
                                  "released": s["released"]})  # fmt: skip
        return {"courses": courses, "queue": queue}

    def grade(self, sess: dict, body: dict) -> dict:
        w, user = self.signed_in(sess, "instructor")
        sid = _int(body.get("submission"), "Choose a submission.")
        sub = next((s for s in w["submissions"] if s["id"] == sid), None)
        if not sub:
            raise ApiError(404, "We couldn't find that submission.")
        score = body.get("score")
        if isinstance(score, bool) or not isinstance(score, int | float) or score < 0:
            raise ApiError(400, "Enter a score of 0 or more.")
        # BUG-40: a score above the assignment's points is accepted
        sub["score"] = score
        return self.teach(sess)

    def release(self, sess: dict, body: dict) -> dict:
        w, user = self.signed_in(sess, "instructor")
        aid = _int(body.get("assignment"), "Choose an assignment.")
        self.assignment_obj(w, aid)
        for s in w["submissions"]:
            if s["assignment"] == aid:
                if s["score"] is None:
                    s["score"] = 0  # BUG-39: ungraded work should stay unreleased
                s["released"] = True
        return self.teach(sess)

    def roster_csv(self, sess: dict, cid: int) -> bytes:
        w, user = self.signed_in(sess, "instructor")
        c = self.course(w, cid)
        lines = ["Student,Email,Progress"]
        for s in w["students"]:
            email = re.sub(r"[^a-z]", "", s["name"].lower().split(",")[0]) + "@students.fernhill.test"
            progress = self.progress(w, c, s["id"]) if s["id"] == 1 else 50 + (s["id"] * 7) % 50
            lines.append(f"{s['name']},{email},{progress}%")  # BUG-38: names with commas aren't quoted
        return ("\n".join(lines) + "\n").encode()

    def login(self, sess: dict, body: dict) -> dict:
        w = self.world(sess)
        email = _text(body, "email").lower()
        u = next((u for u in w["users"] if u["email"] == email), None)
        password = body.get("password")
        if not (u and isinstance(password, str)) or not hmac.compare_digest(
            u["hash"], data.password_hash(password, bytes.fromhex(u["salt"]))
        ):
            raise ApiError(401, "Incorrect email or password.")
        sess["user"] = u["id"]
        return self.me(sess)


def render(path: str, me: dict, status_page: str | None = None) -> bytes:
    name, title, _ = PAGES[path] if not status_page else (status_page, "Page not found", None)
    if status_page == "403":
        title = "Not for this account"
    user = me["user"]
    if not user:
        nav = '<a href="/" data-nav="catalog">Courses</a><a href="/help" data-nav="help">Grading</a>'
        account = '<a href="/login" id="login-link">Log in</a>'
    else:
        nav = '<a href="/" data-nav="catalog">Courses</a>'
        nav += (
            '<a href="/dashboard" data-nav="dashboard">My learning</a>'
            if user["role"] == "student"
            else '<a href="/teach" data-nav="teach">Teaching</a>'
        )
        nav += '<a href="/help" data-nav="help">Grading</a>'
        account = f'<span class="who">{html.escape(user["name"].split()[0])}</span>'
        account += '<button type="button" id="logout" class="link">Log out</button>'
    script = f'<script src="/static/{name}.js" defer></script>' if (STATIC_DIR / f"{name}.js").exists() else ""
    out = (PAGES_DIR / "_layout.html").read_text()
    values = {
        "title": html.escape(title),
        "page": name,
        "role": user["role"] if user else "",
        "nav": nav,
        "account": account,
        "content": (PAGES_DIR / f"{name}.html").read_text(),
        "scripts": script,
    }
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    return out.encode()


def make_handler(store: Store | None = None):
    store = store or Store()
    static = {f.name: f for f in STATIC_DIR.iterdir() if f.is_file() and f.suffix in STATIC_TYPES}

    class Handler(BaseHTTPRequestHandler):
        server_version = "fernhill"

        def log_message(self, fmt, *args):
            pass

        def _session(self) -> tuple[str, dict, bool]:
            sid = None
            try:
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                sid = cookie["fh_sid"].value if "fh_sid" in cookie else None
            except CookieError:
                pass
            new_sid, sess = store.session(sid)
            return new_sid, sess, new_sid != sid

        def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in {**SECURITY_HEADERS, **(extra or {})}.items():
                self.send_header(k, v)
            if self._new_sid:
                secure = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
                self.send_header("Set-Cookie", f"fh_sid={self._sid}; Path=/; HttpOnly; SameSite=Lax{secure}")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, payload: dict):
            self._send(status, json.dumps(payload).encode(), "application/json")

        def _body(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise ApiError(400, "Bad request.") from None
            if length > MAX_BODY:
                raise ApiError(413, "Request too large.")
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                payload = json.loads(raw or b"{}")
            except ValueError:
                raise ApiError(400, "Send JSON.") from None
            if not isinstance(payload, dict):
                raise ApiError(400, "Send a JSON object.")
            return payload

        def do_HEAD(self):
            self._handle("GET")

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def _handle(self, method: str):
            self._sid, self._new_sid = None, False
            url = urlsplit(self.path)
            path = url.path.rstrip("/") or "/"
            query = parse_qs(url.query)
            try:
                if path == "/healthz":
                    return self._send(200, b"ok", "text/plain")
                if path == "/robots.txt":
                    return self._send(200, b"User-agent: *\nAllow: /\n", "text/plain")
                if path.startswith("/static/") and path[8:] in static:
                    f = static[path[8:]]
                    return self._send(200, f.read_bytes(), STATIC_TYPES[f.suffix])
                with store.lock:
                    self._sid, sess, self._new_sid = self._session()
                    if path.startswith("/api/"):
                        body = self._body() if method == "POST" else {}
                        result = self._api(sess, method, path, body, query)
                        if isinstance(result, bytes):
                            extra = {"Content-Disposition": 'attachment; filename="roster.csv"'}
                            return self._send(200, result, "text/csv; charset=utf-8", extra)
                        return self._json(200, result)
                    if method != "GET":
                        return self._send(405, b"Method not allowed", "text/plain", {"Allow": "GET, HEAD"})
                    me = store.me(sess)
                    if path not in PAGES:
                        return self._send(404, render("/", me, "404"), "text/html; charset=utf-8")
                    role = PAGES[path][2]
                    user = store.user(sess)
                    if role and not user:
                        location = "/login?next=" + quote(self.path, safe="")
                        return self._send(302, b"", "text/plain", {"Location": location})
                    if role and user["role"] != role:
                        return self._send(403, render("/", me, "403"), "text/html; charset=utf-8")
                    return self._send(200, render(path, me), "text/html; charset=utf-8")
            except ApiError as err:
                return self._json(err.status, {"ok": False, "error": str(err)})
            except Exception:
                return self._json(500, {"ok": False, "error": "Internal Server Error"})

        def _api(self, sess: dict, method: str, path: str, body: dict, query: dict):
            if method == "GET":
                gets = {
                    "/api/me": lambda: store.me(sess),
                    "/api/courses": lambda: store.catalog(sess, query),
                    "/api/dashboard": lambda: store.dashboard(sess),
                    "/api/teach": lambda: store.teach(sess),
                }
                if path in gets:
                    return gets[path]()
                routes = (
                    (r"/api/courses/(\d+)", lambda i: store.course_view(sess, int(i))),
                    (r"/api/lessons/(\d+)", lambda i: store.lesson(sess, int(i))),
                    (r"/api/quizzes/(\d+)", lambda i: store.quiz(sess, int(i))),
                    (r"/api/assignments/(\d+)", lambda i: store.assignment(sess, int(i))),
                    (r"/api/grades/(\d+)", lambda i: store.gradebook(sess, int(i))),
                    (r"/api/certificates/(\d+)", lambda i: store.certificate(sess, int(i))),
                    (r"/api/forum/(\d+)", lambda i: store.forum(sess, int(i), query)),
                    (r"/api/threads/(\d+)", lambda i: store.thread(sess, int(i))),
                    (r"/api/teach/roster/(\d+)\.csv", lambda i: store.roster_csv(sess, int(i))),
                )
            else:
                posts = {
                    "/api/login": lambda: store.login(sess, body),
                    "/api/logout": lambda: sess.update(user=None) or {"ok": True},
                    "/api/progress": lambda: store.mark(sess, body),
                    "/api/notes": lambda: store.notes(sess, body),
                    "/api/teach/grade": lambda: store.grade(sess, body),
                    "/api/teach/release": lambda: store.release(sess, body),
                }
                if path in posts:
                    return posts[path]()
                routes = (
                    (r"/api/courses/(\d+)/enroll", lambda i: store.enroll(sess, int(i))),
                    (r"/api/quizzes/(\d+)/start", lambda i: store.start(sess, int(i))),
                    (r"/api/quizzes/(\d+)/submit", lambda i: store.submit(sess, int(i), body)),
                    (r"/api/assignments/(\d+)/submit", lambda i: store.hand_in(sess, int(i), body)),
                    (r"/api/forum/(\d+)", lambda i: store.new_thread(sess, int(i), body)),
                    (r"/api/threads/(\d+)/reply", lambda i: store.reply(sess, int(i), body)),
                    (r"/api/posts/(\d+)/like", lambda i: store.like(sess, int(i))),
                    (r"/api/posts/(\d+)/edit", lambda i: store.edit(sess, int(i), body)),
                )
            for pattern, run in routes:
                m = re.fullmatch(pattern, path)
                if m:
                    return run(m.group(1))
            raise ApiError(404, "Not found.")

    return Handler


def serve(env: dict[str, str] | None = None) -> None:
    env = dict(os.environ if env is None else env)
    port = int(env.get("PORT", "8083"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), make_handler())
    print(f"Fernhill Academy listening on :{port}", flush=True)
    httpd.serve_forever()
