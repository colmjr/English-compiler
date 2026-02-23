import { useCallback, useState } from "react";
import {
  getStoredSettings,
  LLMSettings,
  PROVIDERS,
  Provider,
} from "../components/SettingsModal";

// System prompt for Core IL generation
const SYSTEM_PROMPT = `You are a compiler frontend. Output only Core IL JSON (v1.7) matching the provided schema.
No prose, no markdown, no code fences.

=== CRITICAL RULES ===

1. Core IL v1.7 is a CLOSED specification. Use ONLY the primitives listed below.
2. DO NOT invent helper functions. Common mistakes to avoid:
   - NO "get_or_default" → use GetDefault
   - NO "keys" → use Keys
   - NO "append" → use Push
   - NO "contains"/"has" → use SetHas
   - NO "enqueue"/"dequeue" → use PushBack/PopFront
   - NO "heappush"/"heappop"/"insert"/"extract_min" → use HeapPush/HeapPop
3. DO NOT use dot notation like "point.x" → use GetField/SetField for Core IL Records
4. PopFront, PopBack, and HeapPop are STATEMENTS with "target" field, not expressions

=== AVAILABLE CONSTRUCTS ===

Statements: Let, Assign, If, While, For, ForEach, Print, SetIndex, Set, Push, SetField, SetAdd, SetRemove, PushBack, PushFront, PopFront, PopBack, HeapPush, HeapPop, FuncDef, Return, Break, Continue

Expressions: Literal, Var, Binary, Array, Index, Length, Range, Map, Get, GetDefault, Keys, Tuple, Record, GetField, StringLength, Substring, CharAt, Join, StringSplit, StringTrim, StringUpper, StringLower, StringStartsWith, StringEndsWith, StringContains, StringReplace, Set (literal), SetHas, SetSize, DequeNew, DequeSize, HeapNew, HeapSize, HeapPeek, Math, MathPow, MathConst, JsonParse, JsonStringify, RegexMatch, RegexFindAll, RegexReplace, RegexSplit, Call

=== LOOPS ===

For numeric ranges:
  {"type": "For", "var": "i", "iter": {"type": "Range", "from": 0, "to": 10, "inclusive": false}, "body": [...]}

For arrays/collections:
  {"type": "ForEach", "var": "x", "iter": <array_expr>, "body": [...]}

=== ARRAY OPERATIONS ===

Create: {"type": "Array", "items": [<expr>, ...]}
Get element: {"type": "Index", "base": <array>, "index": <int_expr>}
Get length: {"type": "Length", "base": <array>}
Append: {"type": "Push", "base": <array>, "value": <expr>}
Set element: {"type": "SetIndex", "base": <array>, "index": <int_expr>, "value": <expr>}

=== MAP OPERATIONS ===

Create: {"type": "Map", "items": [{"key": <expr>, "value": <expr>}, ...]}
Get value: {"type": "Get", "base": <map>, "key": <key>}
Get with default: {"type": "GetDefault", "base": <map>, "key": <key>, "default": <default_value>}
Get all keys: {"type": "Keys", "base": <map>}
Set value: {"type": "Set", "base": <map>, "key": <key>, "value": <val>}

=== STRING OPERATIONS ===

Get length: {"type": "StringLength", "base": <string>}
Substring (end-exclusive): {"type": "Substring", "base": <string>, "start": <int>, "end": <int>}
Get character: {"type": "CharAt", "base": <string>, "index": <int>}
Join array: {"type": "Join", "sep": <string>, "items": <array>}

=== MATH OPERATIONS ===

Unary functions: {"type": "Math", "op": "sin|cos|tan|sqrt|floor|ceil|abs|log|exp", "arg": <expr>}
Power: {"type": "MathPow", "base": <expr>, "exponent": <expr>}
Constants: {"type": "MathConst", "name": "pi|e"}

=== PRINT ===

Print takes an array of expressions (NOT a single "value" field!):
  {"type": "Print", "args": [<expr>, <expr>, ...]}

Example - print "hello":
  {"type": "Print", "args": [{"type": "Literal", "value": "hello"}]}

Example - print result of 1+1:
  {"type": "Print", "args": [{"type": "Binary", "op": "+", "left": {"type": "Literal", "value": 1}, "right": {"type": "Literal", "value": 1}}]}

=== VERSION ===

Use "coreil-1.7" for all programs.`;

export interface CompileResult {
  success: boolean;
  coreIL: string;
  error: string | null;
}

