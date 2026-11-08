/**
 * TracePilot API client service.
 * Connects frontend components to the backend REST and SSE streaming endpoints.
 */

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchExamples() {
  const res = await fetch(`${API_BASE}/examples`);
  if (!res.ok) {
    throw new Error(`Failed to load preset examples: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchEvaluation() {
  const res = await fetch(`${API_BASE}/evaluation`);
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation metrics: ${res.statusText}`);
  }
  return res.json();
}

export async function submitDebugRequest({ errorText, language = 'auto', structured = true }) {
  const res = await fetch(`${API_BASE}/debug`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      error_text: errorText,
      programming_language: language === 'auto' ? null : language,
      structured,
    }),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || `Debugging analysis failed (${res.status})`);
  }

  return data;
}

export async function streamDebugRequest({
  errorText,
  language = 'auto',
  structured = true,
  onChunk,
  onCompleted,
  onError,
}) {
  try {
    const res = await fetch(`${API_BASE}/debug/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        error_text: errorText,
        programming_language: language === 'auto' ? null : language,
        structured,
        stream: true,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Stream connection failed: ${res.statusText}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop(); // keep remainder for next cycle

      for (const frame of frames) {
        if (!frame.trim()) continue;

        let eventType = 'message';
        let dataStr = '';

        const lines = frame.split('\n');
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.replace('event: ', '').trim();
          } else if (line.startsWith('data: ')) {
            dataStr = line.replace('data: ', '').trim();
          }
        }

        if (dataStr) {
          try {
            const parsedData = JSON.parse(dataStr);
            if (eventType === 'text_chunk') {
              if (onChunk && parsedData.delta) onChunk(parsedData.delta);
            } else if (eventType === 'completed') {
              if (onCompleted) onCompleted(parsedData);
            } else if (eventType === 'failed') {
              if (onError) onError(new Error(parsedData.error || 'Streaming generation failed'));
            }
          } catch {
            // raw string fallback
            if (eventType === 'text_chunk' && onChunk) onChunk(dataStr);
          }
        }
      }
    }
  } catch (err) {
    if (onError) onError(err);
  }
}

