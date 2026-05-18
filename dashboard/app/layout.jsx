import "./globals.css";

export const metadata = {
  title: "KTX Vacancy Control Dashboard",
  description: "KTX route vacancy analytics dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
