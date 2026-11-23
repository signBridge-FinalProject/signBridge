-- SB-47: SQLite metadata schema. No dataset rows or raw media are seeded.
-- Run through db.py (foreign_keys and recursive_triggers enabled per connection).

CREATE TABLE sign_entry (
    sign_id TEXT PRIMARY KEY CHECK(sign_id GLOB 'SIGN_[0-9][0-9][0-9][0-9]*'
        AND substr(sign_id, 6) NOT GLOB '*[^0-9]*'),
    gloss TEXT NOT NULL CHECK(length(trim(gloss)) > 0),
    definition_tr TEXT NOT NULL CHECK(length(trim(definition_tr)) > 0),
    domain TEXT NOT NULL CHECK(domain IN ('daily','health','pharmacy','public_service')),
    variant_code TEXT NOT NULL CHECK(length(trim(variant_code)) > 0),
    lexical_nonmanual_notes TEXT,
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','source_checked','expert_reviewed')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))
) STRICT;

CREATE TABLE sign_equivalent (
    sign_id TEXT NOT NULL REFERENCES sign_entry(sign_id) ON DELETE RESTRICT,
    equivalent_tr TEXT NOT NULL CHECK(length(trim(equivalent_tr)) > 0),
    PRIMARY KEY(sign_id, equivalent_tr)
) STRICT;

CREATE TABLE sign_source (
    source_id TEXT PRIMARY KEY CHECK(length(trim(source_id)) > 0),
    sign_id TEXT NOT NULL REFERENCES sign_entry(sign_id) ON DELETE RESTRICT,
    source_title TEXT NOT NULL CHECK(length(trim(source_title)) > 0),
    source_url TEXT CHECK(source_url IS NULL OR source_url LIKE 'https://%' OR source_url LIKE 'http://%'),
    source_item_ref TEXT NOT NULL CHECK(length(trim(source_item_ref)) > 0),
    checked_on TEXT CHECK(checked_on IS NULL OR
        (length(checked_on)=10 AND date(checked_on,'+0 days') IS NOT NULL
         AND date(checked_on,'+0 days')=checked_on)),
    rights_note TEXT,
    UNIQUE(source_id, sign_id)
) STRICT;

CREATE TABLE dataset_release (
    dataset_name TEXT NOT NULL CHECK(length(trim(dataset_name)) > 0),
    dataset_version TEXT NOT NULL CHECK(length(trim(dataset_version)) > 0
        AND lower(trim(dataset_version)) NOT IN ('unknown','tbd','latest')),
    description TEXT NOT NULL CHECK(length(trim(description)) > 0),
    source_reference TEXT NOT NULL CHECK(length(trim(source_reference)) > 0),
    usage_conditions TEXT NOT NULL CHECK(length(trim(usage_conditions)) > 0),
    PRIMARY KEY(dataset_name, dataset_version)
) STRICT;

CREATE TABLE dataset_class (
    dataset_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    original_label TEXT NOT NULL CHECK(length(trim(original_label)) > 0),
    name_tr TEXT,
    name_en TEXT,
    PRIMARY KEY(dataset_name, dataset_version, original_label),
    FOREIGN KEY(dataset_name, dataset_version)
        REFERENCES dataset_release(dataset_name, dataset_version) ON DELETE RESTRICT
) STRICT;

CREATE TABLE dataset_split (
    dataset_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    split_name TEXT NOT NULL CHECK(split_name IN ('train','validation','test')),
    PRIMARY KEY(dataset_name, dataset_version, split_name),
    FOREIGN KEY(dataset_name, dataset_version)
        REFERENCES dataset_release(dataset_name, dataset_version) ON DELETE RESTRICT
) STRICT;

-- A signer identifier belongs to exactly one split within a release.
CREATE TABLE dataset_signer_split (
    dataset_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    signer_id TEXT NOT NULL CHECK(length(trim(signer_id)) > 0),
    split_name TEXT NOT NULL,
    PRIMARY KEY(dataset_name, dataset_version, signer_id),
    UNIQUE(dataset_name, dataset_version, signer_id, split_name),
    FOREIGN KEY(dataset_name, dataset_version, split_name)
        REFERENCES dataset_split(dataset_name, dataset_version, split_name) ON DELETE RESTRICT
) STRICT;

