from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import clean_json, close_pool, fetch_all, fetch_one, init_pool


def address_label(alias: str) -> str:
    return f"""
        coalesce(
            nullif({alias}.display_name, ''),
            nullif({alias}.name, ''),
            nullif(
                concat_ws(', ',
                    nullif({alias}.road, ''),
                    nullif({alias}.neighbourhood, ''),
                    nullif({alias}.city, ''),
                    nullif({alias}.state, ''),
                    nullif({alias}.country, '')
                ),
                ''
            ),
            '未知地点'
        )
    """


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_pool()
    yield
    close_pool()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )


def _period(car_id: int, days: int) -> dict[str, datetime | int | None]:
    row = fetch_one(
        """
        select min(date) as first_seen_at, max(date) as last_seen_at
        from public.positions
        where car_id = %s
        """,
        (car_id,),
    )
    if not row or row["last_seen_at"] is None:
        raise HTTPException(status_code=404, detail="未找到车辆位置数据")

    last_seen_at = row["last_seen_at"]
    since = None if days == 0 else last_seen_at - timedelta(days=days)
    return {
        "days": days,
        "since": since,
        "until": last_seen_at,
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": last_seen_at,
    }


def _cars() -> list[dict[str, Any]]:
    nearest_location = f"""
        select {address_label("addr")} as label
        from public.addresses addr
        where p.latitude is not null
          and p.longitude is not null
          and addr.latitude is not null
          and addr.longitude is not null
        order by earth_distance(
            ll_to_earth(p.latitude::float8, p.longitude::float8),
            ll_to_earth(addr.latitude::float8, addr.longitude::float8)
        )
        limit 1
    """
    return fetch_all(
        f"""
        select
            c.id,
            c.name,
            c.model,
            c.marketing_name,
            c.trim_badging,
            c.exterior_color,
            c.wheel_type,
            c.efficiency,
            c.inserted_at,
            c.updated_at,
            p.date as latest_seen_at,
            p.odometer,
            p.battery_level,
            p.usable_battery_level,
            p.rated_battery_range_km,
            p.ideal_battery_range_km,
            p.latitude,
            p.longitude,
            p.speed,
            p.power,
            p.outside_temp,
            p.inside_temp,
            p.tpms_pressure_fl,
            p.tpms_pressure_fr,
            p.tpms_pressure_rl,
            p.tpms_pressure_rr,
            s.state::text as current_state,
            s.start_date as state_since,
            u.version as software_version,
            loc.label as location_label
        from public.cars c
        left join lateral (
            select *
            from public.positions
            where car_id = c.id
            order by date desc
            limit 1
        ) p on true
        left join lateral (
            select *
            from public.states
            where car_id = c.id
            order by start_date desc
            limit 1
        ) s on true
        left join lateral (
            select *
            from public.updates
            where car_id = c.id
            order by start_date desc
            limit 1
        ) u on true
        left join lateral ({nearest_location}) loc on true
        order by c.display_priority asc, c.id asc
        """
    )


@app.get("/health")
def health() -> dict[str, Any]:
    fetch_one("select 1 as ok")
    return {"ok": True}


@app.get("/api/cars")
def cars() -> Any:
    return clean_json({"cars": _cars()})


