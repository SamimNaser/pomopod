import {
  startTransition,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from "react";

// Lucide Icons
import {
  Check,
  Copy,
  MoonStar,
  Pause,
  Play,
  RotateCcw,
  Settings2,
  SunMedium,
} from "lucide-react";
import { DynamicIcon } from "lucide-react/dynamic";

// ShadCN components
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button";
import { Dock, DockIcon } from "@/components/ui/dock";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { cn } from "@/lib/utils";

type SessionId = "focus" | "shortBreak" | "longBreak";
type ThemeMode = "light" | "dark";
type SpaceId = "personal" | "study" | "coding";

type TimerSettings = {
  focus: number;
  shortBreak: number;
  longBreak: number;
  longBreakAfter: number;
};

const THEME_STORAGE_KEY = "pomopod-theme";
const TIMER_SETTINGS_STORAGE_KEY = "pomopod-timer-settings";
const ROOM_CODE = "eur-towers-museums-personal";
const MILLISECONDS_PER_SECOND = 1000;
const MILLISECONDS_PER_MINUTE = 60 * MILLISECONDS_PER_SECOND;
const TIMER_TICK_MS = 100; // How often the countdown loop updates.
const DEFAULT_TIMER_SETTINGS: TimerSettings = {
  focus: 30,
  shortBreak: 5,
  longBreak: 15,
  longBreakAfter: 4,
};

// Timer mode options shown above the main countdown.
const sessions: Array<{
  id: SessionId;
  label: string;
}> = [
  { id: "focus", label: "Focus" },
  { id: "shortBreak", label: "Short Break" },
  { id: "longBreak", label: "Long Break" },
];

// Dock spaces swap the heading and context copy for the timer.
const spaces = [
  {
    id: "personal",
    label: "Personal",
    icon: "user-round",
  },
  {
    id: "coding",
    label: "Coding",
    icon: "code",
  },
  {
    id: "study",
    label: "Study",
    icon: "book-open-text",
  },
] as const;

function getInitialTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }

  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);

  if (storedTheme === "light" || storedTheme === "dark") {
    return storedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function getInitialTimerSettings(): TimerSettings {
  if (typeof window === "undefined") {
    return DEFAULT_TIMER_SETTINGS;
  }

  const storedSettings = window.localStorage.getItem(
    TIMER_SETTINGS_STORAGE_KEY,
  );

  if (!storedSettings) {
    return DEFAULT_TIMER_SETTINGS;
  }

  try {
    const parsedSettings = JSON.parse(storedSettings) as Partial<TimerSettings>;

    return {
      focus:
        typeof parsedSettings.focus === "number"
          ? Math.min(600, Math.max(1, parsedSettings.focus))
          : DEFAULT_TIMER_SETTINGS.focus,
      shortBreak:
        typeof parsedSettings.shortBreak === "number"
          ? parsedSettings.shortBreak
          : DEFAULT_TIMER_SETTINGS.shortBreak,
      longBreak:
        typeof parsedSettings.longBreak === "number"
          ? parsedSettings.longBreak
          : DEFAULT_TIMER_SETTINGS.longBreak,
      longBreakAfter:
        typeof parsedSettings.longBreakAfter === "number"
          ? Math.min(8, Math.max(2, parsedSettings.longBreakAfter))
          : DEFAULT_TIMER_SETTINGS.longBreakAfter,
    };
  } catch {
    return DEFAULT_TIMER_SETTINGS;
  }
}

function padTimeUnit(value: number) {
  return String(value).padStart(2, "0");
}

function getTimeParts(totalMilliseconds: number) {
  const totalSeconds = Math.ceil(
    Math.max(totalMilliseconds, 0) / MILLISECONDS_PER_SECOND,
  );
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds / 60) % 60);
  const seconds = totalSeconds % 60;

  return {
    hours: padTimeUnit(hours),
    minutes: padTimeUnit(minutes),
    seconds: padTimeUnit(seconds),
  };
}

function getSessionLength(session: SessionId, settings: TimerSettings) {
  if (session === "focus") {
    return settings.focus;
  }

  if (session === "shortBreak") {
    return settings.shortBreak;
  }

  return settings.longBreak;
}

