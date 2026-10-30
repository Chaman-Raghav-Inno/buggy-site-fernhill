"""Fernhill Academy's demo world: courses, lessons, quizzes, assignments, people and posts, dated from today.

Every visitor gets a fresh copy (see server.Store), so scans never disturb each other.
"""

import hashlib

PASSWORD = "Fernhill@2026"
SALT = b"fernhill-demo-salt"
DAY = 86400

USERS = [
    {"id": 1, "name": "Sara Lindqvist", "email": "sara@fernhill.test", "role": "student"},
    {"id": 2, "name": "Ian Mbeki", "email": "ian@fernhill.test", "role": "instructor"},
]
CLASSMATES = [
    "Pat O'Neill, Jr.",
    "Aiko Tanaka",
    "Diego Ruiz",
    "Fatima Zahra",
    "Liam Byrne",
    "Noor Haddad",
    "Ola Nordmann",
    "Priya Raman",
    "Tomás García",
    "Wei Chen",
]

# fmt: off
COURSES = [
    # id, title, topic, level, seats, enrolled, prerequisite, rating, reviews, instructor, summary
    (1, "Python Basics", "Programming", "Beginner", 120, 87, None, 4.7, 412, 2,
     "Write your first programs: variables, loops, functions and lists, with small projects along the way."),
    (2, "Data Analysis with Python", "Programming", "Intermediate", 80, 54, 1, 4.6, 233, 2,
     "Load, clean and summarise real data sets with pandas, and chart what you find."),
    (3, "Español para viajeros", "Languages", "Beginner", 60, 41, None, 4.8, 189, 3,
     "Spanish for travel: ordering food, asking directions and small talk, with audio drills."),
    (4, "UX Design Fundamentals", "Design", "Beginner", 30, 30, None, 4.5, 97, 3,
     "Research, sketch, prototype and test: the core loop of user experience design."),
    (5, "Intro to Statistics", "Math", "Beginner", 100, 63, None, 4.4, 151, 3,
     "Averages, spread, probability and sampling, explained with everyday examples."),
    (6, "Public Speaking", "Business", "Beginner", 50, 22, None, 4.3, 64, 3,
     "Plan, rehearse and deliver talks with confidence, from five minutes to fifty."),
    (7, "Machine Learning Foundations", "Programming", "Advanced", 60, 38, 2, 4.7, 120, 2,
     "Regression, classification and model evaluation, built up from first principles."),
    (8, "Digital Photography", "Arts", "Beginner", 90, 70, None, 4.9, 302, 3,
     "Exposure, composition and light: take better photos with any camera."),
    (9, "Spreadsheet Skills", "Business", "Beginner", 150, 98, None, 4.2, 88, 3,
     "Formulas, lookups, pivot tables and charts for everyday work."),
    (10, "Café Culture: French for Beginners", "Languages", "Beginner", 60, 35, None, 4.6, 77, 3,
     "Everyday French for cafés, markets and trains, with a focus on listening."),
    (11, "Financial Literacy", "Business", "Beginner", 100, 59, None, 4.5, 110, 3,
     "Budgets, saving, credit and investing basics, without the jargon."),
    (12, "Web Accessibility", "Design", "Intermediate", 70, 26, None, 4.8, 58, 3,
     "Build sites everyone can use: semantics, keyboard access, contrast and testing."),
    (13, "SQL for Analysts", "Programming", "Intermediate", 90, 47, None, 4.6, 140, 2,
     "Query, join and aggregate data with SQL, from first SELECT to window functions."),
]

PYTHON_MODULES = [
    ("Getting started", [("Why Python?", 15), ("Installing Python", 15), ("Your first program", 20),
                         ("Variables and types", 20)]),
    ("Control flow", [("Comparisons", 15), ("If statements", 20), ("While loops", 20), ("For loops", 25)]),
    ("Functions and lists", [("Defining functions", 15), ("Parameters and return", 20), ("Lists", 20),
                             ("Project: to-do list", 20)]),
]
PHOTO_MODULES = [
    ("Exposure", [("Aperture", 12), ("Shutter speed", 12), ("ISO", 10)]),
    ("Composition", [("Rule of thirds", 10), ("Leading lines", 12), ("Light and shadow", 14)]),
]

