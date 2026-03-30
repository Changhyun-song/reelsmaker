import type { Metadata } from "next";
import {
  ClerkProvider,
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
} from "@clerk/nextjs";
import { koKR } from "@clerk/localizations";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReelsMaker",
  description: "AI 영상 제작 파이프라인",
};

const hasClerk = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

function NavBar({ children }: { children?: React.ReactNode }) {
  return (
    <nav className="border-b border-neutral-800 px-6 py-4">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <a href="/" className="text-lg font-bold tracking-tight">
          ReelsMaker
        </a>
        <div className="flex items-center gap-4 text-sm text-neutral-400">
          <a href="/" className="hover:text-neutral-50 transition">
            Home
          </a>
          <a href="/projects" className="hover:text-neutral-50 transition">
            Projects
          </a>
          <a href="/jobs" className="hover:text-neutral-50 transition">
            Jobs
          </a>
          <a href="/ops" className="hover:text-neutral-50 transition">
            Ops
          </a>
          <a href="/status" className="hover:text-neutral-50 transition">
            Status
          </a>
          {children}
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const content = (
    <>
      <NavBar>
        {hasClerk && (
          <>
            <SignedOut>
              <SignInButton mode="modal">
                <button className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 transition">
                  로그인
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <UserButton
                appearance={{ elements: { avatarBox: "w-7 h-7" } }}
              />
            </SignedIn>
          </>
        )}
      </NavBar>
      <div className="px-6 py-4">{children}</div>
    </>
  );

  return (
    <html lang="ko">
      <body className="min-h-screen bg-neutral-950 text-neutral-50 antialiased">
        {hasClerk ? (
          <ClerkProvider localization={koKR}>{content}</ClerkProvider>
        ) : (
          content
        )}
      </body>
    </html>
  );
}