// Extract JSON from response that might have markdown code fences
function extractJSON(text: string): string {
  // Try to extract from code fence
  const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenceMatch) {
    return fenceMatch[1].trim();
  }
  // Return as-is if no code fence
  return text.trim();
}

async function compileWithAnthropic(
  settings: LLMSettings,
  englishText: string,
): Promise<CompileResult> {
  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": settings.apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({
        model: settings.model,
        max_tokens: settings.maxTokens,
        temperature: settings.temperature,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: englishText }],
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg =
        errorData.error?.message || `API error: ${response.status}`;
      return { success: false, coreIL: "", error: errorMsg };
    }

    const data = await response.json();
    const content = extractJSON(data.content?.[0]?.text || "");

    try {
      JSON.parse(content);
      return { success: true, coreIL: content, error: null };
    } catch {
      return {
        success: false,
        coreIL: content,
        error: "LLM returned invalid JSON",
      };
    }
  } catch (err) {
    return {
      success: false,
      coreIL: "",
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

const OPENAI_COMPATIBLE_URLS: Partial<Record<Provider, string>> = {
  openai: "https://api.openai.com/v1/chat/completions",
  groq: "https://api.groq.com/openai/v1/chat/completions",
  together: "https://api.together.xyz/v1/chat/completions",
};

const DIRECT_COMPILERS: Partial<
  Record<
    Provider,
    (settings: LLMSettings, englishText: string) => Promise<CompileResult>
  >
> = {
  anthropic: compileWithAnthropic,
  google: compileWithGoogle,
};

async function compileWithOpenAICompatible(
  url: string,
  settings: LLMSettings,
  englishText: string,
): Promise<CompileResult> {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${settings.apiKey}`,
      },
      body: JSON.stringify({
        model: settings.model,
        max_tokens: settings.maxTokens,
        temperature: settings.temperature,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: englishText },
        ],
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg =
        errorData.error?.message || `API error: ${response.status}`;
      return { success: false, coreIL: "", error: errorMsg };
    }

    const data = await response.json();
    const content = extractJSON(data.choices?.[0]?.message?.content || "");

    try {
      JSON.parse(content);
      return { success: true, coreIL: content, error: null };
    } catch {
      return {
        success: false,
        coreIL: content,
        error: "LLM returned invalid JSON",
      };
    }
  } catch (err) {
    return {
      success: false,
      coreIL: "",
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

async function compileWithGoogle(
  settings: LLMSettings,
  englishText: string,
): Promise<CompileResult> {
  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${settings.model}:generateContent?key=${settings.apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            { parts: [{ text: `${SYSTEM_PROMPT}\n\n${englishText}` }] },
          ],
          generationConfig: {
            temperature: settings.temperature,
            maxOutputTokens: settings.maxTokens,
          },
        }),
      },
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg =
        errorData.error?.message || `API error: ${response.status}`;
      return { success: false, coreIL: "", error: errorMsg };
    }

    const data = await response.json();
    const content = extractJSON(
      data.candidates?.[0]?.content?.parts?.[0]?.text || "",
    );

    try {
      JSON.parse(content);
      return { success: true, coreIL: content, error: null };
    } catch {
      return {
        success: false,
        coreIL: content,
        error: "LLM returned invalid JSON",
      };
    }
  } catch (err) {
    return {
      success: false,
      coreIL: "",
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

export function useCompiler() {
  const [isCompiling, setIsCompiling] = useState(false);

  const compile = useCallback(
    async (englishText: string): Promise<CompileResult> => {
      const settings = getStoredSettings();

      if (!settings.apiKey) {
        const providerName = PROVIDERS[settings.provider].name;
        return {
          success: false,
          coreIL: "",
          error: `No API key configured for ${providerName}. Click the gear icon to add your API key.`,
        };
      }

      if (!englishText.trim()) {
        return {
          success: false,
          coreIL: "",
          error: "Please enter some English text to compile.",
        };
      }

      setIsCompiling(true);

      try {
        const compiler = DIRECT_COMPILERS[settings.provider];
        if (compiler) {
          return await compiler(settings, englishText);
        }

        const url = OPENAI_COMPATIBLE_URLS[settings.provider];
        if (!url) {
          return {
            success: false,
            coreIL: "",
            error: `Unknown provider: ${settings.provider}`,
          };
        }
        return await compileWithOpenAICompatible(url, settings, englishText);
      } finally {
        setIsCompiling(false);
      }
    },
    [],
  );

  const hasApiKey = useCallback(() => {
    return !!getStoredSettings().apiKey;
  }, []);

  return {
    compile,
    isCompiling,
    hasApiKey,
  };
}
