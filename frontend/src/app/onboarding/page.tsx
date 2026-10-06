"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function OnboardingPage() {
  const [displayName, setDisplayName] = useState("");
  const [about, setAbout] = useState("");
  const [editAvatar, setEditAvatar] = useState("/avatars/avatar1.svg");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ 
          display_name: displayName,
          about: about || null,
          avatar_url: editAvatar 
        }),
      });
      
      if (!res.ok) {
          const errData = await res.json().catch(()=>({}));
          throw new Error(errData.detail || "Failed to create profile");
      }
      
      router.push("/");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--surface)] px-4">
      <div className="w-full max-w-md bg-[var(--background)] p-8 rounded-2xl shadow-xl border border-[var(--border)]">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold">Set up your profile</h1>
          <p className="text-[var(--text-muted)] mt-2">
            This is how you'll appear to your contacts
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
                 <div className="flex flex-col items-center justify-center mb-6">
                    <label className="block text-sm font-medium mb-3">Choose Avatar</label>
                    <div className="flex gap-2">
                       {[1, 2, 3, 4, 5].map(i => (
                          <div 
                             key={i} 
                             onClick={() => setEditAvatar(`/avatars/avatar${i}.svg`)}
                             className={`cursor-pointer border-4 rounded-full p-1 ${editAvatar === `/avatars/avatar${i}.svg` ? 'border-[var(--primary)]' : 'border-transparent'}`}
                          >
                             <img src={`/avatars/avatar${i}.svg`} alt={`Avatar ${i}`} className="w-12 h-12 rounded-full bg-gray-100" />
                          </div>
                       ))}
                    </div>
                 </div>
          <div>
            <label className="block text-sm font-medium mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. John Doe"
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">About (Optional)</label>
            <input
              type="text"
              value={about}
              onChange={(e) => setAbout(e.target.value)}
              placeholder="Available"
              className="input-field"
            />
          </div>
          <button type="submit" disabled={loading || !displayName} className="btn-primary w-full mt-6">
            {loading ? "Saving..." : "Start Messaging"}
          </button>
        </form>
      </div>
    </div>
  );
}
