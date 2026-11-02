import type { Metadata } from "next";

import { AdminApp } from "@/components/AdminApp";

export const metadata: Metadata = {
  title: "Админ",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      follow: false,
      noimageindex: true,
    },
  },
};

export default function AdminPage() {
  return <AdminApp />;
}
