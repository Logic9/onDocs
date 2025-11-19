import "./globals.css";

export const metadata = {
  title: "onDocs",
  description: "100% Offline, Edge AI Document Analyzer",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
