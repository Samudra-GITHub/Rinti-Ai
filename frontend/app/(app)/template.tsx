"use client";

import { motion } from "framer-motion";

// A template remounts on every navigation, which gives each page a short,
// restrained entrance. (Reduced motion is handled by MotionConfig.)
export default function AppTemplate({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      className="h-full"
    >
      {children}
    </motion.div>
  );
}
