-- Source fixture: exercises identity preservation, FK ordering, self-ref FK,
-- a non-autoincrement PK table, a view, and the MySQL-only types that stress
-- MySQL->MSSQL translation (UNSIGNED, JSON, TINYINT(1), ENUM, DOUBLE, TEXT).

CREATE DATABASE IF NOT EXISTS testdb;
USE testdb;

-- the mysql client loading this file defaults to latin1; without this the
-- UTF-8 bytes below would be double-encoded at seed time.
SET NAMES utf8mb4;

CREATE TABLE parent (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(100) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE child (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  parent_id INT NOT NULL,
  qty       INT UNSIGNED DEFAULT 0,
  big_qty   BIGINT UNSIGNED DEFAULT 0,
  price     DECIMAL(10,2),
  meta      JSON,
  notes     TEXT,
  is_active TINYINT(1) DEFAULT 1,
  status    ENUM('new','active','done') DEFAULT 'new',
  ratio     DOUBLE,
  CONSTRAINT fk_child_parent FOREIGN KEY (parent_id) REFERENCES parent(id)
);

-- self-referential FK: forces FK-disable load (no parent-first order exists)
CREATE TABLE employee (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(100),
  manager_id INT NULL,
  CONSTRAINT fk_emp_mgr FOREIGN KEY (manager_id) REFERENCES employee(id)
);

-- non-autoincrement PK: must NOT get IDENTITY_INSERT
CREATE TABLE tag (
  code  VARCHAR(20) PRIMARY KEY,
  label VARCHAR(100)
);

INSERT INTO parent (name) VALUES ('Acme'), ('O''Brien & Co'), ('Çağrı Ünicode');

INSERT INTO child (parent_id, qty, big_qty, price, meta, notes, is_active, status, ratio) VALUES
 (1, 5,          10,                  19.99,      '{"a":1,"b":[2,3]}',  'first note',                 1, 'active', 1.5),
 (1, 0,          0,                   NULL,       NULL,                 NULL,                         0, 'new',    NULL),
 (2, 4294967295, 18446744073709551615, 1234567.89, '{"x":"quote''d"}',  'has ''quotes'' and stuff',   1, 'done',   3.14159);

INSERT INTO employee (name, manager_id) VALUES ('CEO', NULL);
INSERT INTO employee (name, manager_id) VALUES ('VP', 1);

INSERT INTO tag (code, label) VALUES ('A', 'Alpha'), ('B', 'Beta');

CREATE VIEW v_active_children AS
SELECT p.name AS parent_name, c.qty, c.status
FROM parent p JOIN child c ON c.parent_id = p.id
WHERE c.is_active = 1;
