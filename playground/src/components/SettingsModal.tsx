import { useState, useEffect } from "react";

export type Provider = "anthropic" | "openai" | "google" | "groq" | "together";

export interface ProviderConfig {
  name: string;
  models: { id: string; name: string }[];
  defaultModel: string;
  apiKeyPlaceholder: string;
  apiKeyPrefix: string;
}

export const PROVIDERS: Record<Provider, ProviderConfig> = {
  anthropic: {
    name: "Anthropic",
    models: [
      { id: "claude-sonnet-4-20250514", name: "Claude Sonnet 4" },
      { id: "claude-opus-4-20250514", name: "Claude Opus 4" },
      { id: "claude-3-5-sonnet-20241022", name: "Claude 3.5 Sonnet" },
      { id: "claude-3-5-haiku-20241022", name: "Claude 3.5 Haiku" },
    ],
    defaultModel: "claude-sonnet-4-20250514",
    apiKeyPlaceholder: "sk-ant-...",
    apiKeyPrefix: "sk-ant-",
  },
  openai: {
    name: "OpenAI",
    models: [
      { id: "gpt-4o", name: "GPT-4o" },
      { id: "gpt-4o-mini", name: "GPT-4o Mini" },
      { id: "gpt-4-turbo", name: "GPT-4 Turbo" },
      { id: "o1", name: "o1" },
      { id: "o1-mini", name: "o1 Mini" },
    ],
    defaultModel: "gpt-4o",
    apiKeyPlaceholder: "sk-...",
    apiKeyPrefix: "sk-",
  },
  google: {
    name: "Google AI",
    models: [
      { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash" },
      { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro" },
      { id: "gemini-1.5-flash", name: "Gemini 1.5 Flash" },
    ],
    defaultModel: "gemini-2.0-flash",
    apiKeyPlaceholder: "AIza...",
    apiKeyPrefix: "AIza",
  },
  groq: {
    name: "Groq",
    models: [
      { id: "llama-3.3-70b-versatile", name: "Llama 3.3 70B" },
      { id: "llama-3.1-8b-instant", name: "Llama 3.1 8B" },
      { id: "mixtral-8x7b-32768", name: "Mixtral 8x7B" },
      { id: "gemma2-9b-it", name: "Gemma 2 9B" },
    ],
    defaultModel: "llama-3.3-70b-versatile",
    apiKeyPlaceholder: "gsk_...",
    apiKeyPrefix: "gsk_",
  },
  together: {
    name: "Together AI",
    models: [
      {
        id: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        name: "Llama 3.3 70B Turbo",
      },
      {
        id: "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        name: "Llama 3.1 405B Turbo",
      },
      { id: "mistralai/Mixtral-8x22B-Instruct-v0.1", name: "Mixtral 8x22B" },
      { id: "Qwen/Qwen2.5-72B-Instruct-Turbo", name: "Qwen 2.5 72B" },
      {
        id: "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        name: "DeepSeek R1 70B",
      },
    ],
    defaultModel: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    apiKeyPlaceholder: "",
    apiKeyPrefix: "",
  },
};

export interface LLMSettings {
  provider: Provider;
  apiKey: string;
  model: string;
  temperature: number;
  maxTokens: number;
}

const STORAGE_KEY = "english-compiler-settings";
const MIN_TEMPERATURE = 0;
const MAX_TEMPERATURE = 1;
const MIN_MAX_TOKENS = 1024;
const MAX_MAX_TOKENS = 8192;
const MAX_TOKENS_STEP = 1024;

const DEFAULT_SETTINGS: LLMSettings = {
  provider: "anthropic",
  apiKey: "",
  model: PROVIDERS.anthropic.defaultModel,
  temperature: 0,
  maxTokens: 4096,
};

function isProvider(value: unknown): value is Provider {
  return typeof value === "string" && value in PROVIDERS;
}

function clampNumber(
  value: unknown,
  min: number,
  max: number,
  fallback: number,
): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, value));
}

function normalizeMaxTokens(value: unknown): number {
  const clamped = clampNumber(
    value,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
    DEFAULT_SETTINGS.maxTokens,
  );
  return Math.round(clamped / MAX_TOKENS_STEP) * MAX_TOKENS_STEP;
}

