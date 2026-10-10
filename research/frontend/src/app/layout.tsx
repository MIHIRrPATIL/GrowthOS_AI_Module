import type { Metadata } from 'next';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';
import { CartProvider } from '../context/CartContext';
import { GrowthOSProvider } from '../context/GrowthOSProvider';
import { Navbar } from '../components/Navbar';
import { CartDrawer } from '../components/CartDrawer';
import { QAOverlay } from '../components/QAOverlay';

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-jakarta',
  display: 'swap'
});

export const metadata: Metadata = {
  title: "Domino's Pizza — Hot & Fresh Delivery | Powered by GrowthOS",
  description: "Order Domino's Pizzas online with hand-tossed crust, authentic Cheese Burst, and 20-minute delivery. Instrumented with GrowthOS Behavioral Intelligence.",
  keywords: ["dominos pizza", "order pizza online", "growthos", "cheese burst", "pizza delivery"]
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${jakarta.variable} font-sans bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col selection:bg-red-500 selection:text-white`}>
        <GrowthOSProvider>
          <CartProvider>
            <Navbar />
            <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
              {children}
            </main>
            <CartDrawer />
            <QAOverlay />
          </CartProvider>
        </GrowthOSProvider>
      </body>
    </html>
  );
}
