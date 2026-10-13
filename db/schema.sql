-- Wipe and recreate everything (fine during development)
drop table if exists proposed_changes, extracted_items, documents, tasks, projects cascade;

create table projects (
    id            serial primary key,
    code          text unique not null,          -- e.g. RVS-2041
    name          text not null,                 -- e.g. Riverside Drainage Upgrade
    client_name   text not null,
    client_email  text,
    phase         text,                          -- design, permitting, construction...
    status        text not null default 'active',
    start_date    date,
    target_date   date
);

create table tasks (
    id              serial primary key,
    project_id      int not null references projects(id),
    title           text not null,
    owner           text,
    due_date        date,
    status          text not null default 'open'
                    check (status in ('open', 'blocked', 'done')),
    blocked_reason  text,
    notes           text,
    source_item_id  int,                         -- which extracted item created it, if any
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create table documents (
    id           serial primary key,
    project_id   int references projects(id),    -- can be null until we know the project
    kind         text not null
                 check (kind in ('email', 'meeting_note', 'rfi', 'report')),
    title        text not null,
    received_at  timestamptz not null default now(),
    raw_text     text not null,
    -- searchable version of the text, kept up to date automatically
    tsv          tsvector generated always as
                 (to_tsvector('english', title || ' ' || raw_text)) stored
);
create index documents_tsv_idx on documents using gin (tsv);

create table extracted_items (
    id            serial primary key,
    document_id   int not null references documents(id),
    project_id    int references projects(id),
    type          text not null
                  check (type in ('request', 'action_item', 'deadline', 'decision')),
    summary       text not null,
    due_date      date,
    owner         text,
    source_quote  text not null,                 -- exact words from the document
    confidence    text not null
                  check (confidence in ('high', 'medium', 'low')),
    created_at    timestamptz not null default now()
);

create table proposed_changes (
    id              serial primary key,
    project_id      int not null references projects(id),
    kind            text not null
                    check (kind in ('create_task', 'update_task', 'flag_conflict', 'client_update')),
    payload         jsonb not null,              -- the actual change, e.g. the new task's fields
    reason          text not null,               -- why the agent proposed it
    cited_item_ids  int[] not null default '{}',
    status          text not null default 'pending'
                    check (status in ('pending', 'approved', 'edited', 'rejected')),
    reviewer_note   text,
    created_at      timestamptz not null default now(),
    decided_at      timestamptz
);