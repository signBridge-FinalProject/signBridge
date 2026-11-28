-- SB-51 example queries over the dataset inventory tables (SB-47 schema).
--
-- Every query is scoped to one release through the named parameters
-- :dataset_name and :dataset_version (query 5 also uses :sample_id).
-- Python:  conn.execute(sql, {"dataset_name": "AUTSL", "dataset_version": "..."})
-- sqlite3 CLI:  .param set :dataset_name 'AUTSL'   (likewise for the others)
--
-- Each query starts with a "-- name:" line so tests can run them one by one.
-- original_label is opaque provider text; CAST(... AS INTEGER) below is only a
-- display ordering for numeric class IDs and does not change stored values.

-- name: samples_per_split
-- 1. Number of samples (color/depth pairs) in each split.
SELECT split_name, count(*) AS samples
FROM video_sample
WHERE dataset_name = :dataset_name AND dataset_version = :dataset_version
GROUP BY split_name
ORDER BY CASE split_name WHEN 'train' THEN 1 WHEN 'validation' THEN 2 ELSE 3 END;

-- name: samples_per_class_and_split
-- 2. Number of samples per class and per split, with the provider's Turkish and
--    English class names exactly as imported.
SELECT c.original_label, c.name_tr, c.name_en, v.split_name, count(*) AS samples
FROM video_sample AS v
JOIN dataset_class AS c
  ON c.dataset_name = v.dataset_name AND c.dataset_version = v.dataset_version
 AND c.original_label = v.original_label
WHERE v.dataset_name = :dataset_name AND v.dataset_version = :dataset_version
GROUP BY c.original_label, c.name_tr, c.name_en, v.split_name
ORDER BY CAST(c.original_label AS INTEGER), c.original_label,
         CASE v.split_name WHEN 'train' THEN 1 WHEN 'validation' THEN 2 ELSE 3 END;

-- name: signers_per_split
-- 3. Number of signers in each split and the comma-separated signer list.
SELECT split_name, count(*) AS signers, group_concat(signer_id, ',') AS signer_list
FROM (SELECT split_name, signer_id
      FROM dataset_signer_split
      WHERE dataset_name = :dataset_name AND dataset_version = :dataset_version
      ORDER BY split_name, signer_id)
GROUP BY split_name
ORDER BY CASE split_name WHEN 'train' THEN 1 WHEN 'validation' THEN 2 ELSE 3 END;

-- name: classes_with_fewest_train_samples
-- 4. The ten classes with the fewest training samples, including classes with
--    no training sample at all (count 0).
SELECT c.original_label, c.name_tr, c.name_en, count(v.sample_id) AS train_samples
FROM dataset_class AS c
LEFT JOIN video_sample AS v
  ON v.dataset_name = c.dataset_name AND v.dataset_version = c.dataset_version
 AND v.original_label = c.original_label AND v.split_name = 'train'
WHERE c.dataset_name = :dataset_name AND c.dataset_version = :dataset_version
GROUP BY c.original_label, c.name_tr, c.name_en
ORDER BY train_samples, CAST(c.original_label AS INTEGER), c.original_label
LIMIT 10;

-- name: sample_lookup
-- 5. Class, class names, signer, split and relative file paths of one sample.
--    Paths are relative to the release's private media root.
SELECT v.sample_id, v.original_label, c.name_tr, c.name_en, v.signer_id, v.split_name,
       v.color_path, v.depth_path, v.color_bytes, v.depth_bytes
FROM video_sample AS v
JOIN dataset_class AS c
  ON c.dataset_name = v.dataset_name AND c.dataset_version = v.dataset_version
 AND c.original_label = v.original_label
WHERE v.dataset_name = :dataset_name AND v.dataset_version = :dataset_version
  AND v.sample_id = :sample_id;

-- name: samples_per_signer
-- 6. Number of samples recorded by each signer, with the signer's split.
SELECT signer_id, split_name, count(*) AS samples
FROM video_sample
WHERE dataset_name = :dataset_name AND dataset_version = :dataset_version
GROUP BY signer_id, split_name
ORDER BY CASE split_name WHEN 'train' THEN 1 WHEN 'validation' THEN 2 ELSE 3 END, signer_id;
