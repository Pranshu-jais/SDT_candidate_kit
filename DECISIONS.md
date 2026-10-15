# DECISIONS.md  (about 150-200 words in total - plain language, your own words)

1. **Indexes.** We created a unique compound index on `attendance_logs` (`emp_code`, `date`) to enforce one record per employee per day and guarantee race safety[cite: 3]. We also added indexes on `employees.emp_code` (unique)[cite: 3], `employees.department`, and `attendance_logs.date` to support fast filtering, sorting, and aggregation across ~100k records[cite: 3]. We considered indexing derived fields like `late_minutes`, but rejected it since analytical scans cover these adequately without write-amplification overhead.

2. **Punch-in race.** When two identical punch-in requests arrive simultaneously for the same employee and date, the database's unique compound index (`emp_code`, `date`) intercepts them[cite: 3]. The first transaction successfully inserts the document, while the second triggers a `DuplicateKeyError`. Our code catches this exception and immediately returns a `409 Conflict`, ensuring zero duplicate logs[cite: 3].

3. **Ties.** The late-comer leaderboard uses MongoDB's `$denseRank` window function[cite: 3]. If employees tie at the cutoff limit, all tied rows are returned (meaning items > limit can appear), sharing standard competition ranks (e.g., 1, 2, 2, 4)[cite: 3]. Tied rows are sorted by `total_late_minutes` descending, then `emp_code` ascending[cite: 3].

4. **Headcount.** The department summary pipeline starts from the `employees` collection filtered by `joined_on` <= month-end, ensuring employees with zero attendance logs are accurately counted per rule R9[cite: 1, 3]. It then left-joins `attendance_logs`[cite: 3].

5. **100x Data Scale.** To serve 100x the data, we would introduce pre-aggregated monthly summary collection tables or materialized views updated via background worker streams rather than computing complex cross-collection joins and time-series pipelines on the fly.



