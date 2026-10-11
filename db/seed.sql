insert into projects (code, name, client_name, client_email, phase, start_date, target_date) values
  ('RVS-2041',  'Riverside Drainage Upgrade',      'Millbrook Public Works', 'dana.ortiz@example.com',  'design',     '2026-06-01', '2027-04-30'),
  ('OAK-1187',  'Oak Street Bridge Rehabilitation', 'Harlan County DOT',      'marcus.reed@example.com', 'design',     '2026-05-15', '2027-06-30'),
  ('LKV-3302',  'Lakeview Subdivision Grading',     'Lakeview Homes LLC',     'priya.shah@example.com',  'permitting', '2026-07-01', '2027-02-28'),
  ('CR12-0459', 'County Road 12 Widening',          'Harlan County DOT',      'teresa.nguyen@example.com', 'design',   '2026-08-01', '2027-09-30');

-- Each row names its project by code; the join looks up the real project id.
insert into tasks (project_id, title, owner, due_date, status, blocked_reason)
select p.id, v.title, v.owner, v.due::date, v.status, v.reason
from (values
  -- Riverside Drainage Upgrade
  ('RVS-2041', 'Complete hydraulic model for 25-year storm',        'Alex Romero',  '2026-10-16', 'open',    null),
  ('RVS-2041', 'Culvert replacement design at Sta. 12+40 (90% plans)', 'Alex Romero', '2026-10-30', 'open',  null),
  ('RVS-2041', 'Submit stormwater permit application to state DEQ', 'Morgan Hale',  '2026-10-23', 'blocked', 'Waiting on client''s signed owner authorization form'),
  ('RVS-2041', 'Topographic survey of outfall area',                'Casey Brooks', '2026-09-25', 'done',    null),
  ('RVS-2041', 'Review geotechnical report',                        'Riley Chen',   '2026-10-09', 'done',    null),
  ('RVS-2041', 'Prepare 60% cost estimate',                         'Sam Patel',    '2026-10-20', 'open',    null),
  ('RVS-2041', 'Schedule public meeting with residents',            'Sam Patel',    '2026-11-05', 'open',    null),
  -- Oak Street Bridge Rehabilitation
  ('OAK-1187', 'Bridge deck condition inspection report',           'Riley Chen',   '2026-09-30', 'done',    null),
  ('OAK-1187', 'Load rating analysis',                              'Riley Chen',   '2026-10-21', 'open',    null),
  ('OAK-1187', 'Traffic control plan for lane closure',             'Jordan Lee',   '2026-11-02', 'open',    null),
  ('OAK-1187', 'Coordinate power line relocation with utility',     'Jordan Lee',   '2026-10-14', 'blocked', 'Utility has not confirmed relocation schedule'),
  ('OAK-1187', 'Expansion joint replacement specifications',        'Alex Romero',  '2026-10-28', 'open',    null),
  ('OAK-1187', 'Prepare bid documents',                             'Jordan Lee',   '2026-12-04', 'open',    null),
  -- Lakeview Subdivision Grading
  ('LKV-3302', 'Mass grading plan',                                 'Alex Romero',  '2026-10-19', 'open',    null),
  ('LKV-3302', 'Erosion and sediment control plan',                 'Morgan Hale',  '2026-10-26', 'open',    null),
  ('LKV-3302', 'Boundary and topographic survey',                   'Casey Brooks', '2026-09-18', 'done',    null),
  ('LKV-3302', 'Revise lot layout per client feedback',             'Alex Romero',  '2026-10-13', 'open',    null),
  ('LKV-3302', 'Retaining wall design at lots 14-18',               'Riley Chen',   '2026-11-09', 'blocked', 'Need geotechnical boring data from client''s consultant'),
  ('LKV-3302', 'Submit preliminary plat to county',                 'Morgan Hale',  '2026-11-16', 'open',    null),
  -- County Road 12 Widening
  ('CR12-0459', 'Right-of-way survey',                              'Casey Brooks', '2026-10-07', 'done',    null),
  ('CR12-0459', 'Pavement design report',                           'Riley Chen',   '2026-10-22', 'open',    null),
  ('CR12-0459', 'Drainage ditch regrading plan',                    'Alex Romero',  '2026-11-06', 'open',    null),
  ('CR12-0459', 'Right-of-way acquisition exhibits',                'Morgan Hale',  '2026-10-29', 'open',    null),
  ('CR12-0459', '30% plan review meeting with county',              'Jordan Lee',   '2026-10-15', 'open',    null)
) as v(code, title, owner, due, status, reason)
join projects p on p.code = v.code;