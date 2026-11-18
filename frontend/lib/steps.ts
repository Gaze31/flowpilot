// The settings each step type reads, taken from backend/app/engine/nodes/*.py
// required = the backend reads it with config["key"], so a missing value crashes the step.

export type Field = {
  key: string;
  label: string;
  kind: "text" | "textarea" | "number" | "json" | "select";
  required?: boolean;
  placeholder?: string;
  options?: string[];
};

export const STEP_FIELDS: Record<string, Field[]> = {
  "trigger.manual": [
    { key: "payload", label: "Test data (JSON)", kind: "json", placeholder: '{"emails": ["..."]}' },
  ],
  "trigger.schedule": [
    { key: "cron", label: "Cron (UTC)", kind: "text", required: true, placeholder: "0 8 * * *" },
  ],
  "llm.prompt": [
    { key: "prompt", label: "Prompt", kind: "textarea", required: true, placeholder: "Summarise {{n1.output.payload}}" },
    { key: "max_tokens", label: "Max tokens", kind: "number", placeholder: "500" },
    { key: "output_schema", label: "Output schema (JSON)", kind: "json", placeholder: '{"urgent": "list[str]"}' },
  ],
  "action.http": [
    { key: "url", label: "URL", kind: "text", required: true, placeholder: "https://example.com/hook" },
    { key: "method", label: "Method", kind: "select", options: ["GET", "POST", "PUT", "PATCH", "DELETE"] },
    { key: "json", label: "JSON body", kind: "json", placeholder: '{"text": "{{n2.output.text}}"}' },
  ],
  "action.email": [
    { key: "to", label: "To", kind: "text", required: true, placeholder: "me@example.com" },
    { key: "subject", label: "Subject", kind: "text" },
    { key: "body", label: "Body", kind: "textarea" },
  ],
};

export function missingFields(stepType: string, config: Record<string, unknown>): string[] {
  const fields = STEP_FIELDS[stepType] ?? [];
  return fields
    .filter((f) => f.required && (config[f.key] === undefined || config[f.key] === ""))
    .map((f) => f.label);
}