@app.get("/api/cars/{car_id}/dashboard")
def dashboard(
    car_id: int,
    days: int = Query(default=30, ge=0, le=3650, description="0 表示全部数据"),
) -> Any:
    cars_by_id = {car["id"]: car for car in _cars()}
    car = cars_by_id.get(car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="未找到车辆")

    period = _period(car_id, days)
    since = period["since"]
    until = period["until"]

    drive_stats = fetch_one(
        """
        select
            count(*)::int as drive_count,
            coalesce(sum(distance), 0)::float8 as distance_km,
            coalesce(sum(duration_min), 0)::float8 as duration_min,
            max(speed_max)::float8 as max_speed_kmh,
            avg(nullif(speed_max, 0))::float8 as avg_max_speed_kmh,
            coalesce(sum(
                case
                    when d.distance > 0
                     and d.start_rated_range_km is not null
                     and d.end_rated_range_km is not null
                     and d.start_rated_range_km > d.end_rated_range_km
                     and c.efficiency is not null
                    then (d.start_rated_range_km - d.end_rated_range_km) * c.efficiency
                    else 0
                end
            ), 0)::float8 as estimated_drive_kwh,
            case
                when coalesce(sum(nullif(d.distance, 0)), 0) > 0 then
                    (
                        sum(
                            case
                                when d.distance > 0
                                 and d.start_rated_range_km is not null
                                 and d.end_rated_range_km is not null
                                 and d.start_rated_range_km > d.end_rated_range_km
                                 and c.efficiency is not null
                                then (d.start_rated_range_km - d.end_rated_range_km) * c.efficiency
                                else 0
                            end
                        ) / nullif(sum(d.distance), 0)
                    ) * 100
                else null
            end::float8 as estimated_kwh_per_100km
        from public.drives d
        join public.cars c on c.id = d.car_id
        where d.car_id = %s
          and (%s::timestamp is null or d.start_date >= %s::timestamp)
        """,
        (car_id, since, since),
    )

    charge_stats = fetch_one(
        """
        select
            count(*)::int as charge_count,
            count(*) filter (where end_date is null)::int as active_charge_count,
            coalesce(sum(charge_energy_added), 0)::float8 as charge_energy_added_kwh,
            coalesce(sum(charge_energy_used), 0)::float8 as charge_energy_used_kwh,
            coalesce(sum(cost), 0)::float8 as cost,
            avg(end_battery_level - start_battery_level)::float8 as avg_soc_added_pct,
            max(end_battery_level)::int as max_end_battery_level
        from public.charging_processes
        where car_id = %s
          and (%s::timestamp is null or start_date >= %s::timestamp)
        """,
        (car_id, since, since),
    )

    lifetime = fetch_one(
        """
        select
            (select count(*)::int from public.drives where car_id = %s) as drive_count,
            (select coalesce(sum(distance), 0)::float8 from public.drives where car_id = %s) as distance_km,
            (select count(*)::int from public.charging_processes where car_id = %s) as charge_count,
            (select coalesce(sum(charge_energy_added), 0)::float8 from public.charging_processes where car_id = %s) as charge_energy_added_kwh,
            (select min(odometer)::float8 from public.positions where car_id = %s and odometer is not null) as first_odometer_km,
            (select max(odometer)::float8 from public.positions where car_id = %s and odometer is not null) as latest_odometer_km
        """,
        (car_id, car_id, car_id, car_id, car_id, car_id),
    )

    daily = fetch_all(
        """
        with drive_days as (
            select
                date_trunc('day', start_date)::date as day,
                count(*)::int as drives,
                coalesce(sum(distance), 0)::float8 as distance_km,
                coalesce(sum(duration_min), 0)::float8 as duration_min,
                max(speed_max)::float8 as max_speed_kmh
            from public.drives
            where car_id = %s
              and (%s::timestamp is null or start_date >= %s::timestamp)
            group by 1
        ),
        charge_days as (
            select
                date_trunc('day', start_date)::date as day,
                count(*)::int as charges,
                coalesce(sum(charge_energy_added), 0)::float8 as charge_energy_added_kwh,
                coalesce(sum(cost), 0)::float8 as cost
            from public.charging_processes
            where car_id = %s
              and (%s::timestamp is null or start_date >= %s::timestamp)
            group by 1
        )
        select
            coalesce(d.day, c.day) as day,
            coalesce(d.drives, 0) as drives,
            coalesce(d.distance_km, 0)::float8 as distance_km,
            coalesce(d.duration_min, 0)::float8 as duration_min,
            d.max_speed_kmh,
            coalesce(c.charges, 0) as charges,
            coalesce(c.charge_energy_added_kwh, 0)::float8 as charge_energy_added_kwh,
            coalesce(c.cost, 0)::float8 as cost
        from drive_days d
        full outer join charge_days c using (day)
        order by day
        """,
        (car_id, since, since, car_id, since, since),
    )

    monthly = fetch_all(
        """
        with drive_months as (
            select
                date_trunc('month', start_date)::date as month,
                count(*)::int as drives,
                coalesce(sum(distance), 0)::float8 as distance_km
            from public.drives
            where car_id = %s
              and (%s::timestamp is null or start_date >= %s::timestamp)
            group by 1
        ),
        charge_months as (
            select
                date_trunc('month', start_date)::date as month,
                count(*)::int as charges,
                coalesce(sum(charge_energy_added), 0)::float8 as charge_energy_added_kwh,
                coalesce(sum(cost), 0)::float8 as cost
            from public.charging_processes
            where car_id = %s
              and (%s::timestamp is null or start_date >= %s::timestamp)
            group by 1
        )
        select
            coalesce(d.month, c.month) as month,
            coalesce(d.drives, 0) as drives,
            coalesce(d.distance_km, 0)::float8 as distance_km,
            coalesce(c.charges, 0) as charges,
            coalesce(c.charge_energy_added_kwh, 0)::float8 as charge_energy_added_kwh,
            coalesce(c.cost, 0)::float8 as cost
        from drive_months d
        full outer join charge_months c using (month)
        order by month
        """,
        (car_id, since, since, car_id, since, since),
    )

    states = fetch_all(
        """
        with params as (
            select %s::timestamp as since, %s::timestamp as until
        )
        select
            s.state::text as state,
            (
                sum(
                    greatest(
                        0::double precision,
                        extract(
                            epoch from (
                                least(coalesce(s.end_date, p.until), p.until)
                                - greatest(s.start_date, coalesce(p.since, s.start_date))
                            )
                        )::double precision
                    )
                ) / 3600.0
            )::float8 as hours
        from public.states s
        cross join params p
        where s.car_id = %s
          and s.start_date <= p.until
          and coalesce(s.end_date, p.until) >= coalesce(p.since, '-infinity'::timestamp)
        group by s.state
        order by hours desc
        """,
        (since, until, car_id),
    )

    range_series = fetch_all(
        """
        select distinct on (date_trunc('day', date))
            date_trunc('day', date)::date as day,
            date as sampled_at,
            battery_level,
            usable_battery_level,
            rated_battery_range_km::float8 as rated_battery_range_km,
            ideal_battery_range_km::float8 as ideal_battery_range_km,
            odometer::float8 as odometer
        from public.positions
        where car_id = %s
          and (%s::timestamp is null or date >= %s::timestamp)
          and battery_level is not null
        order by date_trunc('day', date), date desc
        """,
        (car_id, since, since),
    )

    drive_location_start = f"coalesce(nullif(sg.name, ''), {address_label('sa')})"
    drive_location_end = f"coalesce(nullif(eg.name, ''), {address_label('ea')})"
    recent_drives = fetch_all(
        f"""
        select
            d.id,
            d.start_date,
            d.end_date,
            d.distance::float8 as distance_km,
            d.duration_min,
            d.speed_max,
            d.power_max,
            d.power_min,
            d.outside_temp_avg::float8 as outside_temp_avg,
            d.inside_temp_avg::float8 as inside_temp_avg,
            d.ascent,
            d.descent,
            {drive_location_start} as start_location,
            {drive_location_end} as end_location,
            case
                when d.distance > 0
                 and d.start_rated_range_km is not null
                 and d.end_rated_range_km is not null
                 and d.start_rated_range_km > d.end_rated_range_km
                 and c.efficiency is not null
                then ((d.start_rated_range_km - d.end_rated_range_km) * c.efficiency)::float8
                else null
            end as estimated_kwh
        from public.drives d
        join public.cars c on c.id = d.car_id
        left join public.addresses sa on sa.id = d.start_address_id
        left join public.addresses ea on ea.id = d.end_address_id
        left join public.geofences sg on sg.id = d.start_geofence_id
        left join public.geofences eg on eg.id = d.end_geofence_id
        where d.car_id = %s
          and (%s::timestamp is null or d.start_date >= %s::timestamp)
        order by d.start_date desc
        limit 12
        """,
        (car_id, since, since),
    )

    charge_location = f"coalesce(nullif(g.name, ''), {address_label('a')})"
    recent_charges = fetch_all(
        f"""
        select
            cp.id,
            cp.start_date,
            cp.end_date,
            cp.charge_energy_added::float8 as charge_energy_added_kwh,
            cp.charge_energy_used::float8 as charge_energy_used_kwh,
            cp.start_battery_level,
            cp.end_battery_level,
            cp.duration_min,
            cp.outside_temp_avg::float8 as outside_temp_avg,
            cp.cost::float8 as cost,
            {charge_location} as location,
            ch.max_power_kw,
            ch.fast_charger
        from public.charging_processes cp
        left join public.addresses a on a.id = cp.address_id
        left join public.geofences g on g.id = cp.geofence_id
        left join lateral (
            select
                max(charger_power)::float8 as max_power_kw,
                bool_or(coalesce(fast_charger_present, false)) as fast_charger
            from public.charges
            where charging_process_id = cp.id
        ) ch on true
        where cp.car_id = %s
          and (%s::timestamp is null or cp.start_date >= %s::timestamp)
        order by cp.start_date desc
        limit 12
        """,
        (car_id, since, since),
    )

    top_destinations = fetch_all(
        f"""
        select
            {drive_location_end} as location,
            count(*)::int as visits,
            coalesce(sum(d.distance), 0)::float8 as arriving_distance_km,
            max(d.end_date) as last_seen_at
        from public.drives d
        left join public.addresses ea on ea.id = d.end_address_id
        left join public.geofences eg on eg.id = d.end_geofence_id
        left join public.addresses sa on sa.id = d.start_address_id
        left join public.geofences sg on sg.id = d.start_geofence_id
        where d.car_id = %s
          and d.end_date is not null
          and coalesce(d.distance, 0) > 0.1
          and (%s::timestamp is null or d.start_date >= %s::timestamp)
        group by location
        order by visits desc, last_seen_at desc
        limit 8
        """,
        (car_id, since, since),
    )

    top_charge_locations = fetch_all(
        f"""
        select
            {charge_location} as location,
            count(*)::int as sessions,
            coalesce(sum(cp.charge_energy_added), 0)::float8 as charge_energy_added_kwh,
            max(cp.start_date) as last_seen_at
        from public.charging_processes cp
        left join public.addresses a on a.id = cp.address_id
        left join public.geofences g on g.id = cp.geofence_id
        where cp.car_id = %s
          and (%s::timestamp is null or cp.start_date >= %s::timestamp)
        group by location
        order by sessions desc, last_seen_at desc
        limit 8
        """,
        (car_id, since, since),
    )

    updates = fetch_all(
        """
        select id, start_date, end_date, version
        from public.updates
        where car_id = %s
        order by start_date desc
        limit 8
        """,
        (car_id,),
    )

    active_charge = fetch_one(
        f"""
        select
            cp.id,
            cp.start_date,
            cp.charge_energy_added::float8 as charge_energy_added_kwh,
            cp.start_battery_level,
            cp.end_battery_level,
            {charge_location} as location
        from public.charging_processes cp
        left join public.addresses a on a.id = cp.address_id
        left join public.geofences g on g.id = cp.geofence_id
        where cp.car_id = %s
          and cp.end_date is null
        order by cp.start_date desc
        limit 1
        """,
        (car_id,),
    )

    return clean_json(
        {
            "car": car,
            "data_window": period,
            "summary": {
                **(drive_stats or {}),
                **(charge_stats or {}),
            },
            "lifetime": lifetime or {},
            "daily": daily,
            "monthly": monthly,
            "states": states,
            "range": range_series,
            "recent_drives": recent_drives,
            "recent_charges": recent_charges,
            "locations": {
                "destinations": top_destinations,
                "charging": top_charge_locations,
            },
            "updates": updates,
            "active_charge": active_charge,
        }
    )