QUIZ_2 = [
    {"type": "single", "text": "Which keyword starts a loop that repeats while a condition is true?",
     "options": ["for", "while", "loop", "repeat"], "answer": [1]},
    {"type": "multi", "text": "Which of these are comparison operators in Python? Select all that apply.",
     "options": ["==", "!=", "=<", ">="], "answer": [0, 1, 3]},
    {"type": "number", "text": "How many times does the body of `for i in range(3):` run?", "answer": 3},
    {"type": "text", "text": "Which keyword defines a function? (one word)", "answer": "def"},
    {"type": "single", "text": "What does `break` do inside a loop?",
     "options": ["Skips to the next iteration", "Leaves the loop", "Pauses the program", "Restarts the loop"],
     "answer": [1]},
    {"type": "single", "text": "What does `print(10 // 3)` print?", "options": ["3", "3.33", "4", "1"], "answer": [0]},
    {"type": "multi", "text": "Which of these values are falsy? Select all that apply.",
     "options": ["0", '""', "[]", '"False"'], "answer": [0, 1, 2]},
    {"type": "single", "text": "Which statement skips to the next iteration of a loop?",
     "options": ["pass", "continue", "skip", "next"], "answer": [1]},
    {"type": "number", "text": "What is `2 ** 3`?", "answer": 8},
]
# fmt: on

FORUM_TITLES = [
    "How do I install Python on a Chromebook?",
    "for vs while: when to use which?",
    "Lesson 7 exercise help",
    "Is range(1, 10) inclusive?",
    "My first program printed nothing",
    "Share your to-do list projects!",
    "Tabs or spaces?",
    "What editor do you use?",
    "Off-by-one errors everywhere",
    "Study group, Tuesdays 6 PM",
    "Why does 0.1 + 0.2 != 0.3?",
    "Tips for the reflection assignment",
    "Recursion in module 3?",
    "Welcome! Introduce yourself",
]


def password_hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 20_000).hex()


DEMO_HASH = password_hash(PASSWORD, SALT)


def _modules(course_id: int, title: str, next_lesson: list[int]) -> list[dict]:
    if course_id == 1:
        spec = PYTHON_MODULES
    elif course_id == 8:
        spec = PHOTO_MODULES
    else:
        spec = [
            ("Foundations", [(f"Welcome to {title}", 10), ("Key ideas", 15), ("First practice", 20)]),
            ("Going further", [("Worked examples", 20), ("Common mistakes", 15), ("Wrap-up", 10)]),
        ]
    modules = []
    for mtitle, lessons in spec:
        items = []
        for ltitle, minutes in lessons:
            lid = next_lesson[0]
            next_lesson[0] += 1
            body = (
                f"{ltitle}. In this lesson you'll work through the idea step by step, then try it yourself. "
                "Read the explanation, follow the example and finish with the short exercise at the end. "
                "Take notes as you go: they're saved with your progress."
            )
            items.append({"id": lid, "title": ltitle, "minutes": minutes, "body": body})
        modules.append({"title": mtitle, "lessons": items})
    return modules


