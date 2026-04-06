"use client";

import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Stuhi <span className="text-primary">Portfolio Intelligence</span>
        </Link>
        <a
          href="https://calendar.google.com/calendar/appointments/schedules/AcZssZ3ltgIqF8oF87Qnx1UC_BrtXMyR2VYLrZ8xBKX8_LlPznmL5Jdt_VQO1iljGxV-kB-QiSbLdD5e"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-primary transition-colors hover:text-primary/80"
        >
          Contact us
        </a>
      </div>
    </header>
  );
}
