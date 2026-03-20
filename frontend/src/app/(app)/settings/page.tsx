"use client";

import { SettingsForm } from "@/components/settings/settings-form";

export default function SettingsPage() {
  return (
    <div className="p-6">
      <h2 className="text-lg font-bold mb-4">Settings</h2>
      <SettingsForm />
    </div>
  );
}
