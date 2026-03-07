import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CareCompare MVP",
  description: "Healthcare cost transparency and benefits matching MVP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
