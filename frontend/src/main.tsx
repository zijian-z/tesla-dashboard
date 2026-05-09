import React from 'react';
import ReactDOM from 'react-dom/client';
import {
  Activity,
  BatteryCharging,
  CalendarDays,
  CarFront,
  ChartNoAxesColumn,
  CircleDollarSign,
  Clock3,
  Gauge,
  MapPin,
  Moon,
  Navigation,
  PlugZap,
  RefreshCw,
  Route,
  Smartphone,
  Thermometer,
  Zap
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import './styles.css';

type Car = {
  id: number;
  name?: string | null;
  model?: string | null;
  marketing_name?: string | null;
  trim_badging?: string | null;
  exterior_color?: string | null;
  wheel_type?: string | null;
  efficiency?: number | null;
  latest_seen_at?: string | null;
  odometer?: number | null;
  battery_level?: number | null;
  usable_battery_level?: number | null;
  rated_battery_range_km?: number | null;
  ideal_battery_range_km?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  speed?: number | null;
  power?: number | null;
  outside_temp?: number | null;
  inside_temp?: number | null;
  tpms_pressure_fl?: number | null;
  tpms_pressure_fr?: number | null;
  tpms_pressure_rl?: number | null;
  tpms_pressure_rr?: number | null;
  current_state?: string | null;
  state_since?: string | null;
  software_version?: string | null;
  location_label?: string | null;
};

type DataWindow = {
  days: number;
  since?: string | null;
  until?: string | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  is_custom?: boolean;
};

type Summary = {
  drive_count?: number;
  distance_km?: number;
  duration_min?: number;
  avg_distance_km?: number | null;
  longest_drive_km?: number | null;
  max_speed_kmh?: number;
  avg_max_speed_kmh?: number;
  avg_drive_speed_kmh?: number | null;
  ascent_m?: number | null;
  descent_m?: number | null;
  estimated_drive_kwh?: number;
  estimated_kwh_per_100km?: number | null;
  charge_count?: number;
  active_charge_count?: number;
  charge_energy_added_kwh?: number;
  charge_energy_used_kwh?: number;
  cost?: number;
  avg_soc_added_pct?: number | null;
  max_end_battery_level?: number | null;
  avg_charge_energy_added_kwh?: number | null;
  avg_charge_duration_min?: number | null;
  max_charge_power_kw?: number | null;
  avg_charge_power_kw?: number | null;
  fast_charge_count?: number;
  charge_efficiency_pct?: number | null;
};

type Lifetime = {
  drive_count?: number;
  distance_km?: number;
  charge_count?: number;
  charge_energy_added_kwh?: number;
  first_odometer_km?: number | null;
  latest_odometer_km?: number | null;
};

type DayPoint = {
  day: string;
  drives: number;
  distance_km: number;
  duration_min: number;
  max_speed_kmh?: number | null;
  estimated_drive_kwh?: number | null;
  estimated_kwh_per_100km?: number | null;
  charges: number;
  charge_energy_added_kwh: number;
  cost: number;
};

type MonthPoint = {
  month: string;
  drives: number;
  distance_km: number;
  estimated_drive_kwh?: number | null;
  charges: number;
  charge_energy_added_kwh: number;
  cost: number;
};

type StatePoint = {
  state: string;
  hours: number;
};

type RangePoint = {
  day: string;
  sampled_at: string;
  battery_level?: number | null;
  usable_battery_level?: number | null;
  rated_battery_range_km?: number | null;
  ideal_battery_range_km?: number | null;
  odometer?: number | null;
};

type DriveRecord = {
  id: number;
  start_date: string;
  end_date?: string | null;
  distance_km?: number | null;
  duration_min?: number | null;
  speed_max?: number | null;
  outside_temp_avg?: number | null;
  ascent?: number | null;
  descent?: number | null;
  start_location?: string | null;
  end_location?: string | null;
  estimated_kwh?: number | null;
  estimated_kwh_per_100km?: number | null;
};

type ChargeRecord = {
  id: number;
  start_date: string;
  end_date?: string | null;
  charge_energy_added_kwh?: number | null;
  charge_energy_used_kwh?: number | null;
  start_battery_level?: number | null;
  end_battery_level?: number | null;
  duration_min?: number | null;
  cost?: number | null;
  location?: string | null;
  latest_charge_at?: string | null;
  max_power_kw?: number | null;
  avg_power_kw?: number | null;
  fast_charger?: boolean | null;
  is_active?: boolean | null;
};

type LocationRecord = {
  location: string;
  visits?: number;
  sessions?: number;
  arriving_distance_km?: number;
  charge_energy_added_kwh?: number;
  last_seen_at?: string | null;
};

type RouteRecord = {
  start_location?: string | null;
  end_location?: string | null;
  trips?: number;
  distance_km?: number;
  avg_distance_km?: number | null;
  last_seen_at?: string | null;
};

type Insights = {
  first_sample_at?: string | null;
  latest_sample_at?: string | null;
  first_odometer_km?: number | null;
  latest_odometer_km?: number | null;
  odometer_delta_km?: number | null;
  first_rated_battery_range_km?: number | null;
  latest_rated_battery_range_km?: number | null;
  rated_range_delta_km?: number | null;
  latest_battery_level?: number | null;
  latest_usable_battery_level?: number | null;
  latest_outside_temp?: number | null;
  latest_inside_temp?: number | null;
  avg_outside_temp?: number | null;
  avg_inside_temp?: number | null;
  avg_tpms_pressure_fl?: number | null;
  avg_tpms_pressure_fr?: number | null;
  avg_tpms_pressure_rl?: number | null;
  avg_tpms_pressure_rr?: number | null;
};

type UpdateRecord = {
  id: number;
  start_date: string;
  end_date?: string | null;
  version?: string | null;
};

type Dashboard = {
  car: Car;
  data_window: DataWindow;
  summary: Summary;
  lifetime: Lifetime;
  daily: DayPoint[];
  monthly: MonthPoint[];
  states: StatePoint[];
  range: RangePoint[];
  insights: Insights;
  drive_efficiency: DriveRecord[];
  charge_sessions: ChargeRecord[];
  recent_drives: DriveRecord[];
  recent_charges: ChargeRecord[];
  locations: {
    destinations: LocationRecord[];
    charging: LocationRecord[];
    routes: RouteRecord[];
  };
  updates: UpdateRecord[];
  active_charge?: ChargeRecord | null;
};

type ReportKey = 'overview' | 'trends' | 'drives' | 'charging' | 'efficiency' | 'battery' | 'locations' | 'vehicle';
type PeriodKey = '7' | '30' | '90' | '365' | '0' | 'custom';

const defaultApiBase = import.meta.env.BASE_URL === '/' ? '' : import.meta.env.BASE_URL.replace(/\/$/, '');
const API_BASE = import.meta.env.VITE_API_BASE ?? defaultApiBase;
const AUTO_REFRESH_MS = 60_000;

const ranges: Array<{ label: string; value: PeriodKey }> = [
  { label: '7天', value: '7' },
  { label: '30天', value: '30' },
  { label: '90天', value: '90' },
  { label: '一年', value: '365' },
  { label: '全部', value: '0' },
  { label: '自定义', value: 'custom' }
];

const numberFormat = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 });
const integerFormat = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 });
const currencyFormat = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  maximumFractionDigits: 0
});