def world(now: float) -> dict:
    """A fresh copy of everything one visitor can see and change."""

    def at(days: float) -> int:
        return int(now + days * DAY)

    next_lesson = [101]
    courses = []
    for cid, title, topic, level, seats, enrolled, prereq, rating, reviews, instructor, summary in COURSES:
        courses.append(
            {
                "id": cid,
                "title": title,
                "topic": topic,
                "level": level,
                "seats": seats,
                "enrolled": enrolled,
                "prereq": prereq,
                "rating": rating,
                "reviews": reviews,
                "instructor": instructor,
                "summary": summary,
                "published": at(-400 + cid * 25),
                "modules": _modules(cid, title, next_lesson),
            }
        )
    python = courses[0]["modules"]
    photo = courses[7]["modules"]
    py_lessons = [lesson["id"] for m in python for lesson in m["lessons"]]
    photo_lessons = [lesson["id"] for m in photo for lesson in m["lessons"]]

    quizzes = [
        {"id": 1, "course": 1, "title": "Quiz 1: Variables and types", "questions": [], "max_attempts": 2,
         "minutes": 10, "points": 10},
        {"id": 2, "course": 1, "title": "Quiz 2: Control flow", "questions": QUIZ_2, "max_attempts": 2,
         "minutes": 10, "points": 9},
        {"id": 3, "course": 1, "title": "Quiz 3: Practice on syntax", "questions": [], "max_attempts": 2,
         "minutes": 10, "points": 10},
    ]  # fmt: skip
    attempts = [
        {"id": 1, "quiz": 1, "user": 1, "score": 6, "total": 10, "started": at(-12), "finished": at(-12)},
        {"id": 2, "quiz": 3, "user": 1, "score": 9, "total": 10, "started": at(-6), "finished": at(-6)},
    ]
    assignments = [
        {"id": 1, "course": 1, "title": "Temperature converter", "points": 10, "due": at(-10), "min_words": 0,
         "brief": "Write a program that converts Celsius to Fahrenheit and back. Upload your .py or .txt file."},
        {"id": 2, "course": 1, "title": "Shopping list program", "points": 10, "due": at(-2), "min_words": 0,
         "brief": "Build a shopping list that can add, remove and print items. Upload your file."},
        {"id": 3, "course": 1, "title": "Final reflection", "points": 20, "due": at(5), "min_words": 150,
         "brief": "In at least 150 words, reflect on what you learned and what you'd build next."},
    ]  # fmt: skip
    students = [{"id": 1, "name": "Sara Lindqvist"}] + [{"id": 10 + i, "name": n} for i, n in enumerate(CLASSMATES)]
    submissions = [
        {"id": 1, "assignment": 1, "user": 1, "submitted": at(-3), "file": "converter.py", "size": 1840,
         "text": "", "score": 8, "released": True},
        {"id": 2, "assignment": 2, "user": 1, "submitted": at(-3), "file": "shopping.py", "size": 2210,
         "text": "", "score": None, "released": False},
    ]  # fmt: skip
    for i, s in enumerate(students[1:5]):
        submissions.append(
            {"id": 3 + i, "assignment": 2, "user": s["id"], "submitted": at(-2.5 + i * 0.1), "file": "list.py",
             "size": 1500 + i * 120, "text": "", "score": None, "released": False}
        )  # fmt: skip
    threads = []
    for i, title in enumerate(FORUM_TITLES):
        author = students[(i * 3) % len(students)]["name"]
        replies = [
            {"id": 1000 + i * 10 + r, "author": students[(i + r + 1) % len(students)]["name"],
             "body": f"Reply {r + 1}: here's what worked for me.", "created": at(-20 + i + r * 0.1), "likes": r}
            for r in range(i % 4)
        ]  # fmt: skip
        threads.append(
            {"id": i + 1, "course": 1, "title": title, "author": author, "created": at(-30 + i * 2),
             "body": f"{title} Any advice welcome!", "likes": (i * 7) % 5, "replies": replies,
             "reply_count": len(replies)}
        )  # fmt: skip
    threads.sort(key=lambda t: -t["created"])
    return {
        "courses": courses,
        "users": [{**u, "salt": SALT.hex(), "hash": DEMO_HASH} for u in USERS],
        "students": students,
        "enrollments": {
            1: {1: {"since": at(-30), "done": py_lessons[:7], "last": py_lessons[6], "notes": {}}},
            8: {
                1: {
                    "since": at(-40),
                    "done": list(photo_lessons),
                    "last": photo_lessons[-1],
                    "notes": {},
                    "finished": at(-5),
                }
            },
        },
        "quizzes": quizzes,
        "attempts": attempts,
        "assignments": assignments,
        "submissions": submissions,
        "threads": threads,
        "next_id": 5000,
    }
