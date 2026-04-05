"use client";

import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-4xl items-center px-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Stuhi <span className="text-primary">Portfolio Intelligence</span>
        </Link>
      </div>
    </header>
  );
}
