from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def active_charge_condition(
    cp_alias: str = "cp",
    charge_alias: str = "ch",
    position_alias: str = "lp",
) -> str:
    return f"""
        {cp_alias}.end_date is null
        and {charge_alias}.latest_charge_at is not null
        and {charge_alias}.latest_charge_at >= localtimestamp - interval '45 minutes'
        and {charge_alias}.latest_charge_at >= coalesce(
            {position_alias}.latest_seen_at,
            {charge_alias}.latest_charge_at
        ) - interval '30 minutes'
        and not exists (
            select 1
            from public.drives later_drive
            where later_drive.car_id = {cp_alias}.car_id
              and later_drive.start_date > {cp_alias}.start_date
        )
        and not exists (
            select 1
            from public.charging_processes later_charge
            where later_charge.car_id = {cp_alias}.car_id
              and later_charge.start_date > {cp_alias}.start_date
        )
    """


MIN_REPORT_CHARGE_KWH = 0.5
TODAY_ENERGY_HISTORY_DAYS = 30
MAX_TODAY_ENERGY_SEGMENT_HOURS = 24


def report_charge_condition(cp_alias: str = "cp", latest_alias: str | None = None) -> str:
    energy = (
        f"coalesce({cp_alias}.charge_energy_added::float8, {latest_alias}.charge_energy_added_kwh, 0)"
        if latest_alias
        else f"coalesce({cp_alias}.charge_energy_added::float8, 0)"
    )
    end_battery_level = (
        f"coalesce({cp_alias}.end_battery_level, {latest_alias}.battery_level)"
        if latest_alias
        else f"{cp_alias}.end_battery_level"
    )
    return f"""
        (
            {energy} >= {MIN_REPORT_CHARGE_KWH}
            or (
                {cp_alias}.start_battery_level is not null
                and {end_battery_level} is not null
                and ({end_battery_level} - {cp_alias}.start_battery_level) >= 1
            )
        )
    """


def display_zone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.display_timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Shanghai")


def utc_naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc)


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def hour_start(value: datetime) -> datetime:
    return value.replace(minute=0, second=0, microsecond=0)


def add_hourly_energy(
    buckets: list[float],
    start_local: datetime,
    end_local: datetime,
    rate_kwh_per_hour: float,
    window_start: datetime,
    window_end: datetime,
) -> None:
    start = max(start_local, window_start)
    end = min(end_local, window_end)
    if end <= start:
        return

    cursor = start
    while cursor < end:
        next_hour = min(hour_start(cursor) + timedelta(hours=1), end)
        buckets[cursor.hour] += rate_kwh_per_hour * ((next_hour - cursor).total_seconds() / 3600)
        cursor = next_hour