-- One sample row represents an RGB/depth pair, not two independent samples.
-- Forward-slash paths are relative to a private, externally configured media root.
CREATE TABLE video_sample (
    dataset_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    sample_id TEXT NOT NULL CHECK(length(trim(sample_id)) > 0),
    original_label TEXT NOT NULL,
    signer_id TEXT NOT NULL,
    split_name TEXT NOT NULL,
    color_path TEXT NOT NULL CHECK(length(trim(color_path)) > 0 AND color_path LIKE '%.mp4'
        AND substr(color_path,1,1) <> '/' AND instr(color_path,':')=0
        AND instr(color_path,char(92))=0 AND instr('/'||color_path||'/','/../')=0
        AND instr('/'||color_path||'/','/./')=0 AND instr(color_path,'//')=0),
    depth_path TEXT NOT NULL CHECK(length(trim(depth_path)) > 0 AND depth_path LIKE '%.mp4'
        AND substr(depth_path,1,1) <> '/' AND instr(depth_path,':')=0
        AND instr(depth_path,char(92))=0 AND instr('/'||depth_path||'/','/../')=0
        AND instr('/'||depth_path||'/','/./')=0 AND instr(depth_path,'//')=0),
    color_bytes INTEGER CHECK(color_bytes IS NULL OR color_bytes > 0),
    depth_bytes INTEGER CHECK(depth_bytes IS NULL OR depth_bytes > 0),
    PRIMARY KEY(dataset_name, dataset_version, sample_id),
    UNIQUE(dataset_name, dataset_version, color_path),
    UNIQUE(dataset_name, dataset_version, depth_path),
    CHECK(color_path <> depth_path),
    FOREIGN KEY(dataset_name, dataset_version, original_label)
        REFERENCES dataset_class(dataset_name, dataset_version, original_label) ON DELETE RESTRICT,
    FOREIGN KEY(dataset_name, dataset_version, signer_id, split_name)
        REFERENCES dataset_signer_split(dataset_name, dataset_version, signer_id, split_name) ON DELETE RESTRICT
) STRICT;

