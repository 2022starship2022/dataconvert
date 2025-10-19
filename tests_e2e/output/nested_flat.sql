CREATE TABLE IF NOT EXISTS "nested_scores" (
  "id" INTEGER,
  "user.name" TEXT,
  "user.contact.email" TEXT,
  "user.contact.phone" TEXT,
  "tags" TEXT,
  "scores.math" INTEGER,
  "scores.english" INTEGER
);
INSERT INTO "nested_scores" ("id", "user.name", "user.contact.email", "user.contact.phone", "tags", "scores.math", "scores.english") VALUES
  (1, 'Alice', 'alice@example.com', '123', '["x", "y"]', 95, 88);
INSERT INTO "nested_scores" ("id", "user.name", "user.contact.email", "user.contact.phone", "tags", "scores.math", "scores.english") VALUES
  (2, 'Bob', 'bob@example.com', NULL, '[]', 78, 91);
