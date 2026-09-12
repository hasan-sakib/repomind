import { describe, expect, it } from "vitest";

import { forgotPasswordSchema, loginSchema, registerSchema, resetPasswordSchema } from "./auth";

describe("registerSchema", () => {
  it("accepts a valid registration", () => {
    const result = registerSchema.safeParse({
      full_name: "Ada Lovelace",
      email: "ada@example.com",
      password: "correct-horse-battery",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an empty name", () => {
    const result = registerSchema.safeParse({
      full_name: "",
      email: "ada@example.com",
      password: "correct-horse-battery",
    });
    expect(result.success).toBe(false);
  });

  it("rejects an invalid email", () => {
    const result = registerSchema.safeParse({
      full_name: "Ada Lovelace",
      email: "not-an-email",
      password: "correct-horse-battery",
    });
    expect(result.success).toBe(false);
  });

  it("rejects a password under 8 characters", () => {
    const result = registerSchema.safeParse({
      full_name: "Ada Lovelace",
      email: "ada@example.com",
      password: "short",
    });
    expect(result.success).toBe(false);
  });
});

describe("loginSchema", () => {
  it("accepts a valid login", () => {
    expect(
      loginSchema.safeParse({ email: "ada@example.com", password: "anything" }).success,
    ).toBe(true);
  });

  it("rejects an empty password (login has no minimum length — that's not our rule to enforce)", () => {
    expect(loginSchema.safeParse({ email: "ada@example.com", password: "" }).success).toBe(false);
  });

  it("rejects an invalid email", () => {
    expect(loginSchema.safeParse({ email: "nope", password: "anything" }).success).toBe(false);
  });
});

describe("forgotPasswordSchema", () => {
  it("accepts a valid email", () => {
    expect(forgotPasswordSchema.safeParse({ email: "ada@example.com" }).success).toBe(true);
  });

  it("rejects an invalid email", () => {
    expect(forgotPasswordSchema.safeParse({ email: "nope" }).success).toBe(false);
  });
});

describe("resetPasswordSchema", () => {
  it("accepts a strong-enough new password", () => {
    expect(resetPasswordSchema.safeParse({ new_password: "correct-horse-battery" }).success).toBe(
      true,
    );
  });

  it("rejects a new password under 8 characters", () => {
    expect(resetPasswordSchema.safeParse({ new_password: "short" }).success).toBe(false);
  });
});
