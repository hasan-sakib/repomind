import { z } from "zod";

export const registerSchema = z.object({
  full_name: z.string().min(1, "Enter your name").max(200),
  email: z.email("Enter a valid email address"),
  password: z.string().min(8, "Must be at least 8 characters").max(128),
});

export const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

export const forgotPasswordSchema = z.object({
  email: z.email("Enter a valid email address"),
});

export const resetPasswordSchema = z.object({
  new_password: z.string().min(8, "Must be at least 8 characters").max(128),
});
