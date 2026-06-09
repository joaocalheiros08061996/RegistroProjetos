alter table tasks
add column if not exists description text not null default '';

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'tasks_description_max_length'
    ) then
        alter table tasks
        add constraint tasks_description_max_length
        check (char_length(description) <= 150);
    end if;
end $$;
