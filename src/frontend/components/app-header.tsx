"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLogout } from "@/lib/hooks";
import { clearSubscriptionId, getSubscriptionId } from "@/lib/subscription";

export function AppHeader() {
  const router = useRouter();
  const logoutMutation = useLogout();
  const isLoggedIn = typeof window !== "undefined" && !!getSubscriptionId();

  async function handleLogout() {
    try {
      await logoutMutation.mutateAsync();
    } catch {
      // proceed with local cleanup even if API fails
    }
    clearSubscriptionId();
    router.replace("/");
  }

  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Stuhi <span className="text-primary">Portfolio Intelligence</span>
        </Link>
        <div className="flex items-center gap-3">
          <a
            href="https://calendar.google.com/calendar/appointments/schedules/AcZssZ3ltgIqF8oF87Qnx1UC_BrtXMyR2VYLrZ8xBKX8_LlPznmL5Jdt_VQO1iljGxV-kB-QiSbLdD5e"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-primary transition-colors hover:text-primary/80"
          >
            Contact us
          </a>
          {isLoggedIn && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleLogout}
              disabled={logoutMutation.isPending}
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
