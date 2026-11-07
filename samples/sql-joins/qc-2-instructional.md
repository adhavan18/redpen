# QC 2: instructional quality
Lesson: SQL Joins (v3), generated 2026-11-07 14:35

- planned time: 47 minutes
- rubric average: 4.0/5
- simulated classroom: 85% correct before the lesson, 80% after (gain -5 points)

## Objective alignment

| objective part | taught | practised | assessed | coverage |
|---|---|---|---|---|
| Write INNER JOIN queries to combine rows from multiple tables based on a matching condition. | [1] | [6] | [2] | full |
| Write LEFT JOIN queries to include all records from the left table alongside matching right table records. | [2] | [6] | [0] | full |
| Predict which rows each JOIN type returns when matching rows are missing. | [0, 3, 5] | [6] | [1, 3, 4] | full |

## Rubric

- objective_alignment: 5/5 - The lesson strictly addresses writing inner/left joins and predicting output rows for missing data.
- clarity: 4/5 - Generally clear explanations, though terms like normalized tables and mathematical intersection cause minor friction for novices.
- structure: 4/5 - Logical flow from hook to concepts, code examples, misconceptions, and guided practice.
- examples: 4/5 - Python-based list comprehensions effectively simulate relational join outputs for students.
- practical_application: 4/5 - Section 6 provides a solid schema analysis and prediction task for hands-on application.
- assessment_quality: 3/5 - Question 3 performed poorly with students after reading, indicating a confusing phrasing issue regarding left vs right tables.
- pacing: 4/5 - Estimated at 47 minutes against a 45-minute target, which is close enough to be considered on track.
- engagement: 4/5 - Good use of a university enrollment mystery hook and Python simulations to keep learners engaged.

## Item analysis (simulated classroom)

| q | correct before | correct after | discrimination | picks per option |
|---|---|---|---|---|
| Q1 | 0.75 | 1.0 | 0.0 | [0, 0, 1, 7] |
| Q2 | 1.0 | 1.0 | 0.0 | [8, 0, 0, 0] |
| Q3 | 1.0 | 1.0 | 0.0 | [0, 8, 0, 0] |
| Q4 | 0.75 | 0.0 | 0.0 | [0, 3, 0, 5] |
| Q5 | 0.75 | 1.0 | 0.0 | [0, 7, 1, 0] |

## Run sheet

-  0- 3 min: The Missing Data Mystery
-  3- 9 min: Combining Tables with INNER JOIN
-  9-15 min: Preserving Records with LEFT JOIN
- 15-16 min: video: Learn MySQL joins in 5 minutes!
- 16-22 min: Predicting Outcomes for Missing Matches
- 22-28 min: Working with SQL Joins
- 28-32 min: Common Pitfalls and Misconceptions
- 32-40 min: Query Prediction and Design Exercise
- 40-42 min: Lesson Summary
- 42-47 min: knowledge check

## Findings

### I1 [high] over time (open)
where: whole lesson; found by: check

planned time is 47 minutes, over the 45-minute limit

suggested fix: cut or shorten the lowest-value section; do not cut the activity or the check

### I10 [high] students still miss it (open)
where: quiz; found by: simulated

Q4: only 0% of simulated students answer correctly after reading the lesson. Most picked option 3: "The row is excluded from the result set". Either the explanation does not cover it or the answer key is wrong.

evidence: When performing a LEFT JOIN where a row in the right table has no corresponding match in the left table, what is returned for the left table's columns in that row?

suggested fix: check the answer key, then strengthen the section that teaches this

### I17 [high] assessment (open)
where: quiz; found by: llm

Question 3 has a reverse confusion where students failed post-reading, likely because the question stem asks about a right table row missing a match in the left table during a LEFT JOIN, which confounds the left-join premise.

evidence: When performing a LEFT JOIN where a row in the right table has no corresponding match in the left table, what is returned for the left table's columns in that row?

suggested fix: Reword Question 3 to focus on the standard behavior of missing right table matches from the perspective of the left table being preserved.

### I15 [medium] confusing passage (open)
where: s4; found by: simulated

3 simulated student(s) got stuck here

