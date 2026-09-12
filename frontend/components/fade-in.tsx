"use client";

import { motion } from "framer-motion";

/** Wraps content that replaces a loading skeleton, so it settles in rather
 * than popping in abruptly once data arrives. */
export function FadeIn({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
