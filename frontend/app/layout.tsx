import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const archivo = Archivo({ subsets: ["latin"], variable: "--font-archivo" });
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Exam Paper Predictor",
  description:
    "Analyzes past exam papers and predicts the next one, with honest probabilities.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${archivo.variable} ${plexMono.variable}`}>
      <body>
        <header className="masthead">
          <div className="masthead-inner">
            <span className="masthead-title">
              <Link href="/">Exam Paper Predictor</Link>
            </span>
            <nav className="nav-links" aria-label="Main">
              <Link className="nav-plain" href="/#features">
                Features
              </Link>
              <Link className="nav-plain" href="/#how">
                How it works
              </Link>
              <Link className="btn small" href="/dashboard">
                Dashboard
              </Link>
            </nav>
          </div>
        </header>
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
