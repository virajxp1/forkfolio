-- Recipe ownership and visibility schema update for ForkFolio.
-- Run this after docs/supabase-auth-profile-schema.sql so public.profiles exists.

alter table public.recipes
    add column if not exists is_public boolean;

update public.recipes
set is_public = true
where is_public is null;

alter table public.recipes
    alter column is_public set default true;

alter table public.recipes
    alter column is_public set not null;

alter table public.recipes
    add column if not exists created_by_user_id uuid;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'recipes_created_by_user_id_fkey'
    ) then
        alter table public.recipes
            add constraint recipes_created_by_user_id_fkey
            foreign key (created_by_user_id)
            references public.profiles (id)
            on delete set null;
    end if;
end $$;

create index if not exists idx_recipes_is_public
    on public.recipes(is_public);

create index if not exists idx_recipes_created_by_user_id
    on public.recipes(created_by_user_id);