const stateLabels: Record<string, string> = {
  online: '在线',
  asleep: '睡眠',
  offline: '离线',
  charging: '充电',
  driving: '行驶'
};

const stateColors: Record<string, string> = {
  online: '#0f766e',
  asleep: '#64748b',
  offline: '#b45309',
  charging: '#d83a45',
  driving: '#2563eb'
};

function n(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(value);
}

function km(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${numberFormat.format(value)} km`;
}

function kwh(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${numberFormat.format(value)} kWh`;
}

function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${integerFormat.format(value)}%`;
}

function minutes(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  if (value < 60) return `${integerFormat.format(value)} 分钟`;
  const hours = Math.floor(value / 60);
  const mins = Math.round(value % 60);
  return mins ? `${hours} 小时 ${mins} 分钟` : `${hours} 小时`;
}

function shortDate(value?: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}

function dateTime(value?: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function dateInput(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function shiftDateInput(value: string, days: number): string {
  const date = value ? new Date(`${value}T00:00:00`) : new Date();
  date.setDate(date.getDate() + days);
  return dateInput(date.toISOString());
}

function monthLabel(value?: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit' });
}

function labelState(value?: string | null): string {
  if (!value) return '未知';
  return stateLabels[value] ?? value;
}

function carTitle(car?: Car | null): string {
  if (!car) return 'Tesla';
  return car.name || car.marketing_name || `车辆 ${car.id}`;
}

function carSubtitle(car?: Car | null): string {
  if (!car) return 'TeslaMate';
  const parts = [car.marketing_name || (car.model ? `Model ${car.model}` : null), car.trim_badging, car.wheel_type].filter(Boolean);
  return parts.join(' · ') || 'TeslaMate';
}

function periodText(dataWindow?: DataWindow | null): string {
  if (!dataWindow) return '—';
  if (dataWindow.days === 0 && !dataWindow.is_custom) return '全部历史';
  if (dataWindow.since && dataWindow.until) return `${shortDate(dataWindow.since)} - ${shortDate(dataWindow.until)}`;
  return `${dataWindow.days} 天`;
}

function ratio(numerator?: number | null, denominator?: number | null): number | null {
  if (!numerator || !denominator) return null;
  return numerator / denominator;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    signal,
    headers: { Accept: 'application/json' }
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function Metric({
  icon,
  label,
  value,
  detail,
  tone = 'neutral'
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail?: string;
  tone?: 'neutral' | 'green' | 'red' | 'amber' | 'blue';
}) {
  return (
    <article className={`metric metric-${tone}`}>
      <div className="metric-icon" aria-hidden="true">
        {icon}
      </div>
      <div>
        <p className="metric-label">{label}</p>
        <strong>{value}</strong>
        {detail ? <span>{detail}</span> : null}
      </div>
    </article>
  );
}

function Section({
  title,
  icon,
  children,
  aside
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <section className="section">
      <div className="section-head">
        <h2>
          {icon}
          {title}
        </h2>
        {aside ? <div className="section-aside">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

function ReportTitle({ title, description }: { title: string; description: string }) {
  return (
    <div className="report-title">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

function App() {
  const [cars, setCars] = React.useState<Car[]>([]);
  const [carId, setCarId] = React.useState<number | null>(null);
  const [period, setPeriod] = React.useState<PeriodKey>('30');
  const [customEnd, setCustomEnd] = React.useState(() => dateInput(new Date().toISOString()));
  const [customStart, setCustomStart] = React.useState(() => shiftDateInput(dateInput(new Date().toISOString()), -6));
  const [activeReport, setActiveReport] = React.useState<ReportKey>('overview');
  const [dashboard, setDashboard] = React.useState<Dashboard | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const dashboardQuery = React.useMemo(() => {
    if (period === 'custom') {
      const params = new URLSearchParams();
      if (customStart) params.set('start', customStart);
      if (customEnd) params.set('end', customEnd);
      return params.toString();
    }
    return `days=${period}`;
  }, [customEnd, customStart, period]);

  React.useEffect(() => {
    const controller = new AbortController();
    setError(null);
    getJson<{ cars: Car[] }>('/api/cars', controller.signal)
      .then((data) => {
        setCars(data.cars);
        setCarId((current) => current ?? data.cars[0]?.id ?? null);
      })
      .catch((err: Error) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [refreshKey]);

  React.useEffect(() => {
    if (!carId) return;
    const controller = new AbortController();
    setLoading(true);
    setRefreshing(true);
    setError(null);
    getJson<Dashboard>(`/api/cars/${carId}/dashboard?${dashboardQuery}`, controller.signal)
      .then((data) => setDashboard(data))
      .catch((err: Error) => {
        if (!controller.signal.aborted) setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => controller.abort();
  }, [carId, dashboardQuery, refreshKey]);

  React.useEffect(() => {
    const timer = window.setInterval(() => {
      setRefreshKey((key) => key + 1);
    }, AUTO_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  const car = dashboard?.car ?? cars.find((item) => item.id === carId) ?? null;
  const summary = dashboard?.summary ?? {};
  const lifetime = dashboard?.lifetime ?? {};
  const insights = dashboard?.insights ?? {};
  const costPerKwh = ratio(summary.cost, summary.charge_energy_added_kwh);
  const costPer100km = summary.cost && summary.distance_km ? (summary.cost / summary.distance_km) * 100 : null;
  const distancePerDay = dashboard?.data_window.days && dashboard.data_window.days > 0 ? ratio(summary.distance_km, dashboard.data_window.days) : null;
  const chargeUsedRatio = summary.charge_energy_used_kwh && summary.charge_energy_added_kwh ? (summary.charge_energy_added_kwh / summary.charge_energy_used_kwh) * 100 : null;
  const daily = React.useMemo(
    () =>
      (dashboard?.daily ?? []).map((item) => ({
        ...item,
        label: shortDate(item.day),
        distance_km: Number(item.distance_km?.toFixed(1) ?? 0),
        charge_energy_added_kwh: Number(item.charge_energy_added_kwh?.toFixed(1) ?? 0),
        estimated_drive_kwh: item.estimated_drive_kwh === null || item.estimated_drive_kwh === undefined ? null : Number(item.estimated_drive_kwh.toFixed(1)),
        estimated_kwh_per_100km:
          item.estimated_kwh_per_100km === null || item.estimated_kwh_per_100km === undefined ? null : Number(item.estimated_kwh_per_100km.toFixed(1))
      })),
    [dashboard]
  );
  const monthly = React.useMemo(
    () =>
      (dashboard?.monthly ?? []).map((item) => ({
        ...item,
        label: monthLabel(item.month),
        distance_km: Number(item.distance_km?.toFixed(1) ?? 0),
        charge_energy_added_kwh: Number(item.charge_energy_added_kwh?.toFixed(1) ?? 0),
        estimated_drive_kwh: item.estimated_drive_kwh === null || item.estimated_drive_kwh === undefined ? null : Number(item.estimated_drive_kwh.toFixed(1))
      })),
    [dashboard]
  );
  const rangeSeries = React.useMemo(
    () =>
      (dashboard?.range ?? []).map((item) => ({
        ...item,
        label: shortDate(item.day),
        battery_level: item.battery_level ?? null,
        rated_battery_range_km: item.rated_battery_range_km ? Number(item.rated_battery_range_km.toFixed(1)) : null
      })),
    [dashboard]
  );
  const states = React.useMemo(
    () =>
      (dashboard?.states ?? [])
        .filter((item) => item.hours > 0.01)
        .map((item) => ({
          ...item,
          label: labelState(item.state),
          value: Number(item.hours.toFixed(1)),
          fill: stateColors[item.state] ?? '#475569'
        })),
    [dashboard]
  );
  const driveEfficiency = React.useMemo(
    () =>
      (dashboard?.drive_efficiency ?? []).map((item) => ({
        ...item,
        label: shortDate(item.start_date),
        distance_km: item.distance_km === null || item.distance_km === undefined ? null : Number(item.distance_km.toFixed(1)),
        estimated_kwh_per_100km:
          item.estimated_kwh_per_100km === null || item.estimated_kwh_per_100km === undefined ? null : Number(item.estimated_kwh_per_100km.toFixed(1))
      })),
    [dashboard]
  );
  const chargeSessions = React.useMemo(
    () =>
      (dashboard?.charge_sessions ?? []).map((item) => ({
        ...item,
        label: shortDate(item.start_date),
        charge_energy_added_kwh:
          item.charge_energy_added_kwh === null || item.charge_energy_added_kwh === undefined ? null : Number(item.charge_energy_added_kwh.toFixed(1)),
        max_power_kw: item.max_power_kw === null || item.max_power_kw === undefined ? null : Number(item.max_power_kw.toFixed(0))
      })),
    [dashboard]
  );
  const reportItems: Array<{ key: ReportKey; label: string; icon: React.ReactNode }> = [
    { key: 'overview', label: '概览', icon: <Activity size={17} /> },
    { key: 'trends', label: '趋势', icon: <ChartNoAxesColumn size={17} /> },
    { key: 'drives', label: '行程', icon: <Navigation size={17} /> },
    { key: 'charging', label: '充电', icon: <PlugZap size={17} /> },
    { key: 'efficiency', label: '效率', icon: <Zap size={17} /> },
    { key: 'battery', label: '电池', icon: <BatteryCharging size={17} /> },
    { key: 'locations', label: '地点', icon: <MapPin size={17} /> },
    { key: 'vehicle', label: '车辆', icon: <CarFront size={17} /> }
  ];
  const reportDescriptions: Record<ReportKey, string> = {
    overview: '车辆当前状态与关键统计',
    trends: '行驶、充电、电量与在线状态变化',
    drives: '最近行程与行驶效率',
    charging: '充电会话、功率和地点',
    efficiency: '能耗、速度、成本和充电效率',
    battery: '电量、续航、温度与胎压观测',
    locations: '常到地点与充电地点',
    vehicle: '车辆硬件、环境和软件信息'
  };

  const renderDailyTrend = () => (
    <Section title="日趋势" icon={<ChartNoAxesColumn size={18} />} aside={dashboard?.data_window.since ? `${shortDate(dashboard.data_window.since)} 起` : '全部'}>
      {daily.length ? (
        <div className="chart chart-tall">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={daily} margin={{ top: 10, right: 10, bottom: 0, left: -18 }}>
              <defs>
                <linearGradient id="distanceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0f766e" stopOpacity={0.28} />
                  <stop offset="95%" stopColor="#0f766e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={18} />
              <YAxis tickLine={false} axisLine={false} width={42} />
              <Tooltip formatter={(value, name) => [n(Number(value)), name === 'distance_km' ? '行驶 km' : '充电 kWh']} labelFormatter={(label) => `日期 ${label}`} />
              <Area type="monotone" dataKey="distance_km" stroke="#0f766e" fill="url(#distanceFill)" strokeWidth={2} name="行驶 km" />
              <Bar dataKey="charge_energy_added_kwh" fill="#d83a45" radius={[4, 4, 0, 0]} name="充电 kWh" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Empty text="当前周期没有行程或充电记录" />
      )}
    </Section>
  );

  const renderRangeTrend = () => (
    <Section title="电量与续航" icon={<BatteryCharging size={18} />}>
      {rangeSeries.length ? (
        <div className="chart chart-tall">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rangeSeries} margin={{ top: 10, right: 10, bottom: 0, left: -18 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={18} />
              <YAxis yAxisId="left" tickLine={false} axisLine={false} width={36} domain={[0, 100]} />
              <YAxis yAxisId="right" orientation="right" tickLine={false} axisLine={false} width={44} />
              <Tooltip formatter={(value, name) => [n(Number(value)), name === 'battery_level' ? '电量 %' : '续航 km']} />
              <Legend iconType="circle" />
              <Line yAxisId="left" type="monotone" dataKey="battery_level" stroke="#d83a45" strokeWidth={2} dot={false} name="电量 %" />
              <Line yAxisId="right" type="monotone" dataKey="rated_battery_range_km" stroke="#2563eb" strokeWidth={2} dot={false} name="额定续航 km" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Empty text="暂无电量记录" />
      )}
    </Section>
  );

  const renderStateChart = () => (
    <Section title="状态占比" icon={<Moon size={18} />}>
      {states.length ? (
        <div className="state-block">
          <div className="chart chart-pie">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={states} dataKey="value" nameKey="label" innerRadius={48} outerRadius={76} paddingAngle={2}>
                  {states.map((entry) => (
                    <Cell key={entry.state} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`${n(Number(value))} 小时`, '时长']} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="state-list">
            {states.map((item) => (
              <div key={item.state}>
                <span style={{ background: item.fill }} />
                <strong>{item.label}</strong>
                <em>{n(item.value)} 小时</em>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <Empty text="暂无状态记录" />
      )}
    </Section>
  );

  const renderMonthlyChart = () => (
    <Section title="月汇总" icon={<CalendarDays size={18} />}>
      {monthly.length ? (
        <div className="chart chart-compact">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthly} margin={{ top: 10, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={8} />
              <YAxis tickLine={false} axisLine={false} width={40} />
              <Tooltip formatter={(value, name) => [n(Number(value)), name === 'distance_km' ? '行驶 km' : '充电 kWh']} />
              <Bar dataKey="distance_km" fill="#0f766e" radius={[4, 4, 0, 0]} name="行驶 km" />
              <Bar dataKey="charge_energy_added_kwh" fill="#d83a45" radius={[4, 4, 0, 0]} name="充电 kWh" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Empty text="暂无月度数据" />
      )}
    </Section>
  );

  const renderEfficiencyTrend = () => (
    <Section title="单次行程效率" icon={<Zap size={18} />} aside={`${driveEfficiency.length} 次有效行程`}>
      {driveEfficiency.length ? (
        <div className="chart chart-tall">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={driveEfficiency} margin={{ top: 10, right: 10, bottom: 0, left: -18 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={18} />
              <YAxis yAxisId="left" tickLine={false} axisLine={false} width={42} />
              <YAxis yAxisId="right" orientation="right" tickLine={false} axisLine={false} width={44} />
              <Tooltip formatter={(value, name) => [n(Number(value)), name === 'distance_km' ? '里程 km' : 'kWh/100km']} />
              <Legend iconType="circle" />
              <Bar yAxisId="left" dataKey="distance_km" fill="#171a20" radius={[4, 4, 0, 0]} name="里程 km" />
              <Line yAxisId="right" type="monotone" dataKey="estimated_kwh_per_100km" stroke="#3e6ae1" strokeWidth={2} dot={false} name="kWh/100km" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Empty text="当前周期没有可计算能耗的行程" />
      )}
    </Section>
  );

  const renderChargePowerTrend = () => (
    <Section title="充电功率与电量" icon={<BatteryCharging size={18} />} aside={`${chargeSessions.length} 次会话`}>
      {chargeSessions.length ? (
        <div className="chart chart-tall">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chargeSessions} margin={{ top: 10, right: 10, bottom: 0, left: -18 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={18} />
              <YAxis yAxisId="left" tickLine={false} axisLine={false} width={42} />
              <YAxis yAxisId="right" orientation="right" tickLine={false} axisLine={false} width={44} />
              <Tooltip formatter={(value, name) => [n(Number(value)), name === 'max_power_kw' ? '峰值 kW' : '充电 kWh']} />
              <Legend iconType="circle" />
              <Bar yAxisId="left" dataKey="charge_energy_added_kwh" fill="#171a20" radius={[4, 4, 0, 0]} name="充电 kWh" />
              <Line yAxisId="right" type="monotone" dataKey="max_power_kw" stroke="#3e6ae1" strokeWidth={2} dot={false} name="峰值 kW" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Empty text="当前周期没有充电功率记录" />
      )}
    </Section>
  );

  const renderDriveList = () => (
    <Section title="最近行程" icon={<Navigation size={18} />}>
      {dashboard?.recent_drives.length ? (
        <div className="record-list">
          {dashboard.recent_drives.map((drive) => (
            <article className="record" key={drive.id}>
              <div className="record-time">
                <Route size={16} />
                <span>{dateTime(drive.start_date)}</span>
              </div>
              <h3>{drive.start_location ?? '未知地点'} → {drive.end_location ?? '未知地点'}</h3>
              <div className="record-facts">
                <span>{km(drive.distance_km)}</span>
                <span>{minutes(drive.duration_min)}</span>
                <span>{drive.speed_max ? `${n(drive.speed_max, 0)} km/h` : '—'}</span>
                <span>{drive.estimated_kwh ? kwh(drive.estimated_kwh) : '—'}</span>
                <span>{drive.estimated_kwh_per_100km ? `${n(drive.estimated_kwh_per_100km)} kWh/100km` : '—'}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty text="当前周期没有行程" />
      )}
    </Section>
  );

  const renderChargeList = () => (
    <Section title="最近充电" icon={<PlugZap size={18} />}>
      {dashboard?.recent_charges.length ? (
        <div className="record-list">
          {dashboard.recent_charges.map((charge) => (
            <article className="record" key={charge.id}>
              <div className="record-time">
                <PlugZap size={16} />
                <span>{dateTime(charge.start_date)}</span>
                {charge.is_active ? <b>进行中</b> : null}
              </div>
              <h3>{charge.location ?? '未知地点'}</h3>
              <div className="record-facts">
                <span>{kwh(charge.charge_energy_added_kwh)}</span>
                <span>{percent(charge.start_battery_level)} → {percent(charge.end_battery_level)}</span>
                <span>{minutes(charge.duration_min)}</span>
                <span>{charge.max_power_kw ? `${n(charge.max_power_kw, 0)} kW` : '—'}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty text="当前周期没有充电" />
      )}
    </Section>
  );

  const renderLocationReports = () => (
    <>
      <Section title="高频路线" icon={<Route size={18} />}>
        {dashboard?.locations.routes.length ? (
          <div className="location-list location-list-wide">
            {dashboard.locations.routes.map((item) => (
              <div className="location-row" key={`${item.start_location}-${item.end_location}-${item.last_seen_at}`}>
                <strong>{item.start_location ?? '未知地点'} → {item.end_location ?? '未知地点'}</strong>
                <span>{item.trips ?? 0} 次 · 总计 {km(item.distance_km)} · 单次 {km(item.avg_distance_km)} · {dateTime(item.last_seen_at)}</span>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="暂无路线统计" />
        )}
      </Section>

      <section className="split-grid">
        <Section title="常到地点" icon={<MapPin size={18} />}>
          {dashboard?.locations.destinations.length ? (
            <div className="location-list">
              {dashboard.locations.destinations.map((item) => (
                <div className="location-row" key={`${item.location}-${item.last_seen_at}`}>
                  <strong>{item.location}</strong>
                  <span>{item.visits ?? 0} 次 · {km(item.arriving_distance_km)} · {dateTime(item.last_seen_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <Empty text="暂无地点统计" />
          )}
        </Section>

        <Section title="充电地点" icon={<Zap size={18} />}>
          {dashboard?.locations.charging.length ? (
            <div className="location-list">
              {dashboard.locations.charging.map((item) => (
                <div className="location-row" key={`${item.location}-${item.last_seen_at}`}>
                  <strong>{item.location}</strong>
                  <span>{item.sessions ?? 0} 次 · {kwh(item.charge_energy_added_kwh)} · {dateTime(item.last_seen_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <Empty text="暂无充电地点统计" />
          )}
        </Section>
      </section>
    </>
  );

  const renderVehicleMetrics = () => (
    <section className="bottom-grid">
      <Metric
        icon={<Thermometer size={20} />}
        label="车外温度"
        value={car?.outside_temp === null || car?.outside_temp === undefined ? '—' : `${n(car.outside_temp)} °C`}
        detail={car?.inside_temp === null || car?.inside_temp === undefined ? undefined : `车内 ${n(car.inside_temp)} °C`}
      />
      <Metric
        icon={<Gauge size={20} />}
        label="胎压"
        value={[car?.tpms_pressure_fl, car?.tpms_pressure_fr, car?.tpms_pressure_rl, car?.tpms_pressure_rr].some(Boolean) ? `${n(car?.tpms_pressure_fl)} / ${n(car?.tpms_pressure_fr)} bar` : '—'}
        detail={[car?.tpms_pressure_rl, car?.tpms_pressure_rr].some(Boolean) ? `${n(car?.tpms_pressure_rl)} / ${n(car?.tpms_pressure_rr)} bar` : undefined}
      />
      <Metric icon={<Smartphone size={20} />} label="软件版本" value={car?.software_version ?? '—'} detail={dashboard?.updates[0] ? dateTime(dashboard.updates[0].start_date) : undefined} />
      <Metric icon={<Clock3 size={20} />} label="数据窗口" value={periodText(dashboard?.data_window)} detail={`${dateTime(dashboard?.data_window.first_seen_at)} 起`} />
    </section>
  );

  const renderBatteryReport = () => (
    <>
      <section className="metrics-grid metrics-grid-compact">
        <Metric icon={<BatteryCharging size={20} />} label="当前电量" value={percent(insights.latest_battery_level ?? car?.battery_level)} detail={`可用 ${percent(insights.latest_usable_battery_level ?? car?.usable_battery_level)}`} />
        <Metric icon={<Gauge size={20} />} label="额定续航变化" value={km(insights.rated_range_delta_km)} detail={`${km(insights.first_rated_battery_range_km)} → ${km(insights.latest_rated_battery_range_km)}`} />
        <Metric icon={<Thermometer size={20} />} label="周期均温" value={insights.avg_outside_temp === null || insights.avg_outside_temp === undefined ? '—' : `${n(insights.avg_outside_temp)} °C`} detail={insights.avg_inside_temp === null || insights.avg_inside_temp === undefined ? undefined : `车内 ${n(insights.avg_inside_temp)} °C`} />
      </section>
      <section className="split-grid">
        {renderRangeTrend()}
        {renderStateChart()}
      </section>
      {renderVehicleMetrics()}
    </>
  );

  const renderCurrentReport = () => {
    if (activeReport === 'overview') {
      return (
        <>
          <section className="status-band">
            <div className="status-main">
              <div className={`status-pill state-${car?.current_state ?? 'unknown'}`}>
                <Activity size={16} />
                {labelState(car?.current_state)}
              </div>
              <h2>{percent(car?.battery_level)}</h2>
              <p>{km(car?.rated_battery_range_km)} 额定续航</p>
            </div>
            <div className="status-detail">
              <div>
                <span>里程表</span>
                <strong>{km(car?.odometer)}</strong>
              </div>
              <div>
                <span>位置</span>
                <strong>{car?.location_label ?? '—'}</strong>
              </div>
              <div>
                <span>更新</span>
                <strong>{dateTime(car?.latest_seen_at)}</strong>
              </div>
            </div>
          </section>

          {dashboard?.active_charge ? (
            <section className="active-charge">
              <PlugZap size={18} />
              <div>
                <strong>正在充电</strong>
                <span>{dashboard.active_charge.location ?? '未知地点'} · {kwh(dashboard.active_charge.charge_energy_added_kwh)} · {dashboard.active_charge.max_power_kw ? `${n(dashboard.active_charge.max_power_kw, 0)} kW` : '功率待更新'}</span>
              </div>
            </section>
          ) : null}

          <section className="metrics-grid" aria-label="核心指标">
            <Metric icon={<Route size={20} />} label="周期里程" value={km(summary.distance_km)} detail={`${summary.drive_count ?? 0} 次行程`} tone="green" />
            <Metric icon={<PlugZap size={20} />} label="充电电量" value={kwh(summary.charge_energy_added_kwh)} detail={`${summary.charge_count ?? 0} 次充电`} tone="red" />
            <Metric icon={<Zap size={20} />} label="估算能耗" value={summary.estimated_kwh_per_100km ? `${n(summary.estimated_kwh_per_100km)} kWh/100km` : '—'} detail={kwh(summary.estimated_drive_kwh)} tone="amber" />
            <Metric icon={<Gauge size={20} />} label="最高车速" value={summary.max_speed_kmh ? `${n(summary.max_speed_kmh, 0)} km/h` : '—'} detail={minutes(summary.duration_min)} tone="blue" />
            <Metric icon={<CalendarDays size={20} />} label="累计里程" value={km(lifetime.latest_odometer_km)} detail={`${integerFormat.format(lifetime.drive_count ?? 0)} 次记录行程`} />
            <Metric icon={<CircleDollarSign size={20} />} label="充电费用" value={summary.cost ? currencyFormat.format(summary.cost) : '—'} detail={summary.avg_soc_added_pct ? `平均 +${n(summary.avg_soc_added_pct, 0)}%` : undefined} />
            <Metric icon={<Clock3 size={20} />} label="日均里程" value={km(distancePerDay)} detail={periodText(dashboard?.data_window)} />
            <Metric icon={<BatteryCharging size={20} />} label="峰值充电功率" value={summary.max_charge_power_kw ? `${n(summary.max_charge_power_kw, 0)} kW` : '—'} detail={summary.fast_charge_count ? `${summary.fast_charge_count} 次快充` : undefined} />
          </section>
        </>
      );
    }

    if (activeReport === 'trends') {
      return (
        <>
          {renderDailyTrend()}
          <section className="split-grid">
            {renderRangeTrend()}
            {renderStateChart()}
          </section>
          {renderMonthlyChart()}
        </>
      );
    }

    if (activeReport === 'drives') {
      return (
        <>
          <section className="metrics-grid metrics-grid-compact">
            <Metric icon={<Route size={20} />} label="周期里程" value={km(summary.distance_km)} detail={`${summary.drive_count ?? 0} 次行程`} tone="green" />
            <Metric icon={<Clock3 size={20} />} label="行驶时长" value={minutes(summary.duration_min)} detail={summary.avg_max_speed_kmh ? `平均最高 ${n(summary.avg_max_speed_kmh, 0)} km/h` : undefined} />
            <Metric icon={<Zap size={20} />} label="估算能耗" value={summary.estimated_kwh_per_100km ? `${n(summary.estimated_kwh_per_100km)} kWh/100km` : '—'} detail={kwh(summary.estimated_drive_kwh)} tone="amber" />
            <Metric icon={<Navigation size={20} />} label="最长行程" value={km(summary.longest_drive_km)} detail={summary.avg_distance_km ? `平均 ${km(summary.avg_distance_km)}` : undefined} />
            <Metric icon={<Gauge size={20} />} label="平均车速" value={summary.avg_drive_speed_kmh ? `${n(summary.avg_drive_speed_kmh, 0)} km/h` : '—'} detail={summary.max_speed_kmh ? `最高 ${n(summary.max_speed_kmh, 0)} km/h` : undefined} />
            <Metric icon={<Activity size={20} />} label="海拔累计" value={summary.ascent_m ? `${n(summary.ascent_m, 0)} m` : '—'} detail={summary.descent_m ? `下降 ${n(summary.descent_m, 0)} m` : undefined} />
          </section>
          {renderEfficiencyTrend()}
          {renderDriveList()}
        </>
      );
    }

    if (activeReport === 'charging') {
      return (
        <>
          {dashboard?.active_charge ? (
            <section className="active-charge">
              <PlugZap size={18} />
              <div>
                <strong>正在充电</strong>
                <span>{dashboard.active_charge.location ?? '未知地点'} · {kwh(dashboard.active_charge.charge_energy_added_kwh)} · {minutes(dashboard.active_charge.duration_min)}</span>
              </div>
            </section>
          ) : null}
          <section className="metrics-grid metrics-grid-compact">
            <Metric icon={<PlugZap size={20} />} label="充电电量" value={kwh(summary.charge_energy_added_kwh)} detail={`${summary.charge_count ?? 0} 次充电`} tone="red" />
            <Metric icon={<CircleDollarSign size={20} />} label="充电费用" value={summary.cost ? currencyFormat.format(summary.cost) : '—'} detail={summary.avg_soc_added_pct ? `平均 +${n(summary.avg_soc_added_pct, 0)}%` : undefined} />
            <Metric icon={<BatteryCharging size={20} />} label="最高充至" value={percent(summary.max_end_battery_level)} detail={summary.active_charge_count ? `${summary.active_charge_count} 个会话进行中` : undefined} />
            <Metric icon={<Gauge size={20} />} label="峰值功率" value={summary.max_charge_power_kw ? `${n(summary.max_charge_power_kw, 0)} kW` : '—'} detail={summary.avg_charge_power_kw ? `平均 ${n(summary.avg_charge_power_kw, 0)} kW` : undefined} />
            <Metric icon={<Clock3 size={20} />} label="平均时长" value={minutes(summary.avg_charge_duration_min)} detail={summary.avg_charge_energy_added_kwh ? `平均 ${kwh(summary.avg_charge_energy_added_kwh)}` : undefined} />
            <Metric icon={<Activity size={20} />} label="充电转化" value={chargeUsedRatio ? `${n(chargeUsedRatio, 0)}%` : '—'} detail={summary.charge_efficiency_pct ? `会话 ${n(summary.charge_efficiency_pct, 0)}%` : undefined} />
          </section>
          {renderChargePowerTrend()}
          {renderChargeList()}
        </>
      );
    }

    if (activeReport === 'efficiency') {
      return (
        <>
          <section className="metrics-grid metrics-grid-compact">
            <Metric icon={<Zap size={20} />} label="行驶能耗" value={summary.estimated_kwh_per_100km ? `${n(summary.estimated_kwh_per_100km)} kWh/100km` : '—'} detail={kwh(summary.estimated_drive_kwh)} tone="amber" />
            <Metric icon={<CircleDollarSign size={20} />} label="每百公里费用" value={costPer100km ? currencyFormat.format(costPer100km) : '—'} detail={costPerKwh ? `${currencyFormat.format(costPerKwh)}/kWh` : undefined} />
            <Metric icon={<Clock3 size={20} />} label="日均里程" value={km(distancePerDay)} detail={periodText(dashboard?.data_window)} />
          </section>
          {renderEfficiencyTrend()}
          {renderDailyTrend()}
        </>
      );
    }

    if (activeReport === 'battery') {
      return renderBatteryReport();
    }

    if (activeReport === 'locations') {
      return renderLocationReports();
    }

    return (
      <>
        <section className="status-band status-band-vehicle">
          <div className="status-main">
            <div className={`status-pill state-${car?.current_state ?? 'unknown'}`}>
              <CarFront size={16} />
              {carTitle(car)}
            </div>
            <h2>{km(car?.odometer)}</h2>
            <p>{carSubtitle(car)}</p>
          </div>
          <div className="status-detail">
            <div>
              <span>当前位置</span>
              <strong>{car?.location_label ?? '—'}</strong>
            </div>
            <div>
              <span>软件版本</span>
              <strong>{car?.software_version ?? '—'}</strong>
            </div>
            <div>
              <span>最近更新</span>
              <strong>{dateTime(car?.latest_seen_at)}</strong>
            </div>
          </div>
        </section>
        {renderVehicleMetrics()}
      </>
    );
  };

  return (
    <div className="app app-layout">
      <aside className="sidebar">
        <div className="brand sidebar-brand">
          <div className="brand-mark">
            <CarFront size={22} />
          </div>
          <div>
            <h1>{carTitle(car)}</h1>
            <p>{carSubtitle(car)}</p>
          </div>
        </div>

        <div className="sidebar-status">
          <div className={`status-pill state-${car?.current_state ?? 'unknown'}`}>
            <Activity size={15} />
            {labelState(car?.current_state)}
          </div>
          <strong>{percent(car?.battery_level)}</strong>
          <span>{km(car?.rated_battery_range_km)} · {dateTime(car?.latest_seen_at)}</span>
        </div>

        <nav className="side-nav" aria-label="报表菜单">
          {reportItems.map((item) => (
            <button key={item.key} type="button" className={activeReport === item.key ? 'active' : ''} onClick={() => setActiveReport(item.key)}>
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-controls">
          <label className="select-wrap">
            <span>车辆</span>
            <select value={carId ?? ''} onChange={(event) => setCarId(Number(event.target.value))}>
              {cars.map((item) => (
                <option value={item.id} key={item.id}>
                  {carTitle(item)}
                </option>
              ))}
            </select>
          </label>

          <span className="control-label">周期</span>
          <div className="range-tabs" role="tablist" aria-label="统计周期">
            {ranges.map((item) => (
              <button type="button" role="tab" aria-selected={period === item.value} className={period === item.value ? 'active' : ''} key={item.value} onClick={() => setPeriod(item.value)}>
                {item.label}
              </button>
            ))}
          </div>

          {period === 'custom' ? (
            <div className="custom-period">
              <label>
                <span>开始</span>
                <input type="date" value={customStart} max={customEnd || undefined} onChange={(event) => setCustomStart(event.target.value)} />
              </label>
              <label>
                <span>结束</span>
                <input type="date" value={customEnd} min={customStart || undefined} onChange={(event) => setCustomEnd(event.target.value)} />
              </label>
            </div>
          ) : null}

          <button className="refresh-button" type="button" onClick={() => setRefreshKey((key) => key + 1)}>
            <RefreshCw size={17} className={refreshing ? 'spin' : ''} />
            刷新
          </button>
        </div>
      </aside>

      <div className="content-shell">
        <div className="range-tabs" role="tablist" aria-label="统计周期">
          {reportItems.map((item) => (
            <button
              type="button"
              role="tab"
              aria-selected={activeReport === item.key}
              className={activeReport === item.key ? 'active' : ''}
              key={item.key}
              onClick={() => setActiveReport(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <main>
          <ReportTitle title={reportItems.find((item) => item.key === activeReport)?.label ?? '报表'} description={reportDescriptions[activeReport]} />
          {error ? <div className="alert">{error}</div> : null}

          {loading && !dashboard ? <div className="loading">加载中</div> : renderCurrentReport()}
        </main>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
