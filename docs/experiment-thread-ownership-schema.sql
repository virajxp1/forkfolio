-- Experiment thread ownership schema update for ForkFolio.
-- Run this after docs/supabase-auth-profile-schema.sql so public.profiles exists.

alter table public.experiment_threads
    add column if not exists created_by_user_id uuid;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'experiment_threads_created_by_user_id_fkey'
    ) then
        alter table public.experiment_threads
            add constraint experiment_threads_created_by_user_id_fkey
            foreign key (created_by_user_id)
            references public.profiles (id)
            on delete set null;
    end if;
end $$;

create index if not exists idx_experiment_threads_created_by_user_id
    on public.experiment_threads(created_by_user_id);