function normalizeString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function normalizeSettings(value: unknown): LLMSettings {
  const parsed = (
    value && typeof value === "object" ? value : {}
  ) as Partial<LLMSettings>;
  const provider = isProvider(parsed.provider)
    ? parsed.provider
    : DEFAULT_SETTINGS.provider;
  const defaultModel = PROVIDERS[provider].defaultModel;
  const model = normalizeString(parsed.model, defaultModel);

  return {
    provider,
    apiKey: normalizeString(parsed.apiKey),
    model: model.trim() ? model : defaultModel,
    temperature: clampNumber(
      parsed.temperature,
      MIN_TEMPERATURE,
      MAX_TEMPERATURE,
      DEFAULT_SETTINGS.temperature,
    ),
    maxTokens: normalizeMaxTokens(parsed.maxTokens),
  };
}

export function getStoredSettings(): LLMSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return normalizeSettings(parsed);
    }
  } catch {
    // Ignore parse errors
  }
  return { ...DEFAULT_SETTINGS };
}

export function saveSettings(settings: LLMSettings): void {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(normalizeSettings(settings)),
  );
}

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [settings, setSettings] = useState<LLMSettings>(DEFAULT_SETTINGS);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setSettings(getStoredSettings());
    }
  }, [isOpen]);

  const handleProviderChange = (provider: Provider) => {
    setSettings((prev) => ({
      ...prev,
      provider,
      model: PROVIDERS[provider].defaultModel,
    }));
  };

  const handleSave = () => {
    saveSettings(settings);
    onClose();
  };

  const handleClear = () => {
    localStorage.removeItem(STORAGE_KEY);
    setSettings({ ...DEFAULT_SETTINGS });
  };

  if (!isOpen) return null;

  const currentProvider = PROVIDERS[settings.provider];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="modal-close" onClick={onClose}>
            &times;
          </button>
        </div>
        <div className="modal-body">
          {/* Provider Selection */}
          <div className="form-group">
            <label>LLM Provider</label>
            <select
              value={settings.provider}
              onChange={(e) => handleProviderChange(e.target.value as Provider)}
              className="form-select"
            >
              {Object.entries(PROVIDERS).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.name}
                </option>
              ))}
            </select>
          </div>

          {/* API Key */}
          <div className="form-group">
            <label>{currentProvider.name} API Key</label>
            <div className="input-with-button">
              <input
                type={showKey ? "text" : "password"}
                value={settings.apiKey}
                onChange={(e) =>
                  setSettings((prev) => ({ ...prev, apiKey: e.target.value }))
                }
                placeholder={currentProvider.apiKeyPlaceholder}
                className="form-input"
              />
              <button
                className="secondary"
                onClick={() => setShowKey(!showKey)}
                type="button"
              >
                {showKey ? "Hide" : "Show"}
              </button>
            </div>
            <p className="form-hint">
              Your API key is stored locally and sent directly to{" "}
              {currentProvider.name}'s API.
            </p>
          </div>

          {/* Model Selection */}
          <div className="form-group">
            <label>Model</label>
            <select
              value={settings.model}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, model: e.target.value }))
              }
              className="form-select"
            >
              {currentProvider.models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          {/* Advanced Settings */}
          <details className="settings-advanced">
            <summary>Advanced Settings</summary>
            <div className="settings-advanced-content">
              {/* Temperature */}
              <div className="form-group">
                <label>Temperature: {settings.temperature.toFixed(1)}</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={settings.temperature}
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      temperature: parseFloat(e.target.value),
                    }))
                  }
                  className="form-range"
                />
                <p className="form-hint">
                  Lower = more deterministic, Higher = more creative. Use 0 for
                  consistent compilation.
                </p>
              </div>

              {/* Max Tokens */}
              <div className="form-group">
                <label>Max Tokens: {settings.maxTokens}</label>
                <input
                  type="range"
                  min="1024"
                  max="8192"
                  step="1024"
                  value={settings.maxTokens}
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      maxTokens: parseInt(e.target.value, 10),
                    }))
                  }
                  className="form-range"
                />
                <p className="form-hint">
                  Maximum length of the generated Core IL output.
                </p>
              </div>

              {/* Custom Model ID */}
              <div className="form-group">
                <label>Custom Model ID (optional)</label>
                <input
                  type="text"
                  value={settings.model}
                  onChange={(e) =>
                    setSettings((prev) => ({ ...prev, model: e.target.value }))
                  }
                  placeholder="Enter custom model ID"
                  className="form-input"
                />
                <p className="form-hint">
                  Override the model dropdown with a custom model ID.
                </p>
              </div>
            </div>
          </details>
        </div>
        <div className="modal-footer">
          <button className="secondary" onClick={handleClear}>
            Reset
          </button>
          <button className="primary" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
