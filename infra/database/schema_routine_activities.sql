create table if not exists atividades (
    id bigserial primary key,
    user_id text not null,
    user_email text,
    tipo_atividade text not null,
    descricao text,
    inicio timestamptz not null,
    fim timestamptz null,
    ano integer not null,
    mes integer not null,
    dia integer not null,
    horas_trabalhadas numeric(14,10),
    created_at timestamptz not null default now()
);

create unique index if not exists idx_atividades_user_open_unique
on atividades (user_id)
where fim is null;

create index if not exists idx_atividades_user_created
on atividades (user_id, created_at desc);

alter table atividades
add column if not exists user_email text;
