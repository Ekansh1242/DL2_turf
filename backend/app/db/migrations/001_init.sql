CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE bookings
  ADD CONSTRAINT no_overlapping_bookings
  EXCLUDE USING gist (
    resource_id WITH =,
    tsrange(start_time, end_time) WITH &&
  )
  WHERE (status = 'confirmed');

CREATE INDEX idx_bookings_resource_time ON bookings (resource_id, start_time, end_time);
CREATE INDEX idx_agent_traces_request ON agent_traces (request_id);
