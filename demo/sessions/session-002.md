---
title: Slow Postgres queries
date: 2026-09-18
tags: [database, performance]
---

**User:** Our Postgres queries are getting slow in production. The dashboard page takes 8 seconds to load. Where do I start?

**Assistant:** Start with `pg_stat_statements` to find the slowest queries by total time. Then run EXPLAIN ANALYZE on the top offenders. Nine times out of ten it's a missing index on a foreign key or a WHERE clause.

**User:** Found it — one query does a sequential scan over 2M rows. It filters on `created_at` but there's no index.

**Assistant:** Add a btree index on `created_at`. But first check the query pattern: if it always filters by a date range plus a status, a composite index on `(status, created_at)` will serve both. Create it concurrently so you don't lock the table: `CREATE INDEX CONCURRENTLY`.

**User:** The index helped — down to 200ms. But I'm worried this keeps happening as we grow.

**Assistant:** Set up a weekly slow-query review: log queries over 500ms, review the top 5 every Monday. Also add a CI check that runs EXPLAIN on new migrations touching large tables. Prevention beats firefighting.

**User:** Good plan. I'll add the CI check this week and schedule the Monday review.

**Assistant:** One more thing — watch out for N+1 queries from the ORM. Enable SQL logging in staging and grep for repeated identical queries. That's the next most common cause after missing indexes.
