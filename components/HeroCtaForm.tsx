"use client";
import React from "react";

export default function HeroCtaForm() {
  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
  };

  return (
    <form
      id="cta"
      action="#"
      onSubmit={onSubmit}
      className="mt-8 flex flex-col sm:flex-row gap-3"
    >
      <input
        type="email"
        required
        placeholder="Work email"
        className="flex-1 rounded-xl bg-slate-800/60 ring-1 ring-slate-700 px-4 py-3 placeholder:text-slate-500 focus:outline-none focus:ring-emerald-500"
      />
      <button className="rounded-xl px-6 py-3 font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950">
        Request demo
      </button>
    </form>
  );
}
