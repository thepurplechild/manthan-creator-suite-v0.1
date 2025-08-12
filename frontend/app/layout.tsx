import './globals.css'
import { AuthProvider } from '../components/auth'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head />
      <body className="min-h-screen bg-gradient-to-b from-neutral-950 to-neutral-900 text-neutral-100">
        <div className="max-w-6xl mx-auto p-6">
          <AuthProvider>{children}</AuthProvider>
        </div>
      </body>
    </html>
  )
}
