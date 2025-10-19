DROP TABLE IF EXISTS "t_pg";
CREATE TABLE IF NOT EXISTS "t_pg" (
  "id" INTEGER,
  "name" TEXT,
  "score" DOUBLE PRECISION,
  "active" BOOLEAN
);
INSERT INTO "t_pg" ("id", "name", "score", "active") VALUES
  (1, 'Alice', 95.5, 1);
INSERT INTO "t_pg" ("id", "name", "score", "active") VALUES
  (2, 'Bob', 82.0, 0);
