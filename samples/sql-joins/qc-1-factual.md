# QC 1: research and factual accuracy
Lesson: SQL Joins (v3), generated 2026-11-07 14:35

- claims checked: 15 (supported 15, partial 0, unsupported 0, contradicted 0); accuracy 100%
- verifier quotes found verbatim in sources: 15/15
- code examples run: 1/1 print what the lesson claims
- live http probes: 0/0 confirmed
- copied passages (12+ words): 0
- sources cited: 9 (0 tier A)

## Claims

| verdict | claim | evidence |
|---|---|---|
| supported | An INNER JOIN combines rows from two or more tables based on a shared column. | S6: "A PostgreSQL JOIN combines rows from two or more tables based on a related column." |
| supported | An INNER JOIN operation finds the strict mathematical intersection of both datasets. | S13: "Strict intersection of both datasets." |
| supported | An INNER JOIN returns only the rows where matching values exist in both tables based on a common key. | S5: "INNER JOIN is used to retrieve rows where matching values exist in both tables." |
| supported | Records with no corresponding match in the other table are excluded from INNER JOIN results. | S10: "If no match exists, the row is excluded from the result set." |
| supported | SQL specifies table joins in the FROM clause. | S1: "The join condition of an inner join can be written either in the WHERE clause or in the JOIN clause." |
| supported | SQL join syntax lists the first table, declares INNER JOIN with the second table, and uses an ON clause for matching criteria. | S12: "The first joined table is referenced in the FROM clause, then the LEFT JOIN is added, followed by the second table you want to join. The tab" |
| supported | A LEFT JOIN returns all rows from the left table paired with matching rows from the right table. | S6: "LEFT JOIN returns all rows from the left table and matching rows from the right table." |
| supported | When a left table row lacks a match in a LEFT JOIN, missing right-table columns are filled with NULL values. | S11: "When a left-table row has no match on the right, the query still keeps it — and fills every right-table column with NULL instead of dropping" |
| supported | An INNER JOIN drops the entire row if a foreign key is broken or missing on either side. | S8: "a NULL value in any one of the foreign keys can result in the entire row being eliminated from the result set, with no indication of error." |
| supported | Filtering a right-table column for a non-null value in the WHERE clause turns a LEFT JOIN into an INNER JOIN by excluding padded NULL values. | S11: "Placing a condition on a right-table column in WHERE looks harmless, but NULL fails almost every comparison, so it quietly strips out the un" |
| supported | A LEFT JOIN only guarantees that all rows from the left table are kept. | S11: "A LEFT JOIN changes that rule: it guarantees every row from the left table appears in the result at least once." |
| supported | Unmatched rows from the right table are excluded in a LEFT JOIN unless a FULL JOIN is used. | S12: "- RIGHT JOIN – Returns all the data from the right table and only the matching rows from the left table. The non-matching rows’ values will " |
| supported | The WHERE clause executes after the join is built. | S11: "- WHERE — filters are applied to the joined result, including those NULL-padded rows." |
| supported | An INNER JOIN returns strictly intersecting records and drops unmatched rows. | S13: "/ INNER JOIN / Strict intersection of both datasets. / Completely Excluded. / Completely Excluded. /" |
| supported | A LEFT JOIN retains every record from the left table and places NULL where matches are absent. | S11: "A LEFT JOIN (also written LEFT OUTER JOIN) returns every row from the "left" table in your query, plus the matching row(s) from the "right" " |

## Code execution

- s5 (python): **pass** - output matches the lesson

## Sources

| id | tier | cited | source |
|---|---|---|---|
| S1 | A | 0 | [7.2. Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html) |
| S2 | A | 0 | [Sams teach yourself SQL in 10 minutes](https://openlibrary.org/works/OL64832W) |
| S3 | B | 9 | [SQL LEFT JOIN - GeeksforGeeks](https://www.geeksforgeeks.org/sql/sql-left-join/) |
| S4 | B | 8 | [SQL Inner Join - GeeksforGeeks](https://www.geeksforgeeks.org/sql/sql-inner-join/) |
| S5 | B | 6 | [SQL Joins (Inner, Left, Right and Full Join) - GeeksforGeeks](https://www.geeksforgeeks.org/sql/sql-join-set-1-inner-left-right-and-full-joins/) |
| S6 | B | 1 | [PostgreSQL - Joins - GeeksforGeeks](https://www.geeksforgeeks.org/postgresql/postgresql-joins/) |
| S7 | B | 0 | [SQL LEFT JOIN | Programiz](https://www.programiz.com/sql/left-join) |
| S8 | B | 0 | [Join (SQL) - Wikipedia](https://en.wikipedia.org/wiki/Join_(SQL)) |
| S9 | C | 4 | [Inner Join](https://www.sqltutorial.net/inner-join.html) |
| S10 | C | 3 | [When to Use LEFT JOIN vs INNER JOIN in SQL: Key Differences, Use Cases](https://www.tutorialpedia.org/blog/when-to-use-left-join-and-when-to-use-inner-join/) |
| S11 | C | 7 | [SQL LEFT JOIN Explained With Examples](https://learn.programmingline.com/learn/sql/sql-left-join) |
| S12 | C | 2 | [9 Practical Examples of SQL LEFT JOIN](https://learnsql.com/blog/left-join-examples/) |
| S13 | C | 4 | [SQL INNER JOIN Tutorial - SQL Server Guides](https://sqlserverguides.com/sql-inner-join-tutorial/) |
| S14 | C | 0 | [PostgreSQL Joins: A Visual Explanation of PostgreSQL Joins](https://neon.com/postgresql/tutorial/joins) |

## Findings

### F1 [high] unknown citation (open)
where: s2; found by: check

cites [S15], which is not one of the research sources

suggested fix: replace [S15] with a real source id or remove the claim

### F2 [medium] uncited section (open)
where: s5; found by: check

only 0 of 5 sentences carry a citation in a example section

suggested fix: add source ids to the factual sentences, or move unsupported material out

### F3 [medium] no primary source (open)
where: whole lesson; found by: check

the lesson does not cite a single tier A (primary) source

suggested fix: cite the specification or official documentation for the core definitions

