import HeroCtaForm from "@/components/HeroCtaForm";
import ContactForm from "@/components/ContactForm";

export default function QrieLanding() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Nav */}
      <header className="sticky top-0 backdrop-blur supports-[backdrop-filter]:bg-slate-950/60 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-2xl bg-emerald-400/10 ring-1 ring-emerald-400/40 flex items-center justify-center">
              <span className="text-emerald-300 font-black">q</span>
            </div>
            <span className="font-semibold tracking-wide">qrie</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm text-slate-300">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#how" className="hover:text-white">How it works</a>
            <a href="#policies" className="hover:text-white">Policies</a>
            <a href="/onboarding" className="hover:text-white">Onboarding</a>
            <a href="#contact" className="hover:text-white">Contact</a>
          </nav>
          <div className="flex items-center gap-3">
            <a href="#cta" className="rounded-xl px-4 py-2 text-sm font-medium ring-1 ring-slate-700 hover:bg-slate-800">Sign in</a>
            <a href="#cta" className="rounded-xl px-4 py-2 text-sm font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950">Get early access</a>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-400/10 via-transparent to-transparent" />
        <div className="max-w-7xl mx-auto px-6 py-20 lg:py-28 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-4xl sm:text-5xl font-black tracking-tight leading-tight">
              CNAPP built for <span className="text-emerald-400">on‑prem</span> and <span className="text-emerald-400">regulated</span> cloud
            </h1>
            <p className="mt-6 text-slate-300 text-lg leading-relaxed">
              qrie gives you real‑time inventory, open‑resource detection, and a transparent compliance engine you can edit. Deploy in your environment. Keep data in your boundary. No black boxes.
            </p>
            <HeroCtaForm />
            <p className="mt-3 text-xs text-slate-400">By requesting access you agree to our privacy policy.</p>
            <div className="mt-10 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs text-slate-400">
              <div className="rounded-xl border border-slate-800 p-3">On‑prem & air‑gapped</div>
              <div className="rounded-xl border border-slate-800 p-3">Customer‑editable policies</div>
              <div className="rounded-xl border border-slate-800 p-3">Real‑time findings DB</div>
              <div className="rounded-xl border border-slate-800 p-3">License control & SSO</div>
            </div>
          </div>
          <div className="relative">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-2 shadow-2xl">
              <div className="rounded-xl overflow-hidden">
                <video className="w-full h-full" controls poster="https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1920&auto=format&fit=crop">
                  <source src="/splash.mp4" type="video/mp4" />
                </video>
              </div>
              <div className="p-4 text-sm text-slate-300">60‑second demo: inventory → open resources → compliance run</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-2xl font-bold">Why qrie</h2>
          <div className="mt-8 grid md:grid-cols-3 gap-6">
            {[
              {t:"Deploy where you run", d:"Fully on‑prem or your cloud account. Ideal for public sector, healthcare, defense, and any org that can’t ship metadata to third‑party SaaS."},
              {t:"Transparent policy engine", d:"20 managed policies at launch, +60 in month 5. See every rule, edit parameters, and build your own (Python/YAML)."},
              {t:"Actionable from day one", d:"Slack/Email export, CSV, and basic assignment so teams can own and fix issues immediately."},
            ].map((f,i)=> (
              <div key={i} className="rounded-2xl p-6 border border-slate-800 bg-slate-900">
                <h3 className="font-semibold text-slate-100">{f.t}</h3>
                <p className="mt-2 text-slate-300 text-sm leading-relaxed">{f.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="py-20 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-2xl font-bold">How it works</h2>
          <ol className="mt-8 grid md:grid-cols-3 gap-6 list-decimal list-inside">
            <li className="rounded-2xl p-6 border border-slate-800 bg-slate-900">
              <h4 className="font-semibold">Inventory</h4>
              <p className="mt-2 text-sm text-slate-300">Scanner lists resources by account, streams findings to your DB.</p>
            </li>
            <li className="rounded-2xl p-6 border border-slate-800 bg-slate-900">
              <h4 className="font-semibold">Open resources</h4>
              <p className="mt-2 text-sm text-slate-300">Continuous detection (EventBridge triggers) flags world‑accessible assets.</p>
            </li>
            <li className="rounded-2xl p-6 border border-slate-800 bg-slate-900">
              <h4 className="font-semibold">Compliance</h4>
              <p className="mt-2 text-sm text-slate-300">Describe → evaluate policies. Tune rules, tag scopes, export to tickets.</p>
            </li>
          </ol>
        </div>
      </section>

      {/* Policies */}
      <section id="policies" className="py-20 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-2xl font-bold">Policy coverage</h2>
          <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
            {['S3','EC2','IAM','RDS','VPC','EKS','ECR','CloudTrail'].map((k,i)=> (
              <div key={i} className="rounded-xl p-4 border border-slate-800 bg-slate-900 flex items-center justify-between">
                <span>{k}</span>
                <span className="text-emerald-300/80">Managed • Custom</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 border-t border-slate-800" id="contact">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold">See qrie in action</h2>
          <p className="mt-3 text-slate-300">Get a 15‑minute walkthrough and a sandbox environment.
          </p>
          <ContactForm />
          <p className="mt-3 text-xs text-slate-500">We’ll never sell your data. Period.</p>
        </div>
      </section>

      <footer className="py-10 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6 text-sm text-slate-400 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <p>© {new Date().getFullYear()} qrie. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <a href="#" className="hover:text-white">Privacy</a>
            <a href="#" className="hover:text-white">Terms</a>
            <a href="#" className="hover:text-white">Security</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
