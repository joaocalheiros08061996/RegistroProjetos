create table if not exists auth_privacy_acknowledgements (
    id bigserial primary key,
    user_id text not null,
    policy_version text not null,
    status text not null check (status in ('ACKNOWLEDGED', 'LEGACY_PENDING')),
    source text not null check (source in ('SIGNUP', 'ADMIN_CSV')),
    email_hash text not null,
    ip_hash text null,
    acknowledged_at timestamptz null,
    recorded_at timestamptz not null default now(),
    administrative_reason text null,

    unique (user_id, policy_version),

    check (
        (
            status = 'ACKNOWLEDGED'
            and source = 'SIGNUP'
            and acknowledged_at is not null
            and ip_hash is not null
            and administrative_reason is null
        )
        or
        (
            status = 'LEGACY_PENDING'
            and source = 'ADMIN_CSV'
            and acknowledged_at is null
            and ip_hash is null
            and administrative_reason is not null
        )
    )
);

create index if not exists idx_auth_privacy_ack_user
on auth_privacy_acknowledgements(user_id);

create index if not exists idx_auth_privacy_ack_policy
on auth_privacy_acknowledgements(policy_version);
