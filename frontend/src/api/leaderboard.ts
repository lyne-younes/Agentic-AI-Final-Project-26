import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { LeaderboardEntry } from "./types";

export const leaderboardKeys = {
  all: ["leaderboard"] as const,
};

/** Every quiz across the student's courses with its attempts; the page derives the rest. */
export function useLeaderboard() {
  return useQuery({
    queryKey: leaderboardKeys.all,
    queryFn: () => apiFetch<LeaderboardEntry[]>("/leaderboard"),
  });
}