CREATE TABLE dataset_mapping (
    dataset_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    original_label TEXT NOT NULL,
    sign_id TEXT NOT NULL REFERENCES sign_entry(sign_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL,
    mapping_status TEXT NOT NULL DEFAULT 'candidate' CHECK(mapping_status IN ('candidate','confirmed')),
    PRIMARY KEY(dataset_name, dataset_version, original_label, sign_id),
    FOREIGN KEY(dataset_name, dataset_version, original_label)
        REFERENCES dataset_class(dataset_name, dataset_version, original_label) ON DELETE RESTRICT,
    FOREIGN KEY(source_id, sign_id) REFERENCES sign_source(source_id, sign_id) ON DELETE RESTRICT
) STRICT;
CREATE UNIQUE INDEX one_confirmed_class_mapping
    ON dataset_mapping(dataset_name, dataset_version, original_label)
    WHERE mapping_status='confirmed';

CREATE TABLE animation_clip (
    clip_id TEXT PRIMARY KEY CHECK(length(trim(clip_id)) > 0),
    sign_id TEXT NOT NULL REFERENCES sign_entry(sign_id) ON DELETE RESTRICT,
    asset_path TEXT NOT NULL CHECK(length(trim(asset_path)) > 0),
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','source_checked','expert_reviewed')),
    is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
    UNIQUE(clip_id, sign_id)
) STRICT;
CREATE UNIQUE INDEX one_default_clip ON animation_clip(sign_id) WHERE is_default=1;

CREATE TABLE review_event (
    event_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL UNIQUE CHECK(length(trim(review_id)) > 0),
    sign_id TEXT NOT NULL REFERENCES sign_entry(sign_id) ON DELETE RESTRICT,
    clip_id TEXT,
    target_status TEXT NOT NULL CHECK(target_status IN ('draft','source_checked','expert_reviewed')),
    source_id TEXT,
    reviewer_name TEXT NOT NULL CHECK(length(trim(reviewer_name)) > 0),
    reviewer_role TEXT NOT NULL CHECK(reviewer_role IN ('source_checker','TID_consultant','native_signer')),
    reviewed_at TEXT NOT NULL CHECK(length(reviewed_at)=20
        AND strftime('%Y-%m-%dT%H:%M:%SZ',reviewed_at) IS NOT NULL
        AND strftime('%Y-%m-%dT%H:%M:%SZ',reviewed_at)=reviewed_at),
    review_note TEXT NOT NULL CHECK(length(trim(review_note)) > 0),
    FOREIGN KEY(clip_id, sign_id) REFERENCES animation_clip(clip_id, sign_id) ON DELETE RESTRICT,
    FOREIGN KEY(source_id, sign_id) REFERENCES sign_source(source_id, sign_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE utterance (
    utterance_id TEXT PRIMARY KEY CHECK(length(trim(utterance_id)) > 0),
    text_tr TEXT,
    utterance_type TEXT NOT NULL DEFAULT 'unknown'
        CHECK(utterance_type IN ('declarative','polar_question','content_question','unknown')),
    validation_status TEXT NOT NULL DEFAULT 'illustrative'
        CHECK(validation_status IN ('illustrative','verified')),
    evidence_ref TEXT,
    reviewer_name TEXT,
    reviewed_on TEXT,
    CHECK(validation_status='illustrative' OR
        (evidence_ref IS NOT NULL AND length(trim(evidence_ref))>0
         AND reviewer_name IS NOT NULL AND length(trim(reviewer_name))>0
         AND reviewed_on IS NOT NULL AND length(reviewed_on)=10
         AND date(reviewed_on,'+0 days') IS NOT NULL AND date(reviewed_on,'+0 days')=reviewed_on))
) STRICT;

CREATE TABLE utterance_sign (
    utterance_id TEXT NOT NULL REFERENCES utterance(utterance_id) ON DELETE RESTRICT,
    position INTEGER NOT NULL CHECK(position > 0),
    sign_id TEXT NOT NULL REFERENCES sign_entry(sign_id) ON DELETE RESTRICT,
    PRIMARY KEY(utterance_id, position)
) STRICT;

CREATE TABLE nonmanual_span (
    span_id TEXT PRIMARY KEY CHECK(length(trim(span_id)) > 0),
    utterance_id TEXT NOT NULL REFERENCES utterance(utterance_id) ON DELETE RESTRICT,
    start_position INTEGER NOT NULL CHECK(start_position > 0),
    end_position INTEGER NOT NULL CHECK(end_position >= start_position),
    marker_description TEXT NOT NULL CHECK(length(trim(marker_description)) > 0),
    function_label TEXT NOT NULL CHECK(function_label IN ('question','negation','focus','other','unknown')),
    validation_status TEXT NOT NULL DEFAULT 'illustrative'
        CHECK(validation_status IN ('illustrative','verified')),
    evidence_ref TEXT,
    reviewer_name TEXT,
    reviewed_on TEXT,
    FOREIGN KEY(utterance_id, start_position) REFERENCES utterance_sign(utterance_id, position) ON DELETE RESTRICT,
    FOREIGN KEY(utterance_id, end_position) REFERENCES utterance_sign(utterance_id, position) ON DELETE RESTRICT,
    CHECK(validation_status='illustrative' OR
        (evidence_ref IS NOT NULL AND length(trim(evidence_ref))>0
         AND reviewer_name IS NOT NULL AND length(trim(reviewer_name))>0
         AND reviewed_on IS NOT NULL AND length(reviewed_on)=10
         AND date(reviewed_on,'+0 days') IS NOT NULL AND date(reviewed_on,'+0 days')=reviewed_on))
) STRICT;

CREATE INDEX samples_by_class ON video_sample(dataset_name,dataset_version,original_label);
CREATE INDEX samples_by_split ON video_sample(dataset_name,dataset_version,split_name);
CREATE INDEX equivalents_by_text ON sign_equivalent(equivalent_tr);
CREATE INDEX sources_by_sign ON sign_source(sign_id);
CREATE INDEX reviews_by_target ON review_event(sign_id,clip_id,event_sequence);

-- Stable sign IDs cannot be reassigned or reused. Retire entries with is_active=0.
CREATE TRIGGER stable_sign_id BEFORE UPDATE OF sign_id ON sign_entry
WHEN NEW.sign_id<>OLD.sign_id BEGIN SELECT RAISE(ABORT,'sign_id is immutable'); END;
CREATE TRIGGER retain_sign_ids BEFORE DELETE ON sign_entry
BEGIN SELECT RAISE(ABORT,'retire signs with is_active=0; IDs must not be reused'); END;

CREATE TRIGGER sign_starts_draft BEFORE INSERT ON sign_entry
WHEN NEW.review_status<>'draft' BEGIN SELECT RAISE(ABORT,'new sign must be draft'); END;
CREATE TRIGGER clip_starts_draft BEFORE INSERT ON animation_clip
WHEN NEW.review_status<>'draft' BEGIN SELECT RAISE(ABORT,'new clip must be draft'); END;

CREATE TRIGGER review_append_only_update BEFORE UPDATE ON review_event
BEGIN SELECT RAISE(ABORT,'review_event is append-only'); END;
CREATE TRIGGER review_append_only_delete BEFORE DELETE ON review_event
BEGIN SELECT RAISE(ABORT,'review_event is append-only'); END;

CREATE TRIGGER review_validate BEFORE INSERT ON review_event BEGIN
    SELECT CASE WHEN NEW.clip_id IS NOT NULL AND NOT EXISTS
        (SELECT 1 FROM animation_clip WHERE clip_id=NEW.clip_id AND sign_id=NEW.sign_id)
        THEN RAISE(ABORT,'clip must belong to reviewed sign') END;
    SELECT CASE WHEN NEW.target_status<>'draft' AND NOT EXISTS
        (SELECT 1 FROM sign_source WHERE source_id=NEW.source_id AND sign_id=NEW.sign_id AND checked_on IS NOT NULL)
        THEN RAISE(ABORT,'promotion requires checked source for same sign') END;
    SELECT CASE WHEN NEW.clip_id IS NULL AND NEW.target_status<>'draft' AND NOT EXISTS
        (SELECT 1 FROM sign_equivalent WHERE sign_id=NEW.sign_id)
        THEN RAISE(ABORT,'reviewed sign requires a Turkish equivalent') END;
    SELECT CASE WHEN NEW.target_status='source_checked' AND
        COALESCE((SELECT review_status FROM animation_clip WHERE clip_id=NEW.clip_id),
                 (SELECT review_status FROM sign_entry WHERE sign_id=NEW.sign_id))<>'draft'
        THEN RAISE(ABORT,'source_checked transition must start at draft') END;
    SELECT CASE WHEN NEW.target_status='expert_reviewed' AND
        (NEW.reviewer_role NOT IN ('TID_consultant','native_signer') OR
         COALESCE((SELECT review_status FROM animation_clip WHERE clip_id=NEW.clip_id),
                  (SELECT review_status FROM sign_entry WHERE sign_id=NEW.sign_id))<>'source_checked')
        THEN RAISE(ABORT,'expert promotion requires prior source check and qualified reviewer role') END;
END;
CREATE TRIGGER review_apply AFTER INSERT ON review_event BEGIN
    UPDATE sign_entry SET review_status=NEW.target_status
        WHERE sign_id=NEW.sign_id AND NEW.clip_id IS NULL;
    UPDATE animation_clip SET review_status=NEW.target_status
        WHERE clip_id=NEW.clip_id AND sign_id=NEW.sign_id;
END;
CREATE TRIGGER sign_status_requires_event BEFORE UPDATE OF review_status ON sign_entry
WHEN NEW.review_status<>OLD.review_status AND NEW.review_status IS NOT
    (SELECT target_status FROM review_event WHERE sign_id=OLD.sign_id AND clip_id IS NULL
     ORDER BY event_sequence DESC LIMIT 1)
BEGIN SELECT RAISE(ABORT,'change sign status through a review event'); END;
CREATE TRIGGER clip_status_requires_event BEFORE UPDATE OF review_status ON animation_clip
WHEN NEW.review_status<>OLD.review_status AND NEW.review_status IS NOT
    (SELECT target_status FROM review_event WHERE sign_id=OLD.sign_id AND clip_id=OLD.clip_id
     ORDER BY event_sequence DESC LIMIT 1)
BEGIN SELECT RAISE(ABORT,'change clip status through a review event'); END;

-- Material edits require an explicit, recorded demotion first.
CREATE TRIGGER sign_edit_requires_draft BEFORE UPDATE ON sign_entry
WHEN OLD.review_status<>'draft' AND
    (NEW.gloss IS NOT OLD.gloss OR NEW.definition_tr IS NOT OLD.definition_tr
     OR NEW.domain IS NOT OLD.domain OR NEW.variant_code IS NOT OLD.variant_code
     OR NEW.lexical_nonmanual_notes IS NOT OLD.lexical_nonmanual_notes)
BEGIN SELECT RAISE(ABORT,'demote sign before material edit'); END;
CREATE TRIGGER clip_edit_requires_draft BEFORE UPDATE ON animation_clip
WHEN OLD.review_status<>'draft' AND
    (NEW.asset_path IS NOT OLD.asset_path OR NEW.sign_id IS NOT OLD.sign_id)
BEGIN SELECT RAISE(ABORT,'demote clip before material edit'); END;
CREATE TRIGGER equivalent_insert_requires_draft BEFORE INSERT ON sign_equivalent
WHEN (SELECT review_status FROM sign_entry WHERE sign_id=NEW.sign_id)<>'draft'
BEGIN SELECT RAISE(ABORT,'demote sign before changing equivalents'); END;
CREATE TRIGGER equivalent_update_requires_draft BEFORE UPDATE ON sign_equivalent
WHEN EXISTS(SELECT 1 FROM sign_entry WHERE sign_id IN (OLD.sign_id,NEW.sign_id) AND review_status<>'draft')
BEGIN SELECT RAISE(ABORT,'demote sign before changing equivalents'); END;
CREATE TRIGGER equivalent_delete_requires_draft BEFORE DELETE ON sign_equivalent
WHEN (SELECT review_status FROM sign_entry WHERE sign_id=OLD.sign_id)<>'draft'
BEGIN SELECT RAISE(ABORT,'demote sign before changing equivalents'); END;
CREATE TRIGGER reviewed_source_immutable BEFORE UPDATE ON sign_source
WHEN EXISTS(SELECT 1 FROM review_event WHERE source_id=OLD.source_id)
    OR EXISTS(SELECT 1 FROM dataset_mapping WHERE source_id=OLD.source_id AND mapping_status='confirmed')
BEGIN SELECT RAISE(ABORT,'referenced review evidence is immutable; create a new source'); END;
CREATE TRIGGER sign_demotion_rechecks_mappings AFTER UPDATE OF review_status ON sign_entry
WHEN NEW.review_status='draft' AND OLD.review_status<>'draft'
BEGIN UPDATE dataset_mapping SET mapping_status='candidate' WHERE sign_id=NEW.sign_id; END;

-- Confirmation is explicit; a matching dataset label is never enough.
CREATE TRIGGER mapping_confirm_insert BEFORE INSERT ON dataset_mapping
WHEN NEW.mapping_status='confirmed' AND NOT EXISTS
    (SELECT 1 FROM sign_entry s JOIN sign_source p ON p.sign_id=s.sign_id
     WHERE s.sign_id=NEW.sign_id AND s.review_status<>'draft'
       AND p.source_id=NEW.source_id AND p.checked_on IS NOT NULL
       AND p.rights_note IS NOT NULL AND length(trim(p.rights_note))>0 AND lower(trim(p.rights_note))<>'not assessed')
BEGIN SELECT RAISE(ABORT,'confirmed mapping requires reviewed sign, checked source and recorded rights assessment'); END;
CREATE TRIGGER mapping_confirm_update BEFORE UPDATE ON dataset_mapping
WHEN NEW.mapping_status='confirmed' AND NOT EXISTS
    (SELECT 1 FROM sign_entry s JOIN sign_source p ON p.sign_id=s.sign_id
     WHERE s.sign_id=NEW.sign_id AND s.review_status<>'draft'
       AND p.source_id=NEW.source_id AND p.checked_on IS NOT NULL
       AND p.rights_note IS NOT NULL AND length(trim(p.rights_note))>0 AND lower(trim(p.rights_note))<>'not assessed')
BEGIN SELECT RAISE(ABORT,'confirmed mapping requires reviewed sign, checked source and recorded rights assessment'); END;

-- An illustrative utterance may be assembled empty; verified ones cannot be empty.
CREATE TRIGGER utterance_starts_illustrative BEFORE INSERT ON utterance
WHEN NEW.validation_status<>'illustrative'
BEGIN SELECT RAISE(ABORT,'assemble utterance before verifying it'); END;
CREATE TRIGGER utterance_verify_nonempty BEFORE UPDATE OF validation_status ON utterance
WHEN NEW.validation_status='verified' AND NOT EXISTS
    (SELECT 1 FROM utterance_sign WHERE utterance_id=NEW.utterance_id)
BEGIN SELECT RAISE(ABORT,'verified utterance requires tokens'); END;
CREATE TRIGGER token_append_contiguous BEFORE INSERT ON utterance_sign
WHEN NEW.position<>(SELECT count(*)+1 FROM utterance_sign WHERE utterance_id=NEW.utterance_id)
BEGIN SELECT RAISE(ABORT,'append tokens contiguously from position 1'); END;
CREATE TRIGGER token_key_immutable BEFORE UPDATE OF utterance_id,position ON utterance_sign
WHEN NEW.utterance_id<>OLD.utterance_id OR NEW.position<>OLD.position
BEGIN SELECT RAISE(ABORT,'token keys immutable; rebuild illustrative sequence after removing spans'); END;
CREATE TRIGGER token_delete_last BEFORE DELETE ON utterance_sign
WHEN OLD.position<>(SELECT max(position) FROM utterance_sign WHERE utterance_id=OLD.utterance_id)
BEGIN SELECT RAISE(ABORT,'remove tokens from the end to retain contiguous positions'); END;

CREATE TRIGGER token_insert_invalidates AFTER INSERT ON utterance_sign BEGIN
    UPDATE utterance SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE utterance_id=NEW.utterance_id;
    UPDATE nonmanual_span SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE utterance_id=NEW.utterance_id;
END;
CREATE TRIGGER token_update_invalidates AFTER UPDATE OF sign_id ON utterance_sign
WHEN NEW.sign_id<>OLD.sign_id BEGIN
    UPDATE utterance SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE utterance_id=NEW.utterance_id;
    UPDATE nonmanual_span SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE utterance_id=NEW.utterance_id;
END;
CREATE TRIGGER token_delete_invalidates AFTER DELETE ON utterance_sign BEGIN
    UPDATE utterance SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE utterance_id=OLD.utterance_id;
    UPDATE nonmanual_span SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE utterance_id=OLD.utterance_id;
END;
CREATE TRIGGER utterance_edit_invalidates AFTER UPDATE OF text_tr,utterance_type ON utterance
WHEN NEW.text_tr IS NOT OLD.text_tr OR NEW.utterance_type IS NOT OLD.utterance_type BEGIN
    UPDATE utterance SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE utterance_id=NEW.utterance_id;
END;
CREATE TRIGGER span_edit_invalidates AFTER UPDATE OF utterance_id,start_position,end_position,marker_description,function_label ON nonmanual_span
WHEN NEW.utterance_id IS NOT OLD.utterance_id OR NEW.start_position<>OLD.start_position
    OR NEW.end_position<>OLD.end_position OR NEW.marker_description<>OLD.marker_description
    OR NEW.function_label<>OLD.function_label BEGIN
    UPDATE nonmanual_span SET validation_status='illustrative',evidence_ref=NULL,reviewer_name=NULL,reviewed_on=NULL
        WHERE span_id=NEW.span_id;
END;
