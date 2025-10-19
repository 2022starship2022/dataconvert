DROP TABLE IF EXISTS "t_sqlite";
CREATE TABLE IF NOT EXISTS "t_sqlite" (
  "id" INTEGER,
  "name" TEXT,
  "score" REAL,
  "active" INTEGER
);
INSERT INTO "t_sqlite" ("id", "name", "score", "active") VALUES
  (1, 'Alice', 95.5, 1);
INSERT INTO "t_sqlite" ("id", "name", "score", "active") VALUES
  (2, 'Bob', 82.0, 0);
