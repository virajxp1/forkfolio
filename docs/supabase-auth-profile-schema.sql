-- Supabase Auth profile schema for ForkFolio.
-- Run this in the Supabase SQL editor after enabling Auth > Google.

create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    display_name text null,
    avatar_url text null,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

alter table public.profiles enable row level security;

create or replace function public.set_profile_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists set_profiles_updated_at on public.profiles;

create trigger set_profiles_updated_at
before update on public.profiles
for each row
execute procedure public.set_profile_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, display_name, avatar_url)
    values (
        new.id,
        coalesce(
            nullif(new.raw_user_meta_data ->> 'full_name', ''),
            nullif(new.raw_user_meta_data ->> 'name', ''),
            split_part(coalesce(new.email, ''), '@', 1),
            'ForkFolio User'
        ),
        coalesce(
            nullif(new.raw_user_meta_data ->> 'avatar_url', ''),
            nullif(new.raw_user_meta_data ->> 'picture', '')
        )
    )
    on conflict (id) do update
    set
        display_name = excluded.display_name,
        avatar_url = excluded.avatar_url,
        updated_at = timezone('utc', now());

    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row
execute procedure public.handle_new_user();

create policy "Profiles are viewable by the owner"
on public.profiles
for select
to authenticated
using ((select auth.uid()) = id);

create policy "Profiles are editable by the owner"
on public.profiles
for update
to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);
