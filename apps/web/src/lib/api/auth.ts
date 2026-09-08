import { apiFetch } from "@/lib/api-client";
import type { MeResponse, User } from "@/lib/types";

export interface AuthResponse {
  user: User;
}

export function register(input: {
  email: string;
  password: string;
  full_name: string;
}): Promise<AuthResponse> {
  return apiFetch("/api/v1/auth/register", { method: "POST", body: JSON.stringify(input) });
}

export function login(input: { email: string; password: string }): Promise<AuthResponse> {
  return apiFetch("/api/v1/auth/login", { method: "POST", body: JSON.stringify(input) });
}

export function logout(): Promise<void> {
  return apiFetch("/api/v1/auth/logout", { method: "POST" });
}

export function getMe(): Promise<MeResponse> {
  return apiFetch("/api/v1/auth/me");
}

export function requestPasswordReset(email: string): Promise<void> {
  return apiFetch("/api/v1/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function confirmPasswordReset(input: {
  token: string;
  new_password: string;
}): Promise<void> {
  return apiFetch("/api/v1/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function requestEmailVerification(): Promise<void> {
  return apiFetch("/api/v1/auth/email/verify/request", { method: "POST" });
}

export function confirmEmailVerification(token: string): Promise<User> {
  return apiFetch("/api/v1/auth/email/verify/confirm", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}