def today_energy(car_id: int, car: dict[str, Any]) -> dict[str, Any]:
    tz = display_zone()
    now_local = datetime.now(tz)
    today_start_local = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    tomorrow_start_local = today_start_local + timedelta(days=1)
    history_start_local = today_start_local - timedelta(days=TODAY_ENERGY_HISTORY_DAYS)
    today_start_utc = utc_naive(today_start_local)
    tomorrow_start_utc = utc_naive(tomorrow_start_local)
    history_start_utc = utc_naive(history_start_local)
    now_utc = utc_naive(now_local)

    rows = fetch_all(
        """
        select
            p.date,
            p.rated_battery_range_km::float8 as rated_battery_range_km,
            p.ideal_battery_range_km::float8 as ideal_battery_range_km,
            p.battery_level,
            p.usable_battery_level,
            p.drive_id,
            p.speed,
            p.power,
            p.is_climate_on,
            st.state
        from public.positions p
        left join lateral (
            select s.state::text as state
            from public.states s
            where s.car_id = p.car_id
              and s.start_date <= p.date
              and coalesce(s.end_date, p.date) >= p.date
            order by s.start_date desc
            limit 1
        ) st on true
        where p.car_id = %s
          and p.date >= %s::timestamp
          and p.date < least(%s::timestamp, %s::timestamp)
          and (
              p.battery_level is not null
              or p.rated_battery_range_km is not null
              or p.ideal_battery_range_km is not null
          )
        order by p.date asc
        """,
        (car_id, history_start_utc, tomorrow_start_utc, now_utc + timedelta(minutes=5)),
    )

    efficiency = to_float(car.get("efficiency"))
    actual_by_hour = [0.0 for _ in range(24)]
    actual_drive_by_hour = [0.0 for _ in range(24)]
    actual_asleep_by_hour = [0.0 for _ in range(24)]
    actual_awake_by_hour = [0.0 for _ in range(24)]
    actual_unknown_by_hour = [0.0 for _ in range(24)]
    history_kwh: dict[str, list[float]] = {
        "drive": [0.0 for _ in range(24)],
        "asleep": [0.0 for _ in range(24)],
        "awake": [0.0 for _ in range(24)],
        "unknown": [0.0 for _ in range(24)],
    }
    history_hours: dict[str, list[float]] = {
        "drive": [0.0 for _ in range(24)],
        "asleep": [0.0 for _ in range(24)],
        "awake": [0.0 for _ in range(24)],
        "unknown": [0.0 for _ in range(24)],
    }

    latest_row: dict[str, Any] | None = rows[-1] if rows else None

    def range_km(row: dict[str, Any]) -> float | None:
        return to_float(row.get("rated_battery_range_km")) or to_float(row.get("ideal_battery_range_km"))

    def battery_level(row: dict[str, Any] | None) -> float | None:
        if not row:
            return None
        return to_float(row.get("battery_level")) or to_float(row.get("usable_battery_level"))

    def is_moving(row: dict[str, Any]) -> bool:
        speed = to_float(row.get("speed")) or 0
        return row.get("drive_id") is not None or speed > 1

    def bucket_key(row: dict[str, Any]) -> str:
        if is_moving(row):
            return "drive"
        state = row.get("state")
        if state == "asleep":
            return "asleep"
        if state:
            return "awake"
        return "unknown"

    def add_history(key: str, start_local: datetime, end_local: datetime, kwh: float, hours: float) -> None:
        cursor = start_local
        while cursor < end_local:
            next_hour = min(hour_start(cursor) + timedelta(hours=1), end_local)
            portion = (next_hour - cursor).total_seconds() / 3600
            if portion > 0 and hours > 0:
                history_kwh[key][cursor.hour] += kwh * (portion / hours)
                history_hours[key][cursor.hour] += portion
            cursor = next_hour

    for previous, current in zip(rows, rows[1:]):
        previous_date = previous.get("date")
        current_date = current.get("date")
        if not isinstance(previous_date, datetime) or not isinstance(current_date, datetime):
            continue

        duration_hours = (current_date - previous_date).total_seconds() / 3600
        if duration_hours <= 0 or duration_hours > MAX_TODAY_ENERGY_SEGMENT_HOURS:
            continue

        previous_range = range_km(previous)
        current_range = range_km(current)
        if not efficiency or previous_range is None or current_range is None:
            continue

        consumed_kwh = max((previous_range - current_range) * efficiency, 0)
        if consumed_kwh <= 0:
            continue

        start_local = as_utc(previous_date).astimezone(tz)
        end_local = as_utc(current_date).astimezone(tz)
        if end_local <= history_start_local or start_local >= tomorrow_start_local:
            continue

        key = bucket_key(current)
        rate = consumed_kwh / duration_hours

        if start_local < today_start_local:
            history_end = min(end_local, today_start_local)
            if history_end > start_local:
                add_history(key, max(start_local, history_start_local), history_end, consumed_kwh, duration_hours)

        if end_local > today_start_local:
            add_hourly_energy(actual_by_hour, start_local, end_local, rate, today_start_local, min(now_local, tomorrow_start_local))
            if key == "drive":
                add_hourly_energy(actual_drive_by_hour, start_local, end_local, rate, today_start_local, min(now_local, tomorrow_start_local))
            elif key == "asleep":
                add_hourly_energy(actual_asleep_by_hour, start_local, end_local, rate, today_start_local, min(now_local, tomorrow_start_local))
            elif key == "awake":
                add_hourly_energy(actual_awake_by_hour, start_local, end_local, rate, today_start_local, min(now_local, tomorrow_start_local))
            else:
                add_hourly_energy(actual_unknown_by_hour, start_local, end_local, rate, today_start_local, min(now_local, tomorrow_start_local))

    def hourly_rate(key: str, hour: int) -> float | None:
        hours = history_hours[key][hour]
        if hours >= 0.25:
            return history_kwh[key][hour] / hours
        return None

    def global_rate(*keys: str) -> float | None:
        total_kwh = sum(sum(history_kwh[key]) for key in keys)
        total_hours = sum(sum(history_hours[key]) for key in keys)
        if total_hours >= 0.5:
            return total_kwh / total_hours
        return None

    parked_global = global_rate("asleep", "awake", "unknown")
    asleep_global = global_rate("asleep") or parked_global
    awake_global = global_rate("awake") or parked_global
    unknown_global = global_rate("unknown") or parked_global
    drive_global = global_rate("drive")

    latest_state = str(car.get("current_state") or (latest_row.get("state") if latest_row else "") or "")
    latest_moving = bool(car.get("current_state") == "driving" or (latest_row and is_moving(latest_row)))
    latest_charging = bool(car.get("current_state") == "charging")
    if latest_moving:
        prediction_basis = "driving"
    elif latest_charging:
        prediction_basis = "charging"
    elif latest_state == "asleep":
        prediction_basis = "asleep"
    else:
        prediction_basis = "awake"

    predicted_drive = [0.0 for _ in range(24)]
    predicted_asleep = [0.0 for _ in range(24)]
    predicted_awake = [0.0 for _ in range(24)]
    predicted_unknown = [0.0 for _ in range(24)]

    def parked_rate(hour: int) -> tuple[str, float | None]:
        if latest_state == "asleep":
            return "asleep", hourly_rate("asleep", hour) or asleep_global
        if latest_state:
            return "awake", hourly_rate("awake", hour) or awake_global
        return "unknown", hourly_rate("unknown", hour) or unknown_global

    for hour in range(24):
        start = today_start_local + timedelta(hours=hour)
        end = start + timedelta(hours=1)
        if end <= now_local or start >= tomorrow_start_local:
            continue

        remaining_hours = (min(end, tomorrow_start_local) - max(start, now_local)).total_seconds() / 3600
        if remaining_hours <= 0:
            continue

        if latest_moving and hour == now_local.hour:
            rate = hourly_rate("drive", hour) or drive_global or hourly_rate("awake", hour) or awake_global or parked_global
            if rate:
                predicted_drive[hour] = rate * remaining_hours
            continue

        if latest_charging and hour == now_local.hour:
            continue

        key, rate = parked_rate(hour)
        if not rate:
            continue
        if key == "asleep":
            predicted_asleep[hour] = rate * remaining_hours
        elif key == "awake":
            predicted_awake[hour] = rate * remaining_hours
        else:
            predicted_unknown[hour] = rate * remaining_hours

    latest_battery_level = battery_level(latest_row) or to_float(car.get("battery_level")) or to_float(car.get("usable_battery_level"))
    latest_range_km = (range_km(latest_row) if latest_row else None) or to_float(car.get("rated_battery_range_km")) or to_float(car.get("ideal_battery_range_km"))
    kwh_per_percent = None
    if efficiency and latest_range_km and latest_battery_level and latest_battery_level > 0:
        kwh_per_percent = latest_range_km * efficiency / latest_battery_level

    battery_samples = [
        {
            "date": row["date"],
            "level": battery_level(row),
        }
        for row in rows
        if isinstance(row.get("date"), datetime) and battery_level(row) is not None
    ]

    def actual_level_at(marker_local: datetime) -> float | None:
        if not battery_samples:
            return None
        marker_utc = utc_naive(marker_local)
        level = None
        for sample in battery_samples:
            if sample["date"] <= marker_utc:
                level = sample["level"]
            else:
                break
        return level

    current_hour = now_local.hour

    def predicted_energy_until(hour: int) -> float:
        end_hour = min(max(hour, 0), 24)
        if end_hour <= current_hour:
            return 0.0
        return sum(
            predicted_drive[index] + predicted_asleep[index] + predicted_awake[index] + predicted_unknown[index]
            for index in range(current_hour, end_hour)
        )

    def predicted_level_at(hour: int) -> float | None:
        if latest_battery_level is None or hour < current_hour:
            return None
        predicted_kwh = predicted_energy_until(hour)
        if not kwh_per_percent:
            return latest_battery_level if predicted_kwh == 0 else None
        return clamp(latest_battery_level - predicted_kwh / kwh_per_percent, 0, 100)

    points = []
    for hour in range(25):
        predicted_kwh = (
            predicted_drive[hour] + predicted_asleep[hour] + predicted_awake[hour] + predicted_unknown[hour]
            if hour < 24
            else 0.0
        )
        marker_local = today_start_local + timedelta(hours=hour)
        actual_battery_level = latest_battery_level if hour == current_hour else actual_level_at(marker_local)
        if marker_local > now_local and hour != current_hour:
            actual_battery_level = None
        points.append(
            {
                "hour": hour,
                "label": f"{hour:02d}:00",
                "actual_battery_level": actual_battery_level,
                "predicted_battery_level": predicted_level_at(hour),
                "actual_kwh": actual_by_hour[hour] if hour < 24 else 0.0,
                "actual_drive_kwh": actual_drive_by_hour[hour] if hour < 24 else 0.0,
                "actual_asleep_kwh": actual_asleep_by_hour[hour] if hour < 24 else 0.0,
                "actual_awake_kwh": actual_awake_by_hour[hour] if hour < 24 else 0.0,
                "actual_unknown_kwh": actual_unknown_by_hour[hour] if hour < 24 else 0.0,
                "predicted_kwh": predicted_kwh,
                "predicted_drive_kwh": predicted_drive[hour] if hour < 24 else 0.0,
                "predicted_asleep_kwh": predicted_asleep[hour] if hour < 24 else 0.0,
                "predicted_awake_kwh": predicted_awake[hour] if hour < 24 else 0.0,
                "predicted_unknown_kwh": predicted_unknown[hour] if hour < 24 else 0.0,
            }
        )

    actual_total = sum(actual_by_hour)
    predicted_total = sum(
        item["predicted_drive_kwh"] + item["predicted_asleep_kwh"] + item["predicted_awake_kwh"] + item["predicted_unknown_kwh"]
        for item in points
    )
    source_hours = {
        "drive": sum(history_hours["drive"]),
        "asleep": sum(history_hours["asleep"]),
        "awake": sum(history_hours["awake"]),
        "unknown": sum(history_hours["unknown"]),
    }
    has_basis_samples = (
        (prediction_basis == "driving" and source_hours["drive"] >= 0.5)
        or (prediction_basis == "asleep" and source_hours["asleep"] >= 0.5)
        or (prediction_basis == "awake" and source_hours["awake"] >= 0.5)
        or (prediction_basis == "charging" and sum(source_hours.values()) >= 0.5)
    )

    return {
        "timezone": settings.display_timezone,
        "generated_at": now_local.isoformat(),
        "as_of": latest_row.get("date") if latest_row else None,
        "history_days": TODAY_ENERGY_HISTORY_DAYS,
        "state": latest_state or None,
        "prediction_basis": prediction_basis,
        "prediction_confidence": "normal" if has_basis_samples else "low",
        "current_battery_level": latest_battery_level,
        "estimated_end_battery_level": predicted_level_at(24),
        "actual_kwh": actual_total,
        "predicted_remaining_kwh": predicted_total,
        "estimated_total_kwh": actual_total + predicted_total,
        "history_hours": source_hours,
        "points": points,
    }


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


