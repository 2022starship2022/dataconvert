DROP TABLE IF EXISTS `t_mysql`;
CREATE TABLE IF NOT EXISTS `t_mysql` (
  `id` INT,
  `name` TEXT,
  `score` DOUBLE,
  `active` BOOLEAN
);
INSERT INTO `t_mysql` (`id`, `name`, `score`, `active`) VALUES
  (1, 'Alice', 95.5, 1);
INSERT INTO `t_mysql` (`id`, `name`, `score`, `active`) VALUES
  (2, 'Bob', 82.0, 0);
