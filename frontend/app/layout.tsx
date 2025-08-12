import './globals.css'
import { Header } from '../components/Header'
import { AuthProvider } from '../components/auth'
import { Sora, Inter } from 'next/font/google'

const display = Sora({ subsets: ['latin'], weight: ['600','700'], variable: '--font-display' })
const sans = Inter({ subsets: ['latin'], weight: ['400','500','600'], variable: '--font-sans' })

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`}>
      <head>
        <title>Manthan — Creator Suite</title>
        <meta name="description" content="From logline to pitch pack to buyer—fast. Manthan Creator Suite." />
        <link rel="icon" href="/favicon.svg" />
        <meta property="og:title" content="Manthan — Creator Suite" />
        <meta property="og:description" content="From logline to pitch pack to buyer—fast." />
      </head>
      <body className="min-h-screen">
        <AuthProvider>
          <Header />
          <main className="max-w-6xl mx-auto p-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  )
}

