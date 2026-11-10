import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], display: 'swap', variable: '--font-sans' });

export const metadata: Metadata = {
  title: 'SentinelFlow — Financial Crime & AML Intelligence Workstation',
  description: 'Institutional-grade AML surveillance, transactional topology analysis, and case intelligence workstation',
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon.ico' },
    ],
    shortcut: '/favicon.ico',
    apple: '/favicon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#080A08] text-[#F2F4EF] min-h-screen antialiased selection:bg-[#B7F34A]/20 selection:text-[#B7F34A]`}>
        {children}
      </body>
    </html>
  );
}
