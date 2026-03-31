create table if not exists projects (
    id bigserial primary key,
    user_id text not null,
    name text not null,
    project_type text not null,
    responsible_login text not null,
    fte numeric(10,2) not null check (fte > 0),

    planned_start timestamptz not null,
    planned_end timestamptz not null,

    severity text not null default 'NONE',
    urgency text not null default 'CAN_WAIT',
    trend text not null default 'STABLE',

    -- NOVOS CAMPOS
    objective text not null default 'PARTIALLY_DEFINED',
    method text not null default 'PARTIALLY_KNOWN',

    estimated_cost numeric(14,2) not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists tasks (
    id bigserial primary key,
    project_id bigint not null references projects(id) on delete cascade,
    user_id text not null,
    name text not null,

    planned_start timestamptz not null,
    planned_end timestamptz not null,

    cost numeric(14,2) not null default 0,
    status text not null default 'PLANNED',

    created_at timestamptz not null default now(),

    unique (project_id, user_id, name)
);

create table if not exists time_entries (
    id bigserial primary key,
    task_id bigint not null references tasks(id) on delete cascade,
    start_time timestamptz not null,
    end_time timestamptz null
);

-- Índices
create index if not exists idx_projects_user_id on projects(user_id);
create index if not exists idx_tasks_project_user on tasks(project_id, user_id);
create index if not exists idx_time_entries_task_start on time_entries(task_id, start_time);