export function PomodoroWorkspace() {
  // Core workspace state.
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [activeSession, setActiveSession] = useState<SessionId>("focus");
  const [activeSpace, setActiveSpace] = useState<SpaceId>("coding");
  const [completedFocusRounds, setCompletedFocusRounds] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [timerSettings, setTimerSettings] = useState<TimerSettings>(
    getInitialTimerSettings,
  );
  const [timeLeft, setTimeLeft] = useState(
    () => getInitialTimerSettings().focus * MILLISECONDS_PER_MINUTE,
  );
  const [isRoomCodeCopied, setIsRoomCodeCopied] = useState(false);
  const timeLeftRef = useRef(timeLeft);

  const currentSessionLength = getSessionLength(activeSession, timerSettings);
  const currentSessionLengthInMs =
    currentSessionLength * MILLISECONDS_PER_MINUTE;
  const activeSpaceMeta =
    spaces.find((space) => space.id === activeSpace) ?? spaces[0];

  useEffect(() => {
    timeLeftRef.current = timeLeft;
  }, [timeLeft]);

  // Manual switches pause the timer, while completed sessions can auto-start the next mode.
  const switchSession = (
    session: SessionId,
    settings = timerSettings,
    options?: {
      autoStart?: boolean;
    },
  ) => {
    const nextTime =
      getSessionLength(session, settings) * MILLISECONDS_PER_MINUTE;

    setActiveSession(session);
    setIsRunning(options?.autoStart ?? false);
    timeLeftRef.current = nextTime;
    setTimeLeft(nextTime);
  };

  const handleTimerSettingChange = (
    setting: keyof TimerSettings,
    value: number,
  ) => {
    const nextSettings = {
      ...timerSettings,
      [setting]: value,
    };

    setTimerSettings(nextSettings);

    if (
      (setting === "focus" ||
        setting === "shortBreak" ||
        setting === "longBreak") &&
      activeSession === setting
    ) {
      const nextTime = value * MILLISECONDS_PER_MINUTE;

      setIsRunning(false);
      timeLeftRef.current = nextTime;
      setTimeLeft(nextTime);
    }
  };

  // Room code copied to clipboard
  const handleCopyRoomCode = async () => {
    try {
      await navigator.clipboard.writeText(ROOM_CODE);
      setIsRoomCodeCopied(true);

      window.setTimeout(() => {
        setIsRoomCodeCopied(false);
      }, 2000);
    } catch {
      setIsRoomCodeCopied(false);
    }
  };

  // When a focus round ends, move into the next break. Break sessions always return to focus.
  const handleSessionComplete = useEffectEvent(() => {
    if (activeSession === "focus") {
      const nextRounds = completedFocusRounds + 1;
      const nextSession =
        nextRounds % timerSettings.longBreakAfter === 0
          ? "longBreak"
          : "shortBreak";

      setCompletedFocusRounds(nextRounds);
      switchSession(nextSession, timerSettings, { autoStart: true });

      return;
    }

    switchSession("focus", timerSettings, { autoStart: true });
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem(
      TIMER_SETTINGS_STORAGE_KEY,
      JSON.stringify(timerSettings),
    );
  }, [timerSettings]);

  // Run the countdown loop in milliseconds while the timer is active.
  useEffect(() => {
    if (!isRunning) {
      return;
    }

    let lastTick = window.performance.now();

    const timer = window.setInterval(() => {
      const now = window.performance.now();
      const elapsed = now - lastTick;
      lastTick = now;

      const nextTime = Math.max(0, timeLeftRef.current - elapsed);
      timeLeftRef.current = nextTime;
      setTimeLeft(nextTime);

      if (nextTime <= 0) {
        window.clearInterval(timer);
        handleSessionComplete();
      }
    }, TIMER_TICK_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [activeSession, isRunning]);

  const progressWidth =
    ((currentSessionLengthInMs - timeLeft) / currentSessionLengthInMs) * 100;
  const { hours, minutes, seconds } = getTimeParts(timeLeft);

  return (
    <div className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex min-h-svh w-full max-w-480 items-center justify-center overflow-hidden p-3 sm:p-4 lg:p-5 min-[1800px]:max-w-640">
        <section className="relative max-h-312 min-h-168 w-full overflow-hidden rounded-[2rem] border border-border/70 bg-card shadow-2xl">
          <div className="relative flex h-full min-h-168 flex-col p-4 sm:p-5 lg:p-6">
            {/* Header with branding and the settings sheet trigger. */}
            <header className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.24em] text-muted-foreground">
                  Pomopod
                </p>
                <h1 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">
                  Pomodoro Workspace
                </h1>
              </div>

              <div className="flex items-start gap-3">
                {/* Settings sheet trigger and side panel content. */}
                <Sheet>
                  <SheetTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      aria-label="Open pomodoro settings"
                      className="rounded-full bg-background/80 backdrop-blur"
                    >
                      <Settings2 />
                    </Button>
                  </SheetTrigger>

                  <SheetContent className="w-full sm:max-w-md">
                    <SheetHeader>
                      <SheetTitle className="font-semibold text-3xl mt-10">
                        Settings
                      </SheetTitle>
                      <SheetDescription>
                        Adjust focus and break lengths, then switch between
                        light and dark mode.
                      </SheetDescription>
                    </SheetHeader>

                    {/* Settings */}
                    <div className="space-y-6 px-4 pb-6">
                      <section className="rounded-3xl border border-border bg-card p-5">
                        {/* Theme toggle  */}
                        <div className="flex items-center justify-between gap-4">
                          <div>
                            <h3 className="font-medium">Appearance</h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                              Dark mode / Light mode
                            </p>
                          </div>

                          <div className="flex items-center gap-3">
                            <SunMedium className="size-4 text-muted-foreground" />
                            <Switch
                              checked={theme === "dark"}
                              onCheckedChange={(checked) => {
                                setTheme(checked ? "dark" : "light");
                              }}
                              aria-label="Toggle dark mode"
                            />
                            <MoonStar className="size-4 text-muted-foreground" />
                          </div>
                        </div>
                      </section>

                      <section className="rounded-3xl border border-border bg-card p-5">
                        <div className="space-y-5">
                          {/* Focus controls  */}
                          <div>
                            <div className="flex items-center justify-between gap-4">
                              <div>
                                <h3 className="font-medium">Focus timer</h3>
                                <p className="mt-1 text-sm text-muted-foreground w-8/10">
                                  How long a focus session should run.
                                </p>
                              </div>

                              <span className="shrink-0 whitespace-nowrap rounded-full border border-border bg-muted px-3 py-1 text-sm font-medium">
                                {timerSettings.focus} min
                              </span>
                            </div>

                            <Slider
                              className="mt-4"
                              min={1}
                              max={Math.cbrt(600)}
                              step={0.001}
                              value={[Math.cbrt(timerSettings.focus)]}
                              onValueChange={([value]) => {
                                handleTimerSettingChange(
                                  "focus",
                                  Math.round(Math.pow(value, 3)),
                                );
                              }}
                            />
                          </div>

                          {/* Short Break controls  */}
                          <div>
                            <div className="flex items-center justify-between gap-4">
                              <div>
                                <h3 className="font-medium">Short break</h3>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  Quick reset after a focus round.
                                </p>
                              </div>

                              <span className="shrink-0 whitespace-nowrap rounded-full border border-border bg-muted px-3 py-1 text-sm font-medium">
                                {timerSettings.shortBreak} min
                              </span>
                            </div>

                            <Slider
                              className="mt-4"
                              min={1}
                              max={Math.cbrt(120)}
                              step={0.001}
                              value={[Math.cbrt(timerSettings.shortBreak)]}
                              onValueChange={([value]) => {
                                handleTimerSettingChange(
                                  "shortBreak",
                                  Math.round(Math.pow(value, 3)),
                                );
                              }}
                            />
                          </div>

                          {/* Long Break controls  */}
                          <div>
                            <div className="flex items-center justify-between gap-4">
                              <div>
                                <h3 className="font-medium">Long break</h3>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  Longer recovery after four focus rounds.
                                </p>
                              </div>

                              <span className="shrink-0 whitespace-nowrap rounded-full border border-border bg-muted px-3 py-1 text-sm font-medium">
                                {timerSettings.longBreak} min
                              </span>
                            </div>

                            <Slider
                              className="mt-4"
                              min={1}
                              max={Math.cbrt(300)}
                              step={0.001}
                              value={[Math.cbrt(timerSettings.longBreak)]}
                              onValueChange={([value]) => {
                                handleTimerSettingChange(
                                  "longBreak",
                                  Math.round(Math.pow(value, 3)),
                                );
                              }}
                            />
                          </div>

                          {/* Long Break trigger controls  */}
                          <div>
                            <div className="flex items-center justify-between gap-4">
                              <div>
                                <h3 className="font-medium">
                                  Long break trigger
                                </h3>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  Choose how many focus sessions happen before a
                                  long break.
                                </p>
                              </div>

                              <span className="shrink-0 whitespace-nowrap rounded-full border border-border bg-muted px-3 py-1 text-sm font-medium">
                                {timerSettings.longBreakAfter} sessions
                              </span>
                            </div>

                            <Slider
                              className="mt-4"
                              min={1}
                              max={Math.cbrt(25)}
                              step={0.001}
                              value={[Math.cbrt(timerSettings.longBreakAfter)]}
                              onValueChange={([value]) => {
                                handleTimerSettingChange(
                                  "longBreakAfter",
                                  Math.round(Math.pow(value, 3)),
                                );
                              }}
                            />
                          </div>
                        </div>
                      </section>
                    </div>
                  </SheetContent>
                </Sheet>
              </div>
            </header>

            {/* Main timer presentation and session controls. */}
            <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center gap-5 py-5 sm:py-6 min-[1800px]:max-w-336">
              {/* Active space label and timer context. */}
              <div className="mt-10 w-full max-w-5xl text-center min-[1800px]:max-w-6xl">
                <h2 className="mt-4 text-balance text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
                  {activeSpaceMeta.label}
                </h2>
                <p className="mx-auto mt-2 max-w-2xl text-pretty text-sm leading-6 text-muted-foreground sm:text-base">
                  Code that communicates its purpose is very important.
                </p>

                {/* Session mode switcher. */}
                <div className="mt-6 flex flex-wrap justify-center gap-3">
                  {sessions.map((session) => (
                    <Button
                      key={session.id}
                      variant={
                        session.id === activeSession ? "default" : "outline"
                      }
                      className="rounded-full px-5"
                      onClick={() => {
                        switchSession(session.id);
                      }}
                    >
                      {session.label}
                    </Button>
                  ))}
                </div>

                {/* Countdown readout. */}
                <div className="mt-6 flex items-start justify-center text-[clamp(4rem,14vw,9rem)] font-semibold leading-none tracking-[-0.06em] tabular-nums">
                  {Number.parseInt(hours) > 0 && (
                    <>
                      <span>{hours}</span>
                      <span className="relative -top-[0.1em] mx-[0.04em]">
                        {":"}
                      </span>
                    </>
                  )}
                  <span>{minutes}</span>
                  <span className="relative -top-[0.1em] mx-[0.04em]">
                    {":"}
                  </span>
                  <span>{seconds}</span>
                </div>

                {/* Inline progress bar. */}
                <div className="mx-auto mt-6 max-w-lg rounded-full border border-border bg-background/80 p-2 backdrop-blur">
                  <div className="h-2 rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-[width]"
                      style={{
                        width: `${Number.isFinite(progressWidth) ? progressWidth : 0}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Primary timer actions. */}
                <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                  <Button
                    size="lg"
                    className="rounded-full px-6"
                    onClick={() => {
                      setIsRunning((current) => !current);
                    }}
                  >
                    {isRunning ? <Pause /> : <Play />}
                    {isRunning ? "Pause" : "Start"}
                  </Button>

                  <Button
                    size="lg"
                    variant="outline"
                    className="rounded-full px-6"
                    onClick={() => {
                      setIsRunning(false);
                      timeLeftRef.current = currentSessionLengthInMs;
                      setTimeLeft(currentSessionLengthInMs);
                    }}
                  >
                    <RotateCcw />
                    Reset
                  </Button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                {/* Room code details  */}
                <div className="flex items-center gap-2 rounded-full border border-border bg-background/80 px-3 py-2 backdrop-blur">
                  <span>{ROOM_CODE}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    className="rounded-full text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                    onClick={() => {
                      void handleCopyRoomCode();
                    }}
                  >
                    {isRoomCodeCopied ? <Check /> : <Copy />}
                  </Button>
                </div>
              </div>
            </div>

            {/* Footer . */}
            <footer className="mt-auto flex flex-col gap-3 pt-4 md:flex-row md:items-end md:justify-between">
              {/* Round summary card. */}
              <div className="w-full max-w-xs rounded-3xl border border-border bg-background/80 p-3.5 backdrop-blur md:w-auto">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                  Session flow
                </p>
                <p className="mt-1.5 text-base font-semibold">
                  {completedFocusRounds} rounds completed
                </p>
              </div>

              {/* Space switcher dock. */}
              <div className="ml-auto flex flex-col items-center justify-center gap-2">
                <p className="rounded-full border border-border bg-background/80 px-4 py-2 text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground backdrop-blur">
                  Switch spaces
                </p>

                <TooltipProvider>
                  <Dock
                    direction="middle"
                    className="mt-0 self-end border-border bg-background/80"
                    iconSize={42}
                    iconMagnification={58}
                  >
                    {spaces.map(({ id, label, icon }) => {
                      const isActive = activeSpace === id;

                      return (
                        <DockIcon key={id}>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <button
                                type="button"
                                aria-label={`Switch to ${label} space`}
                                className={cn(
                                  buttonVariants({
                                    variant: "ghost",
                                    size: "icon",
                                  }),
                                  "size-12 rounded-full border border-transparent p-0",
                                )}
                                onClick={() => {
                                  startTransition(() => {
                                    setActiveSpace(id as SpaceId);
                                  });
                                }}
                              >
                                <span
                                  className={cn(
                                    "flex size-10 items-center justify-center rounded-full transition-colors",
                                    isActive &&
                                      "bg-accent text-accent-foreground shadow-sm",
                                  )}
                                >
                                  {/* <Icon className="size-4" /> */}
                                  <DynamicIcon name={icon} className="size-4" />
                                </span>
                              </button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{label}</p>
                            </TooltipContent>
                          </Tooltip>
                        </DockIcon>
                      );
                    })}
                  </Dock>
                </TooltipProvider>
              </div>
            </footer>
          </div>
        </section>
      </div>
    </div>
  );
}
