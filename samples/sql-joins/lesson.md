# SQL Joins

**Learning objective:** Write INNER and LEFT JOIN queries and predict which rows each returns when matching rows are missing.

*Time: 47 minutes. Audience: first-year computer science undergraduates*

## The Missing Data Mystery
*3 min*

Imagine you manage a university database. One table holds student records, while another records course enrollments. When you want to see who is enrolled in what, some students seem to vanish from your reports entirely because they haven't picked a class yet, while courses without students disappear too. If you only look at one table at a time, you miss the full picture. Relational databases store data across separate, normalized tables to reduce redundancy, but to answer real questions, you need a way to stitch those tables back together based on related columns.

Quick check: before reading on, write down which rows you think a LEFT JOIN keeps.

## Combining Tables with INNER JOIN
*6 min*

To combine rows from two or more tables based on a shared column, you use an INNER JOIN [S4]. This operation finds the strict mathematical intersection of both datasets [S13]. It looks at a common key—such as a student ID or department ID—and returns only the rows where matching values exist in both tables [S5][S9][S15]. If a record exists in one table but has no corresponding match in the other, it is completely filtered out and excluded from your results [S4][S10].

In SQL, you specify this in your `FROM` clause [Yh4CrPHVBdE]. The syntax lists the first table, declares the `INNER JOIN` keyword alongside the second table, and uses an `ON` clause to define the matching criteria [S4][S9]. Because inner joins only output strict matches, they are highly efficient for querying tightly linked relationships, such as valid sales tied to existing products [S10][S13].

## Preserving Records with LEFT JOIN
*6 min*

An inner join discards unmatched rows, but what if you need to keep every single record from your primary table regardless of whether a match exists elsewhere [S10]? For this, you use a LEFT JOIN (also called a LEFT OUTER JOIN) [S3]. A left join returns all rows from the left table, paired with any matching rows from the right table [S3][S5]. 

When a row in the left table lacks a match in the right table, the query still retains that left-table row, filling in the missing right-table columns with `NULL` values [S3][S5][S11]. This makes left joins essential for auditing tasks, such as finding every customer including those who have never placed an order, or finding departments with zero staff [S11].

> **Watch now:** [Learn MySQL joins in 5 minutes!](https://www.youtube.com/watch?v=G3lJAxg1cy8&t=219s) by Bro Code, 3:39-5:02 (1.4 min). Demonstrates visually how left joins display everything from the table on the left while inner joins connect matching rows.

## Predicting Outcomes for Missing Matches
*6 min*

When designing queries, you must be able to predict how missing data affects your output grid. An `INNER JOIN` acts as a gatekeeper: if a foreign key is broken or missing on either side, the entire row is dropped [S4][S13]. A `LEFT JOIN` acts as an inclusive safety net for the table declared on the left side of the query, protecting its rows from deletion while padding missing right-side data with `NULL` [S3][S11].

A common pitfall occurs when placing conditions on right-table columns inside a `WHERE` clause instead of the `ON` clause [S11]. Filtering a right-table column for a non-null value in the `WHERE` clause can accidentally turn your `LEFT JOIN` back into an `INNER JOIN`, silently erasing your unmatched rows because the `WHERE` filter evaluates after the join and excludes the newly padded `NULL` values [S12].

## Working with SQL Joins
*6 min*

Consider two tables: `students` and `enrollments`. The `students` table has student IDs and names, while `enrollments` tracks student IDs and course IDs. Some students have not enrolled in any courses.

```python
# Simulating relational joins in Python standard library
students = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
    {"id": 3, "name": "Charlie"}
]

enrollments = [
    {"id": 1, "course": "CS101"},
    {"id": 2, "course": "CS102"}
]

# INNER JOIN simulation
inner_result = [
    (s["name"], e["course"])
    for s in students
    for e in enrollments
    if s["id"] == e["id"]
]
print("INNER:", inner_result)

# LEFT JOIN simulation
left_result = []
for s in students:
    match = [e["course"] for e in enrollments if e["id"] == s["id"]]
    if match:
        for c in match:
            left_result.append((s["name"], c))
    else:
        left_result.append((s["name"], None))
print("LEFT:", left_result)
```

```output
INNER: [('Alice', 'CS101'), ('Bob', 'CS102')]
LEFT: [('Alice', 'CS101'), ('Bob', 'CS102'), ('Charlie', None)]
```

Notice how Charlie has no course match. The inner join drops Charlie completely, whereas the left join retains Charlie and outputs `None` (SQL's `NULL`) for the course column.

## Common Pitfalls and Misconceptions
*4 min*

### Misconception 1: Left joins keep rows from both tables when matches are missing
Beginners often believe a `LEFT JOIN` will preserve unmatched rows from both the left and right tables [M1]. In reality, a left join only guarantees that all rows from the *left* table are kept. Unmatched rows from the *right* table are still excluded unless you use a `FULL JOIN` [S5][S12].

### Misconception 2: Putting join filters in the WHERE clause behaves the same as the ON clause
Many learners write `LEFT JOIN` queries and filter right-table attributes in the `WHERE` clause, expecting unmatched rows to remain with nulls. Because the `WHERE` clause executes after the join is built, filtering on a right-table column can inadvertently remove your `NULL` rows, transforming your outer join into an inner join [S11].

## Query Prediction and Design Exercise
*8 min*

In this hands-on task, you will analyze table schemas and predict output rows.

1. Review a mock database schema containing an `employees` table (columns: `emp_id`, `name`) and a `departments` table (columns: `dept_id`, `emp_id`, `dept_name`). Note that two employees are not assigned to any department.
2. Write an `INNER JOIN` query linking `employees` and `departments` on `emp_id`. Predict how many rows will be returned if there are 5 total employees and 3 have departments [S4][S9].
3. Rewrite the query as a `LEFT JOIN` keeping `employees` on the left side [S3][S6]. Predict what values appear for the unassigned employees' department columns [S3][S5].
4. Self-check: Confirm that your inner join returns 3 rows while your left join returns all 5 rows, with `NULL` filling the missing department fields for the unassigned workers [S3][S4].

## Lesson Summary
*2 min*

- **INNER JOIN**: Combines rows from multiple tables based on a matching condition, returning strictly the intersecting records and dropping unmatched rows [S4][S9][S13].
- **LEFT JOIN**: Retains every record from the left table, attaching matching right-table data and placing `NULL` where matches are absent [S3][S5][S11].
- **Prediction**: Missing foreign keys cause inner joins to eliminate rows entirely, whereas left joins protect left-table rows while converting missing right-side values to `NULL` [S3][S4][S11].

## Knowledge check
*5 min*

**1. Which SQL operation should you use when you want to retrieve every customer record from a customer table, alongside any matching orders from an orders table, ensuring customers without orders are still included?**

- A) CROSS JOIN
- B) FULL JOIN
- C) INNER JOIN
- D) LEFT JOIN