def _period(
    car_id: int,
    days: int,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, datetime | int | bool | None]:
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
    if start or end:
        first_seen_at = row["first_seen_at"]
        requested_since = datetime.combine(start, time.min) if start else first_seen_at
        requested_until = datetime.combine(end, time.max) if end else last_seen_at
        since = max(requested_since, first_seen_at)
        until = min(requested_until, last_seen_at)
        if since > until:
            raise HTTPException(status_code=404, detail="自定义周期内没有车辆位置数据")
        return {
            "days": (until.date() - since.date()).days + 1,
            "since": since,
            "until": until,
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": last_seen_at,
            "is_custom": True,
        }

    since = None if days == 0 else last_seen_at - timedelta(days=days)
    return {
        "days": days,
        "since": since,
        "until": last_seen_at,
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": last_seen_at,
        "is_custom": False,
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
    days: int = Query(default=7, ge=0, le=3650, description="0 表示全部数据"),
    start: date | None = Query(default=None, description="自定义开始日期，格式 YYYY-MM-DD"),
    end: date | None = Query(default=None, description="自定义结束日期，格式 YYYY-MM-DD"),
) -> Any:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")

    cars_by_id = {car["id"]: car for car in _cars()}
    car = cars_by_id.get(car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="未找到车辆")

    period = _period(car_id, days, start, end)
    since = period["since"]
    until = period["until"]

    drive_stats = fetch_one(
        """
        select
            count(*)::int as drive_count,
            coalesce(sum(distance), 0)::float8 as distance_km,
            coalesce(sum(duration_min), 0)::float8 as duration_min,
            avg(nullif(distance, 0))::float8 as avg_distance_km,
            max(distance)::float8 as longest_drive_km,
            max(speed_max)::float8 as max_speed_kmh,
            avg(nullif(speed_max, 0))::float8 as avg_max_speed_kmh,
            coalesce(sum(ascent), 0)::float8 as ascent_m,
            coalesce(sum(descent), 0)::float8 as descent_m,
            case
                when coalesce(sum(nullif(duration_min, 0)), 0) > 0 then
                    (sum(distance) / nullif(sum(duration_min), 0)) * 60
                else null
            end::float8 as avg_drive_speed_kmh,
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
          and d.start_date <= %s::timestamp
        """,
        (car_id, since, since, until),
    )

    charge_stats = fetch_one(
        f"""
        select
            count(*)::int as charge_count,
            coalesce(sum(cp.charge_energy_added), 0)::float8 as charge_energy_added_kwh,
            coalesce(sum(cp.charge_energy_used), 0)::float8 as charge_energy_used_kwh,
            coalesce(sum(cp.cost), 0)::float8 as cost,
            avg(cp.end_battery_level - cp.start_battery_level)::float8 as avg_soc_added_pct,
            max(cp.end_battery_level)::int as max_end_battery_level,
            avg(nullif(cp.charge_energy_added, 0))::float8 as avg_charge_energy_added_kwh,
            avg(nullif(cp.duration_min, 0))::float8 as avg_charge_duration_min,
            max(ch.max_power_kw)::float8 as max_charge_power_kw,
            avg(nullif(ch.avg_power_kw, 0))::float8 as avg_charge_power_kw,
            count(*) filter (where ch.fast_charger)::int as fast_charge_count,
            case
                when coalesce(sum(nullif(cp.charge_energy_used, 0)), 0) > 0 then
                    (sum(cp.charge_energy_added) / nullif(sum(cp.charge_energy_used), 0)) * 100
                else null
            end::float8 as charge_efficiency_pct
        from public.charging_processes cp
        left join lateral (
            select
                max(charger_power)::float8 as max_power_kw,
                avg(nullif(charger_power, 0))::float8 as avg_power_kw,
                bool_or(coalesce(fast_charger_present, false)) as fast_charger
            from public.charges
            where charging_process_id = cp.id
        ) ch on true
        where cp.car_id = %s
          and (%s::timestamp is null or cp.start_date >= %s::timestamp)
          and cp.start_date <= %s::timestamp
          and {report_charge_condition()}
        """,
        (car_id, since, since, until),
    )

    active_charge_stats = fetch_one(
        f"""
        select count(*)::int as active_charge_count
        from public.charging_processes cp
        left join lateral (
            select max(date) as latest_charge_at
            from public.charges
            where charging_process_id = cp.id
        ) ch on true
        left join lateral (
            select date as latest_seen_at
            from public.positions
            where car_id = cp.car_id
            order by date desc
            limit 1
        ) lp on true
        where cp.car_id = %s
          and (%s::timestamp is null or cp.start_date >= %s::timestamp)
          and cp.start_date <= %s::timestamp
          and {active_charge_condition()}
        """,
        (car_id, since, since, until),
    )

    lifetime = fetch_one(
        f"""
        select
            (select count(*)::int from public.drives where car_id = %s) as drive_count,
            (select coalesce(sum(distance), 0)::float8 from public.drives where car_id = %s) as distance_km,
            (select count(*)::int from public.charging_processes cp where cp.car_id = %s and {report_charge_condition()}) as charge_count,
            (select coalesce(sum(cp.charge_energy_added), 0)::float8 from public.charging_processes cp where cp.car_id = %s and {report_charge_condition()}) as charge_energy_added_kwh,
            (select min(odometer)::float8 from public.positions where car_id = %s and odometer is not null) as first_odometer_km,
            (select max(odometer)::float8 from public.positions where car_id = %s and odometer is not null) as latest_odometer_km
        """,
        (car_id, car_id, car_id, car_id, car_id, car_id),
    )

    daily = fetch_all(
        f"""
        with drive_days as (
            select
                date_trunc('day', d.start_date)::date as day,
                count(*)::int as drives,
                coalesce(sum(d.distance), 0)::float8 as distance_km,
                coalesce(sum(d.duration_min), 0)::float8 as duration_min,
                max(d.speed_max)::float8 as max_speed_kmh,
                coalesce(sum(
                    case
                        when d.distance > 0
                         and d.start_rated_range_km is not null
                         and d.end_rated_range_km is not null
                         and d.start_rated_range_km > d.end_rated_range_km
                         and car.efficiency is not null
                        then (d.start_rated_range_km - d.end_rated_range_km) * car.efficiency
                        else 0
                    end
                ), 0)::float8 as estimated_drive_kwh
            from public.drives d
            join public.cars car on car.id = d.car_id
            where d.car_id = %s
              and (%s::timestamp is null or d.start_date >= %s::timestamp)
              and d.start_date <= %s::timestamp
            group by 1
        ),
        charge_days as (
            select
                date_trunc('day', cp.start_date)::date as day,
                count(*)::int as charges,
                coalesce(sum(cp.charge_energy_added), 0)::float8 as charge_energy_added_kwh,
                coalesce(sum(cp.cost), 0)::float8 as cost
            from public.charging_processes cp
            where cp.car_id = %s
              and (%s::timestamp is null or cp.start_date >= %s::timestamp)
              and cp.start_date <= %s::timestamp
              and {report_charge_condition()}
            group by 1
        )
        select
            coalesce(d.day, c.day) as day,
            coalesce(d.drives, 0) as drives,
            coalesce(d.distance_km, 0)::float8 as distance_km,
            coalesce(d.duration_min, 0)::float8 as duration_min,
            d.max_speed_kmh,
            coalesce(d.estimated_drive_kwh, 0)::float8 as estimated_drive_kwh,
            case
                when coalesce(d.distance_km, 0) > 0 then
                    (coalesce(d.estimated_drive_kwh, 0) / nullif(d.distance_km, 0)) * 100
                else null
            end::float8 as estimated_kwh_per_100km,
            coalesce(c.charges, 0) as charges,
            coalesce(c.charge_energy_added_kwh, 0)::float8 as charge_energy_added_kwh,
            coalesce(c.cost, 0)::float8 as cost
        from drive_days d
        full outer join charge_days c using (day)
        order by day
        """,
        (car_id, since, since, until, car_id, since, since, until),
    )

    monthly = fetch_all(
        f"""
        with drive_months as (
            select
                date_trunc('month', d.start_date)::date as month,
                count(*)::int as drives,
                coalesce(sum(d.distance), 0)::float8 as distance_km,
                coalesce(sum(
                    case
                        when d.distance > 0
                         and d.start_rated_range_km is not null
                         and d.end_rated_range_km is not null
                         and d.start_rated_range_km > d.end_rated_range_km
                         and car.efficiency is not null
                        then (d.start_rated_range_km - d.end_rated_range_km) * car.efficiency
                        else 0
                    end
                ), 0)::float8 as estimated_drive_kwh
            from public.drives d
            join public.cars car on car.id = d.car_id
            where d.car_id = %s
              and (%s::timestamp is null or d.start_date >= %s::timestamp)
              and d.start_date <= %s::timestamp
            group by 1
        ),
        charge_months as (
            select
                date_trunc('month', cp.start_date)::date as month,
                count(*)::int as charges,
                coalesce(sum(cp.charge_energy_added), 0)::float8 as charge_energy_added_kwh,
                coalesce(sum(cp.charge_energy_added) filter (where not coalesce(ch.fast_charger, false)), 0)::float8 as ac_charge_energy_added_kwh,
                coalesce(sum(cp.charge_energy_added) filter (where coalesce(ch.fast_charger, false)), 0)::float8 as dc_charge_energy_added_kwh,
                coalesce(sum(cp.cost), 0)::float8 as cost
            from public.charging_processes cp
            left join lateral (
                select bool_or(coalesce(fast_charger_present, false)) as fast_charger
                from public.charges
                where charging_process_id = cp.id
            ) ch on true
            where cp.car_id = %s
              and (%s::timestamp is null or cp.start_date >= %s::timestamp)
              and cp.start_date <= %s::timestamp
              and {report_charge_condition()}
            group by 1
        )
        select
            coalesce(d.month, c.month) as month,
            coalesce(d.drives, 0) as drives,
            coalesce(d.distance_km, 0)::float8 as distance_km,
            coalesce(d.estimated_drive_kwh, 0)::float8 as estimated_drive_kwh,
            coalesce(c.charges, 0) as charges,
            coalesce(c.charge_energy_added_kwh, 0)::float8 as charge_energy_added_kwh,
            coalesce(c.ac_charge_energy_added_kwh, 0)::float8 as ac_charge_energy_added_kwh,
            coalesce(c.dc_charge_energy_added_kwh, 0)::float8 as dc_charge_energy_added_kwh,
            coalesce(c.cost, 0)::float8 as cost
        from drive_months d
        full outer join charge_months c using (month)
        order by month
        """,
        (car_id, since, since, until, car_id, since, since, until),
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
          and date <= %s::timestamp
          and battery_level is not null
        order by date_trunc('day', date), date desc
        """,
        (car_id, since, since, until),
    )

    insights = fetch_one(
        """
        with first_position as (
            select *
            from public.positions
            where car_id = %s
              and (%s::timestamp is null or date >= %s::timestamp)
              and date <= %s::timestamp
            order by date asc
            limit 1
        ),
        last_position as (
            select *
            from public.positions
            where car_id = %s
              and (%s::timestamp is null or date >= %s::timestamp)
              and date <= %s::timestamp
            order by date desc
            limit 1
        ),
        position_stats as (
            select
                avg(outside_temp)::float8 as avg_outside_temp,
                avg(inside_temp)::float8 as avg_inside_temp,
                avg(tpms_pressure_fl)::float8 as avg_tpms_pressure_fl,
                avg(tpms_pressure_fr)::float8 as avg_tpms_pressure_fr,
                avg(tpms_pressure_rl)::float8 as avg_tpms_pressure_rl,
                avg(tpms_pressure_rr)::float8 as avg_tpms_pressure_rr
            from public.positions
            where car_id = %s
              and (%s::timestamp is null or date >= %s::timestamp)
              and date <= %s::timestamp
        )
        select
            fp.date as first_sample_at,
            lp.date as latest_sample_at,
            fp.odometer::float8 as first_odometer_km,
            lp.odometer::float8 as latest_odometer_km,
            case
                when fp.odometer is not null and lp.odometer is not null
                then (lp.odometer - fp.odometer)::float8
                else null
            end as odometer_delta_km,
            fp.rated_battery_range_km::float8 as first_rated_battery_range_km,
            lp.rated_battery_range_km::float8 as latest_rated_battery_range_km,
            case
                when fp.rated_battery_range_km is not null and lp.rated_battery_range_km is not null
                then (lp.rated_battery_range_km - fp.rated_battery_range_km)::float8
                else null
            end as rated_range_delta_km,
            lp.battery_level as latest_battery_level,
            lp.usable_battery_level as latest_usable_battery_level,
            lp.outside_temp::float8 as latest_outside_temp,
            lp.inside_temp::float8 as latest_inside_temp,
            ps.avg_outside_temp,
            ps.avg_inside_temp,
            ps.avg_tpms_pressure_fl,
            ps.avg_tpms_pressure_fr,
            ps.avg_tpms_pressure_rl,
            ps.avg_tpms_pressure_rr
        from first_position fp
        cross join last_position lp
        cross join position_stats ps
        """,
        (
            car_id,
            since,
            since,
            until,
            car_id,
            since,
            since,
            until,
            car_id,
            since,
            since,
            until,
        ),
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
            end as estimated_kwh,
            case
                when d.distance > 0
                 and d.start_rated_range_km is not null
                 and d.end_rated_range_km is not null
                 and d.start_rated_range_km > d.end_rated_range_km
                 and c.efficiency is not null
                then (((d.start_rated_range_km - d.end_rated_range_km) * c.efficiency) / d.distance * 100)::float8
                else null
            end as estimated_kwh_per_100km,
            coalesce(route.route_points, '[]'::jsonb) as route_points
        from public.drives d
        join public.cars c on c.id = d.car_id
        left join public.addresses sa on sa.id = d.start_address_id
        left join public.addresses ea on ea.id = d.end_address_id
        left join public.geofences sg on sg.id = d.start_geofence_id
        left join public.geofences eg on eg.id = d.end_geofence_id
        left join lateral (
            select jsonb_agg(
                jsonb_build_object(
                    'sampled_at', sampled.date,
                    'latitude', sampled.latitude::float8,
                    'longitude', sampled.longitude::float8,
                    'speed', sampled.speed,
                    'power', sampled.power,
                    'battery_level', sampled.battery_level
                )
                order by sampled.date
            ) as route_points
            from (
                select date, latitude, longitude, speed, power, battery_level
                from (
                    select
                        p.date,
                        p.latitude,
                        p.longitude,
                        p.speed,
                        p.power,
                        p.battery_level,
                        (row_number() over (order by p.date))::int as rn,
                        (count(*) over ())::int as total
                    from public.positions p
                    where p.car_id = d.car_id
                      and (
                          p.drive_id = d.id
                          or (
                              p.date >= d.start_date
                              and p.date <= coalesce(d.end_date, d.start_date + interval '8 hours')
                          )
                      )
                      and p.latitude is not null
                      and p.longitude is not null
                ) ranked
                where total <= 160
                   or rn = 1
                   or rn = total
                   or ((rn - 1) %% greatest(1, ceil(total / 160.0)::int)) = 0
                order by date
            ) sampled
        ) route on true
        where d.car_id = %s
          and (%s::timestamp is null or d.start_date >= %s::timestamp)
          and d.start_date <= %s::timestamp
        order by d.start_date desc
        limit 12
        """,
        (car_id, since, since, until),
    )

    drive_efficiency = fetch_all(
        f"""
        select
            d.id,
            d.start_date,
            d.end_date,
            d.distance::float8 as distance_km,
            d.duration_min,
            d.speed_max,
            d.outside_temp_avg::float8 as outside_temp_avg,
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
            end as estimated_kwh,
            case
                when d.distance > 0
                 and d.start_rated_range_km is not null
                 and d.end_rated_range_km is not null
                 and d.start_rated_range_km > d.end_rated_range_km
                 and c.efficiency is not null
                then (((d.start_rated_range_km - d.end_rated_range_km) * c.efficiency) / d.distance * 100)::float8
                else null
            end as estimated_kwh_per_100km
        from public.drives d
        join public.cars c on c.id = d.car_id
        left join public.addresses sa on sa.id = d.start_address_id
        left join public.addresses ea on ea.id = d.end_address_id
        left join public.geofences sg on sg.id = d.start_geofence_id
        left join public.geofences eg on eg.id = d.end_geofence_id
        where d.car_id = %s
          and coalesce(d.distance, 0) > 0.1
          and (%s::timestamp is null or d.start_date >= %s::timestamp)
          and d.start_date <= %s::timestamp
        order by d.start_date asc
        limit 80
        """,
        (car_id, since, since, until),
    )

    charge_location = f"coalesce(nullif(g.name, ''), {address_label('a')})"
    recent_charges = fetch_all(
        f"""
        select
            cp.id,
            cp.start_date,
            cp.end_date,
            coalesce(cp.charge_energy_added::float8, latest.charge_energy_added_kwh) as charge_energy_added_kwh,
            cp.charge_energy_used::float8 as charge_energy_used_kwh,
            cp.start_battery_level,
            coalesce(cp.end_battery_level, latest.battery_level) as end_battery_level,
            case
                when cp.duration_min is not null then cp.duration_min
                when ch.latest_charge_at is not null then
                    greatest(
                        0.0,
                        floor(extract(epoch from (ch.latest_charge_at - cp.start_date)) / 60.0)
                    )::int
                else null
            end as duration_min,
            cp.outside_temp_avg::float8 as outside_temp_avg,
            cp.cost::float8 as cost,
            {charge_location} as location,
            ch.latest_charge_at,
            ch.max_power_kw,
            ch.fast_charger,
            ({active_charge_condition()})::bool as is_active,
            coalesce(charge_samples.samples, '[]'::jsonb) as samples
        from public.charging_processes cp
        left join public.addresses a on a.id = cp.address_id
        left join public.geofences g on g.id = cp.geofence_id
        left join lateral (
            select
                max(date) as latest_charge_at,
                max(charger_power)::float8 as max_power_kw,
                bool_or(coalesce(fast_charger_present, false)) as fast_charger
            from public.charges
            where charging_process_id = cp.id
        ) ch on true
        left join lateral (
            select
                charge_energy_added::float8 as charge_energy_added_kwh,
                battery_level
            from public.charges
            where charging_process_id = cp.id
            order by date desc
            limit 1
        ) latest on true
        left join lateral (
            select jsonb_agg(
                jsonb_build_object(
                    'sampled_at', sampled.date,
                    'minute', extract(epoch from (sampled.date - cp.start_date)) / 60.0,
                    'charger_power_kw', sampled.charger_power,
                    'battery_level', sampled.battery_level,
                    'charge_energy_added_kwh', sampled.charge_energy_added::float8,
                    'charger_voltage', sampled.charger_voltage,
                    'charger_actual_current', sampled.charger_actual_current
                )
                order by sampled.date
            ) as samples
            from (
                select
                    date,
                    charger_power,
                    battery_level,
                    charge_energy_added,
                    charger_voltage,
                    charger_actual_current
                from (
                    select
                        c.date,
                        c.charger_power,
                        c.battery_level,
                        c.charge_energy_added,
                        c.charger_voltage,
                        c.charger_actual_current,
                        (row_number() over (order by c.date))::int as rn,
                        (count(*) over ())::int as total
                    from public.charges c
                    where c.charging_process_id = cp.id
                ) ranked
                where total <= 160
                   or rn = 1
                   or rn = total
                   or ((rn - 1) %% greatest(1, ceil(total / 160.0)::int)) = 0
                order by date
            ) sampled
        ) charge_samples on true
        left join lateral (
            select date as latest_seen_at
            from public.positions
            where car_id = cp.car_id
            order by date desc
            limit 1
        ) lp on true
        where cp.car_id = %s
          and (%s::timestamp is null or cp.start_date >= %s::timestamp)
          and cp.start_date <= %s::timestamp
          and (
              {report_charge_condition("cp", "latest")}
              or {active_charge_condition()}
          )
        order by cp.start_date desc
        limit 12
        """,
        (car_id, since, since, until),
    )

    charge_sessions = fetch_all(
        f"""
        select
            cp.id,
            cp.start_date,
            cp.end_date,
            coalesce(cp.charge_energy_added::float8, latest.charge_energy_added_kwh) as charge_energy_added_kwh,
            cp.charge_energy_used::float8 as charge_energy_used_kwh,
            cp.start_battery_level,
            coalesce(cp.end_battery_level, latest.battery_level) as end_battery_level,
            case
                when cp.duration_min is not null then cp.duration_min
                when ch.latest_charge_at is not null then
                    greatest(
                        0.0,
                        floor(extract(epoch from (ch.latest_charge_at - cp.start_date)) / 60.0)
                    )::int
                else null
            end as duration_min,
            cp.cost::float8 as cost,
            {charge_location} as location,
            ch.latest_charge_at,
            ch.max_power_kw,
            ch.avg_power_kw,
            ch.fast_charger,
            ({active_charge_condition()})::bool as is_active
        from public.charging_processes cp
        left join public.addresses a on a.id = cp.address_id
        left join public.geofences g on g.id = cp.geofence_id
        left join lateral (
            select
                max(date) as latest_charge_at,
                max(charger_power)::float8 as max_power_kw,
                avg(nullif(charger_power, 0))::float8 as avg_power_kw,
                bool_or(coalesce(fast_charger_present, false)) as fast_charger
            from public.charges
            where charging_process_id = cp.id
        ) ch on true
        left join lateral (
            select
                charge_energy_added::float8 as charge_energy_added_kwh,
                battery_level
            from public.charges
            where charging_process_id = cp.id
            order by date desc
            limit 1
        ) latest on true
        left join lateral (
            select date as latest_seen_at
            from public.positions
            where car_id = cp.car_id
            order by date desc
            limit 1
        ) lp on true
        where cp.car_id = %s
          and (%s::timestamp is null or cp.start_date >= %s::timestamp)
          and cp.start_date <= %s::timestamp
          and (
              {report_charge_condition("cp", "latest")}
              or {active_charge_condition()}
          )
        order by cp.start_date asc
        limit 80
        """,
        (car_id, since, since, until),
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
          and d.start_date <= %s::timestamp
        group by 1
        order by visits desc, last_seen_at desc
        limit 8
        """,
        (car_id, since, since, until),
    )

    route_stats = fetch_all(
        f"""
        select
            {drive_location_start} as start_location,
            {drive_location_end} as end_location,
            count(*)::int as trips,
            coalesce(sum(d.distance), 0)::float8 as distance_km,
            avg(nullif(d.distance, 0))::float8 as avg_distance_km,
            max(d.end_date) as last_seen_at
        from public.drives d
        left join public.addresses sa on sa.id = d.start_address_id
        left join public.addresses ea on ea.id = d.end_address_id
        left join public.geofences sg on sg.id = d.start_geofence_id
        left join public.geofences eg on eg.id = d.end_geofence_id
        where d.car_id = %s
          and d.end_date is not null
          and coalesce(d.distance, 0) > 0.1
          and (%s::timestamp is null or d.start_date >= %s::timestamp)
          and d.start_date <= %s::timestamp
        group by 1, 2
        order by trips desc, distance_km desc, last_seen_at desc
        limit 10
        """,
        (car_id, since, since, until),
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
          and cp.start_date <= %s::timestamp
          and {report_charge_condition()}
        group by 1
        order by sessions desc, last_seen_at desc
        limit 8
        """,
        (car_id, since, since, until),
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
            cp.end_date,
            coalesce(cp.charge_energy_added::float8, latest.charge_energy_added_kwh) as charge_energy_added_kwh,
            cp.start_battery_level,
            coalesce(cp.end_battery_level, latest.battery_level) as end_battery_level,
            case
                when cp.duration_min is not null then cp.duration_min
                when ch.latest_charge_at is not null then
                    greatest(
                        0.0,
                        floor(extract(epoch from (ch.latest_charge_at - cp.start_date)) / 60.0)
                    )::int
                else null
            end as duration_min,
            {charge_location} as location,
            ch.latest_charge_at,
            ch.max_power_kw,
            ch.fast_charger,
            true as is_active
        from public.charging_processes cp
        left join public.addresses a on a.id = cp.address_id
        left join public.geofences g on g.id = cp.geofence_id
        left join lateral (
            select
                max(date) as latest_charge_at,
                max(charger_power)::float8 as max_power_kw,
                bool_or(coalesce(fast_charger_present, false)) as fast_charger
            from public.charges
            where charging_process_id = cp.id
        ) ch on true
        left join lateral (
            select
                charge_energy_added::float8 as charge_energy_added_kwh,
                battery_level
            from public.charges
            where charging_process_id = cp.id
            order by date desc
            limit 1
        ) latest on true
        left join lateral (
            select date as latest_seen_at
            from public.positions
            where car_id = cp.car_id
            order by date desc
            limit 1
        ) lp on true
        where cp.car_id = %s
          and {active_charge_condition()}
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
                **(active_charge_stats or {}),
            },
            "lifetime": lifetime or {},
            "daily": daily,
            "monthly": monthly,
            "today_energy": today_energy(car_id, car),
            "states": states,
            "range": range_series,
            "insights": insights or {},
            "drive_efficiency": drive_efficiency,
            "charge_sessions": charge_sessions,
            "recent_drives": recent_drives,
            "recent_charges": recent_charges,
            "locations": {
                "destinations": top_destinations,
                "charging": top_charge_locations,
                "routes": route_stats,
            },
            "updates": updates,
            "active_charge": active_charge,
        }
    )
