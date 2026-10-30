# Fernhill Academy: answer key (40 planted bugs)

Fernhill Academy is an online-learning site (course catalog, lesson player, timed quizzes, assignments, gradebook,
certificates, a discussion forum and an instructor's grading page) with **functional bugs planted on purpose**, for
checking what the AI QA Scanner finds. Most bugs break a published grading rule, so finding them takes the rules,
some arithmetic, a second page or a second account.

This file is never served, and nothing the site serves (pages, scripts, CSS, images) names or hints at a bug.
Server-side code marks each one with a `BUG-nn` comment; `tests/test_fernhill.py` keeps the server-side ones in
place. The rules every bug breaks are published on the site's **How grading works** page (`/help`).

## Run it

- **Locally**: `python -m fernhill` (port 8083, or `PORT`), then open http://localhost:8083.
- **Railway**: New service → GitHub repo → this repository, then **Generate domain**. `railway.json` sets the start
  command and health check; no variables or volume needed.

Every visitor (cookie) gets a private copy of the demo world, dated around today, so parallel scans never see each
other's changes and a new browser session starts from the original data. Logging in as the student and then the
instructor in the same browser shares one world, so a grade Ian enters is what Sara sees. A restart resets everything.

## Test data

Days below are counted from the day the session starts ("day 0" is today).

| What | Value |
|---|---|
| Accounts (password `Fernhill@2026`, listed on the login page) | `sara@fernhill.test` student · `ian@fernhill.test` instructor of Python Basics, Data Analysis with Python, Machine Learning Foundations and SQL for Analysts |
| Courses | 13. Python Basics: 3 modules × 4 lessons, 225 minutes. UX Design Fundamentals is full (30 of 30). Data Analysis with Python requires Python Basics. Accented titles: "Español para viajeros", "Café Culture: French for Beginners" |
| Python Basics lessons | Getting started: Why Python?, Installing Python, Your first program, Variables and types · Control flow: Comparisons, If statements, While loops, For loops · Functions and lists: Defining functions, Parameters and return, Lists, Project: to-do list |
| Sara in Python Basics | Enrolled day −30; first 7 lessons done (58%); last opened "While loops" |
| Sara in Digital Photography | All 6 lessons done; enrolled day −40, finished day −5 |
| Quizzes (Python Basics) | Quiz 1 (closed, Sara 6/10) · Quiz 2 "Control flow" (open: 9 questions, 10 minutes, 2 attempts) · Quiz 3 (closed, Sara 9/10) |
| Assignments (Python Basics) | Temperature converter, 10 points, due day −10; Sara submitted day −3, scored 8, released · Shopping list program, 10 points, due day −2; Sara and 4 classmates submitted, not graded · Final reflection, 20 points, due day +5, at least 150 words |
| Forum (Python Basics) | 14 threads, 5 a page, newest first. Sara wrote "How do I install Python on a Chromebook?" (thread 1) and "Tips for the reflection assignment"; "Recursion in module 3?" has no replies |
| Classmates | 10, including "Pat O'Neill, Jr." (a comma in the name) and "Tomás García" |

Difficulty: **Medium** needs a flow or a comparison; **Hard** needs the published rules, a second page, a reload,
a role switch or an edge-case value; **Expert** needs arithmetic across several numbers, a race, a reload mid-quiz
or a downloaded file.

## The bugs

### Catalog

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-01 | Search doesn't ignore accents | Search "espanol" or "cafe" (the box suggests "español, café") | Español para viajeros / Café Culture | "No courses match" | Medium | Medium | `server.py` `Store.catalog` |
| BUG-02 | Load more repeats a course | Home page, Load more courses | 13 different courses | "Data Analysis with Python" appears twice (the page asks for more from the 6th card, but the server sends 6 a page) | Medium | Medium | `static/catalog.js` `more` |
| BUG-03 | Load more drops the filters | Level "Beginner" (9 courses), Load more | Only Beginner courses | Intermediate and Advanced courses appear | Medium | Hard | `static/catalog.js` `more` |
| BUG-04 | Course length is wrong | Python Basics card or course page: "4h 45m" | 3h 45m (225 minutes of lessons) | 4h 45m: hours are rounded instead of floored (any length with 30+ spare minutes) | Low | Hard | `static/core.js` `F.duration` |

### Course page

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-05 | A full course still takes students | As Sara, UX Design Fundamentals ("Course full (30 of 30)"), Enroll | Enrolling refused | "You're enrolled"; "31 of 30 seats taken" | High | Medium | `server.py` `Store.enroll` |
| BUG-06 | Prerequisite not enforced | As Sara, Data Analysis with Python ("Requires Python Basics… Not completed yet"), Enroll | Enrolling refused | Enrolled | High | Medium | `server.py` `Store.enroll` |
| BUG-07 | Syllabus leaves out the first lesson | Python Basics syllabus | 12 lessons from "Why Python?" | "12 lessons" above a list of 11; "Why Python?" missing | Medium | Hard | `static/course.js` (loop starts at 1) |

### Lessons

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-08 | Next skips the first lesson of a module | Lesson "Variables and types" (last of module 1), Next lesson | Comparisons | If statements; Comparisons is skipped (same from module 2 to 3) | Medium | Medium | `static/learn.js` `neighbour` |
| BUG-09 | Progress counts a lesson twice | Open a lesson already done (e.g. "Why Python?", 58%), press Next | Still 58% (7 of 12) | 67% with 7 lessons ticked; repeat and progress passes 100% | High | Hard | `server.py` `Store.mark` |
| BUG-10 | Notes typed just before moving on are lost | On a lesson, type a note and press Next within a second; go back | The note is there | Empty: the delayed save writes the next lesson's (empty) notes to it | High | Expert | `static/learn.js` notes `input` handler |
| BUG-11 | Back leaves the course | Course page → a lesson → Next, Next → browser Back | The previous lesson | The course page: lessons replace the history entry | Medium | Hard | `static/learn.js` `open` (`replaceState`) |
| BUG-12 | Arrow keys change lesson while typing notes | Type in "Your notes", press ← or → to move the cursor | The cursor moves | The page goes to the previous / next lesson (and → marks the lesson complete) | Low | Hard | `static/learn.js` `keydown` |

### Quizzes

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-13 | Reloading resets the time limit | Quiz 2, Start; wait; reload; Start | The clock keeps running (or the attempt resumes) | A fresh 10:00; the abandoned attempt doesn't count and the server never checks the time | High | Expert | `static/quiz.js` timer, `server.py` `Store.submit` |
| BUG-14 | "Select all that apply" accepts a partial answer | Q2 (comparison operators): tick only `==` | Wrong (needs `==`, `!=`, `>=`) | Marked right: one right pick is enough | High | Hard | `server.py` `Store.right` |
| BUG-15 | "3.0" is not accepted for 3 | Q3: answer `3.0` | Right (help: "3, 3.0") | Wrong | High | Hard | `server.py` `Store.right` |
| BUG-16 | Text answers are case and space sensitive | Q4: answer `Def` or `def ` | Right | Wrong | High | Hard | `server.py` `Store.right` |
| BUG-17 | Percentages are truncated | Score 6 / 9 | 67% | 66% (floored; help says rounded) | Medium | Hard | `static/quiz.js` `finish` |
| BUG-18 | A third attempt is allowed | Finish Quiz 2 twice, open it again | "You've used all your attempts", no Start | Start is shown and a third attempt runs | High | Medium | `server.py` `Store.start`, `static/quiz.js` |
| BUG-19 | The last attempt counts, not the best | Score 6/9, then 2/9; Grades | Quiz 2: 6 / 9 | 2 / 9 | High | Hard | `server.py` `Store.gradebook` |
| BUG-20 | Flags vanish when you use the question list | Flag question 3, click another number in the question list | Question 3 stays flagged | All flags cleared (Next / Previous keep them) | Low | Medium | `static/quiz.js` `#qnav` click |
| BUG-21 | Skipped questions aren't counted as unanswered | Answer Q1, jump to Q9 with the list, answer, Submit quiz | "You have 7 unanswered questions" | "You have answered every question" | Medium | Hard | `static/quiz.js` submit (sparse array) |
| BUG-22 | Review shows your wrong pick as the correct answer | Answer a single-choice question wrongly, submit | Correct answer: the right option | "Correct answer:" repeats your wrong option | Medium | Medium | `static/quiz.js` `finish` |

### Assignments

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-23 | Upper-case file extensions are refused | Temperature converter: attach `converter.PY` or `Report.PDF` | Accepted | "Upload a PDF, TXT, DOCX or PY file." | Medium | Hard | `static/assignment.js` `TYPES` |
| BUG-24 | Resubmitting wipes the grade | Temperature converter (graded 8), resubmit a file | Grade stays until regraded (help) | "Waiting for a grade"; the gradebook drops it | High | Medium | `server.py` `Store.hand_in` |
| BUG-25 | Late penalty isn't capped at 50% | Temperature converter: 8/10, 7 days late | 4 / 10 (50% cap) | 2.4 / 10 (70% off) | High | Expert | `server.py` `Store.graded` |
| BUG-26 | Word count ignores line breaks | Final reflection: 160 words on 16 lines | "160 words", submits | "145 words (at least 150)", "Write at least 150 words." (double spaces count extra) | Medium | Hard | `static/assignment.js` `words` |

### Gradebook

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-27 | Weights are ignored | Grades, Python Basics (fresh session) | 60%: quizzes 90 × 40% + assignments 40 × 60% | 28%: a plain average of the rows | Critical | Expert | `server.py` `Store.gradebook` |
| BUG-28 | The highest quiz is dropped | Grades | Quiz 1 (60%) dropped | Quiz 3 (90%) dropped | High | Medium | `server.py` `Store.gradebook` |
| BUG-29 | Ungraded work counts as zero | Grades: Shopping list program "Submitted, not graded yet" | Not counted | 0% and counted | High | Hard | `server.py` `Store.gradebook` |

### Certificates

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-30 | Certificate before finishing, with a failing grade | Mark lessons 8 to 11 of Python Basics complete (11 of 12, 92%), open Certificate | "Not quite yet" (needs every lesson and 70%; grade is 28%) | Certificate issued | Critical | Hard | `server.py` `Store.certificate` |
| BUG-31 | Certificate shows the enrolment date | Digital Photography certificate | Completed (day −5) | Completed (day −40, the enrolment date) | Medium | Hard | `server.py` `Store.certificate` |

### Discussion

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-32 | Page 2 repeats a thread | Discussion, Older | Threads 6 to 10 | Starts with the last thread of page 1 | Medium | Medium | `server.py` `Store.forum` |
| BUG-33 | Unlimited likes | Like a post twice | One like per person (help) | Each click adds one | Medium | Medium | `server.py` `Store.like` |
| BUG-34 | Reply counts don't update | Reply to "Recursion in module 3?", back to the list | 1 reply | "0 replies" (the thread says 1) | Low | Hard | `server.py` `Store.reply` |
| BUG-35 | Editing skips the 1,000-character limit | Edit your own post (thread 1) to 1,500 characters | Refused (posts and replies refuse 1,001) | Saved | Medium | Hard | `server.py` `Store.edit`, `static/thread.js` (no `maxlength`) |

### Dashboard

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-36 | "Continue where you left off" starts over | My learning, Python Basics, Continue where you left off | While loops (last opened) | Why Python? (lesson 1); the course page's "Go to course" is right | Medium | Medium | `static/dashboard.js` (`c.first`) |

### Instructor

| ID | Bug | Steps to reproduce | Expected | Actual | Severity | Difficulty | Where |
|---|---|---|---|---|---|---|---|
| BUG-37 | Half points are cut off | As Ian, Shopping list program, score 9.5 for Sara, Save | 9.5 | "Saved 9."; 9 stored | High | Hard | `static/teach.js` (`parseInt`) |
| BUG-38 | Roster CSV breaks on commas in names | Download roster (CSV) for Python Basics, open in a spreadsheet | 3 columns | "Pat O'Neill, Jr." splits into 4 columns, shifting the email and progress | Medium | Expert | `server.py` `Store.roster_csv` |
| BUG-39 | Releasing grades gives ungraded work 0 | Grade one Shopping list submission, Release grades | Refused until every submission is graded (help) | Every ungraded submission becomes 0 and is released | Critical | Hard | `server.py` `Store.release` |
| BUG-40 | Scores above the maximum are accepted | Score 15 on a 10-point assignment | Refused | "Saved 15."; Sara sees 15 / 10 | High | Medium | `server.py` `Store.grade` |

## What is not a planted bug

- Quiz 1 and Quiz 3 are closed (listed without a link); their scores are seed data. `/quiz?id=1` says "We couldn't
  find that quiz".
- Console errors that come with a page: 403 on student pages as Ian (and `/teach` as Sara), 404 on unknown pages.
- Bugs that combine: BUG-25, BUG-28 and BUG-29 also move the overall grade of BUG-27; the expected 60% applies
  every rule. BUG-09 can push progress over 100%.
- Each visitor has a private world: changes in one browser session do not show in another.
- "Demo learning site for QA testing" in the footer and the demo accounts on the login page.

By area: catalog 4, course page 3, lessons 5, quizzes 10, assignments 4, gradebook 3, certificates 2, discussion 4,
dashboard 1, instructor 4.
By difficulty: Medium 14, Hard 21, Expert 5. By severity: Critical 3, High 16, Medium 17, Low 4.