**2. You execute an INNER JOIN between an 'authors' table and a 'books' table on 'author_id'. One author has written no books and has no matching entry in the books table. What happens to this author in the result set?**

- A) The author is excluded entirely from the result set.
- B) The query throws a syntax error due to missing data.
- C) The author is included with NULL values for book columns.
- D) The author is duplicated for every book in the database.

**3. How do you properly construct an INNER JOIN query in SQL to combine 'employees' and 'departments' tables based on 'department_id'?**

- A) SELECT * FROM employees JOIN departments MATCH employees.department_id = departments.department_id;
- B) SELECT * FROM employees INNER JOIN departments ON employees.department_id = departments.department_id;
- C) SELECT * FROM employees, departments USING INNER JOIN department_id;
- D) SELECT * FROM employees INNER JOIN departments WHERE employees.department_id = departments.department_id;

**4. When performing a LEFT JOIN where a row in the right table has no corresponding match in the left table, what is returned for the left table's columns in that row?**

- A) Default zero values
- B) NULL values
- C) An error code
- D) The row is excluded from the result set

**5. Which of the following describes the key structural difference between an INNER JOIN and a LEFT JOIN?**

- A) INNER JOIN requires an ON clause, while LEFT JOIN operates without any matching condition.
- B) INNER JOIN returns only matching intersection records, while LEFT JOIN preserves all records from the left table regardless of matches.
- C) INNER JOIN keeps all records from both tables, while LEFT JOIN keeps only matching records.
- D) INNER JOIN only works with numerical keys, while LEFT JOIN handles text strings.

### Answers

1. **D**: A LEFT JOIN returns all rows from the left table, paired with matching rows from the right table, and fills in NULL when there is no match.
2. **A**: An INNER JOIN acts as an intersection and gatekeeper, filtering out and completely excluding any rows that lack a matching key in both tables.
3. **B**: Standard SQL syntax for an inner join lists the tables with the INNER JOIN keyword and specifies the matching condition using an ON clause.
4. **B**: A LEFT JOIN preserves all rows from the left table; when right-table matches are missing, right-table columns are filled with NULL values.
5. **B**: An INNER JOIN returns only the strict intersection of matching rows, whereas a LEFT JOIN guarantees that all rows from the left table are retained.

## References

- **[S3]** SQL LEFT JOIN - GeeksforGeeks. <https://www.geeksforgeeks.org/sql/sql-left-join/> (tier B: tutorial site (uneven quality))
- **[S4]** SQL Inner Join - GeeksforGeeks. <https://www.geeksforgeeks.org/sql/sql-inner-join/> (tier B: tutorial site (uneven quality))
- **[S5]** SQL Joins (Inner, Left, Right and Full Join) - GeeksforGeeks. <https://www.geeksforgeeks.org/sql/sql-join-set-1-inner-left-right-and-full-joins/> (tier B: tutorial site (uneven quality))
- **[S6]** PostgreSQL - Joins - GeeksforGeeks. <https://www.geeksforgeeks.org/postgresql/postgresql-joins/> (tier B: tutorial site (uneven quality))
- **[S9]** Inner Join. <https://www.sqltutorial.net/inner-join.html> (tier C: unclassified site)
- **[S10]** When to Use LEFT JOIN vs INNER JOIN in SQL: Key Differences, Use Cases & Practical Examples. <https://www.tutorialpedia.org/blog/when-to-use-left-join-and-when-to-use-inner-join/> (tier C: unclassified site)
- **[S11]** SQL LEFT JOIN Explained With Examples. <https://learn.programmingline.com/learn/sql/sql-left-join> (tier C: unclassified site)
- **[S12]** 9 Practical Examples of SQL LEFT JOIN. <https://learnsql.com/blog/left-join-examples/> (tier C: unclassified site)
- **[S13]** SQL INNER JOIN Tutorial - SQL Server Guides. <https://sqlserverguides.com/sql-inner-join-tutorial/> (tier C: unclassified site)

**Learner questions referenced**

- **[M1]** How to join (merge) data frames (inner, outer, left, right) <https://stackoverflow.com/questions/1299871/how-to-join-merge-data-frames-inner-outer-left-right>

**Videos**

- Learn MySQL joins in 5 minutes! by Bro Code <https://www.youtube.com/watch?v=G3lJAxg1cy8&t=219s> (3:39-5:02)

**Further reading**

- Sams teach yourself SQL in 10 minutes, Ben Forta (1999) <https://openlibrary.org/works/OL64832W>