evidence: Ravi (struggling): "Filtering a right-table column for a non-null value in the WHERE clause can accidentally turn your LEFT JOIN back into a" - This part is way too complicated with too many big words, and I got totally mixed up about whether WHERE or ON is supposed to be used. / Meera (average): "Filtering a right-table column for a non-null value in the WHERE clause can accidentally turn your LEFT JOIN back into a" - This part is a bit heavy and confusing about why a WHERE clause suddenly changes the whole join type when I just wanted to filter something. / Karthik (strong): "When performing a LEFT JOIN where a row in the right table has no corresponding match in the left table, what is returne" - This is a trick question or a conceptual confusion because a left join by definition always preserves the left table, so rows in the left table are never missing when matched against the right table; rather, it is the right table rows that are missing.

suggested fix: define the term or add the missing step where they got stuck

### I16 [medium] clarity (open)
where: s2; found by: llm

Novice learners struggle with jargon like normalized tables and mathematical intersection without prior context.

evidence: Relational databases store data across separate, normalized tables to reduce redundancy... This operation finds the strict mathematical intersection of both datasets

suggested fix: Add a brief inline definition clarifying that normalized means split into logical categories to avoid repeating data.

### I2 [low] pacing (open)
where: s2; found by: check

"Combining Tables with INNER JOIN" is about 0.8 min of reading for a 6-minute slot

suggested fix: add an example or a check-your-understanding prompt

### I3 [low] pacing (open)
where: s3; found by: check

"Preserving Records with LEFT JOIN" is about 0.7 min of reading for a 6-minute slot

suggested fix: add an example or a check-your-understanding prompt

### I4 [low] pacing (open)
where: s4; found by: check

"Predicting Outcomes for Missing Matches" is about 0.8 min of reading for a 6-minute slot

suggested fix: add an example or a check-your-understanding prompt

### I5 [low] dead distractors (open)
where: quiz; found by: simulated

Q1: nobody in the simulated classroom picked "CROSS JOIN", "FULL JOIN"

suggested fix: replace them with options built on a real misconception

### I6 [low] no learning signal (open)
where: quiz; found by: simulated

Q2: every simulated student answers correctly before reading the lesson

evidence: You execute an INNER JOIN between an 'authors' table and a 'books' table on 'author_id'. One author has written no books and has no matching entry in the books table. What happens to this author in the result set?

suggested fix: make it an application question with a new scenario, so it measures what the lesson taught

### I7 [low] dead distractors (open)
where: quiz; found by: simulated

Q2: nobody in the simulated classroom picked "The query throws a syntax error due to missing data.", "The author is included with NULL values for book columns.", "The author is duplicated for every book in the database."

suggested fix: replace them with options built on a real misconception

### I8 [low] no learning signal (open)
where: quiz; found by: simulated

Q3: every simulated student answers correctly before reading the lesson

evidence: How do you properly construct an INNER JOIN query in SQL to combine 'employees' and 'departments' tables based on 'department_id'?

suggested fix: make it an application question with a new scenario, so it measures what the lesson taught

### I9 [low] dead distractors (open)
where: quiz; found by: simulated

Q3: nobody in the simulated classroom picked "SELECT * FROM employees JOIN departments MATCH employees.department_id = departments.department_id;", "SELECT * FROM employees, departments USING INNER JOIN department_id;", "SELECT * FROM employees INNER JOIN departments WHERE employees.department_id = departments.department_id;"

suggested fix: replace them with options built on a real misconception

### I11 [low] dead distractors (open)
where: quiz; found by: simulated

Q4: nobody in the simulated classroom picked "Default zero values", "An error code"

suggested fix: replace them with options built on a real misconception

### I12 [low] dead distractors (open)
where: quiz; found by: simulated

Q5: nobody in the simulated classroom picked "INNER JOIN requires an ON clause, while LEFT JOIN operates without any matching condition.", "INNER JOIN only works with numerical keys, while LEFT JOIN handles text strings."

suggested fix: replace them with options built on a real misconception

### I13 [low] confusing passage (open)
where: s1; found by: simulated

1 simulated student(s) got stuck here

evidence: Asha (novice): "Relational databases store data across separate, normalized tables to reduce redundancy" - I have no idea what normalized tables or redundancy mean since they aren't explained anywhere.

suggested fix: define the term or add the missing step where they got stuck

### I14 [low] confusing passage (open)
where: s2; found by: simulated

1 simulated student(s) got stuck here

evidence: Asha (novice): "This operation finds the strict mathematical intersection of both datasets" - Taking this literally, I started thinking about math class geometry instead of tables.

suggested fix: define the term or add the missing step where they got stuck

