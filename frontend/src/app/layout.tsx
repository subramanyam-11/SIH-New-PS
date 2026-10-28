import './globals.css';
import { AuthProvider } from '@/lib/auth';

export const metadata = {
  title: 'AICTE Approval Workflow Automation & Compliance Management',
  description: 'Statutory approval workflow automation and compliance monitoring platform for AICTE',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 min-h-screen text-slate-900">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
