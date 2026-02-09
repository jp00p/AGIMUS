UPDATE crystal_instances
SET status = 'available'
WHERE status NOT IN ('available','attuned','harmonized','dematerialized','rematerialized');

ALTER TABLE crystal_instances
  MODIFY COLUMN status ENUM(
    'available',
    'attuned',
    'harmonized',
    'dematerialized',
    'rematerialized'
  )
  NOT NULL
  DEFAULT 'available';

DELETE i1 FROM crystal_rematerialization_items i1
JOIN crystal_rematerialization_items i2
  ON i1.rematerialization_id = i2.rematerialization_id
 AND i1.crystal_instance_id = i2.crystal_instance_id
 AND i1.id > i2.id;

ALTER TABLE crystal_rematerialization_items
  ADD UNIQUE KEY uq_remat_item (rematerialization_id, crystal_instance_id),
  ADD KEY idx_remat_id (rematerialization_id);
