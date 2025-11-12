"use client";
import React from "react";

export default function ContactForm() {
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const name = (data.get("name") || "").toString();
    const email = (data.get("email") || "").toString();
    const organization = (data.get("organization") || "").toString();

    // Gather lightweight marketing context
    const url = typeof window !== "undefined" ? new URL(window.location.href) : null;
    const params = url ? Object.fromEntries(url.searchParams.entries()) : {} as Record<string, string>;
    const marketing = {
      utm_source: params["utm_source"] ?? "",
      utm_medium: params["utm_medium"] ?? "",
      utm_campaign: params["utm_campaign"] ?? "",
      utm_term: params["utm_term"] ?? "",
      utm_content: params["utm_content"] ?? "",
      referrer: typeof document !== "undefined" ? document.referrer : "",
      user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "",
      page_path: url ? url.pathname + url.search : "",
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone ?? "",
    };

    try {
      const res = await fetch("/api/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, organization, marketing }),
      });

      if (!res.ok) {
        console.error("Lead submit failed", await res.text());
        return;
      }

      // Optional: clear form or show a toast
      form.reset();
      const toast = document.getElementById("toast");
      if (toast) {
        toast.textContent = "Thanks! We'll be in touch."; 
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 3000);
      } else {
        console.log("Thanks! We'll be in touch.");
      }
    } catch (err) {
      console.error("Network error submitting lead", err);
    }
  };

  return (
    <form className="mt-8 grid sm:grid-cols-3 gap-3" onSubmit={onSubmit}>
      <input
        type="text"
        placeholder="Full name"
        name="name"
        required
        className="rounded-xl bg-slate-800/60 ring-1 ring-slate-700 px-4 py-3 placeholder:text-slate-500 focus:outline-none focus:ring-emerald-500"
      />
      <input
        type="email"
        placeholder="Work email"
        name="email"
        required
        className="rounded-xl bg-slate-800/60 ring-1 ring-slate-700 px-4 py-3 placeholder:text-slate-500 focus:outline-none focus:ring-emerald-500"
      />
      <input
        type="text"
        placeholder="Organization (optional)"
        name="organization"
        className="rounded-xl bg-slate-800/60 ring-1 ring-slate-700 px-4 py-3 placeholder:text-slate-500 focus:outline-none focus:ring-emerald-500 sm:col-span-3"
      />
      <button className="rounded-xl px-6 py-3 font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950">
        Request access
      </button>
    </form>
  );
}
