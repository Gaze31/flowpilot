"use client";

import { useState } from "react";

import { STEP_FIELDS, type Field } from "@/lib/steps";
import { STEP_STYLES } from "./StepNode";

type Config = Record<string, unknown>;

type Props = {
  stepId: string;
  stepType: string;
  config: Config;
  onChange: (config: Config) => void;
};

export function SettingsPanel({ stepId, stepType, config, onChange }: Props) {
  const fields = STEP_FIELDS[stepType] ?? [];
  const label = STEP_STYLES[stepType]?.label ?? stepType;

  function setValue(key: string, value: unknown) {
    const next = { ...config };
    if (value === undefined || value === "") {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange(next);
  }

  return (
    <aside className="w-80 shrink-0 overflow-y-auto border-l border-zinc-800 bg-zinc-950 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Settings</p>
      <h2 className="mb-4 mt-1 text-base font-semibold text-zinc-100">
        {label} <span className="text-zinc-500">{stepId}</span>
      </h2>
      <div className="flex flex-col gap-4">
        {fields.map((field) => (
          <label key={field.key} className="block">
            <span className="mb-1 block text-xs font-medium text-zinc-400">
              {field.label}
              {field.required && <span className="text-orange-500"> *</span>}
            </span>
            <FieldInput field={field} value={config[field.key]} onChange={(v) => setValue(field.key, v)} />
          </label>
        ))}
      </div>
    </aside>
  );
}

const INPUT_CLASS =
  "w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-orange-500 focus:outline-none";

function FieldInput({ field, value, onChange }: { field: Field; value: unknown; onChange: (v: unknown) => void }) {
  if (field.kind === "textarea") {
    return (
      <textarea
        rows={4}
        className={INPUT_CLASS}
        placeholder={field.placeholder}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (field.kind === "number") {
    return (
      <input
        type="number"
        className={INPUT_CLASS}
        placeholder={field.placeholder}
        value={value === undefined ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
      />
    );
  }

  if (field.kind === "select") {
    return (
      <select className={INPUT_CLASS} value={String(value ?? field.options?.[0] ?? "")} onChange={(e) => onChange(e.target.value)}>
        {field.options?.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  if (field.kind === "json") {
    return <JsonInput value={value} placeholder={field.placeholder} onChange={onChange} />;
  }

  return (
    <input
      type="text"
      className={INPUT_CLASS}
      placeholder={field.placeholder}
      value={String(value ?? "")}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function JsonInput({ value, placeholder, onChange }: { value: unknown; placeholder?: string; onChange: (v: unknown) => void }) {
  const [text, setText] = useState(value === undefined ? "" : JSON.stringify(value, null, 2));
  const [error, setError] = useState("");

  function handleChange(newText: string) {
    setText(newText);
    if (newText.trim() === "") {
      setError("");
      onChange(undefined);
      return;
    }
    try {
      onChange(JSON.parse(newText));
      setError("");
    } catch {
      setError("Not valid JSON yet. The last valid version is kept.");
    }
  }

  return (
    <>
      <textarea
        rows={6}
        className={INPUT_CLASS + " font-mono text-xs"}
        placeholder={placeholder}
        value={text}
        onChange={(e) => handleChange(e.target.value)}
      />
      {error && <span className="mt-1 block text-xs text-red-400">{error}</span>}
    </>
  );
}