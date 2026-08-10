function normalizeErrorDetail(detail, fallback) {
  if (typeof detail === 'string' && detail.trim()) {
    return detail.replace(/^Value error,\s*/i, '');
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (!item || typeof item !== 'object') return '';

        const message = item.msg || item.message || item.detail;
        return typeof message === 'string'
          ? message.replace(/^Value error,\s*/i, '')
          : '';
      })
      .filter(Boolean);

    if (messages.length) return messages.join(' ');
  }

  if (detail && typeof detail === 'object') {
    const message = detail.msg || detail.message || detail.detail;
    if (typeof message === 'string' && message.trim()) {
      return message.replace(/^Value error,\s*/i, '');
    }
  }

  return fallback;
}

async function responseErrorMessage(response) {
  const fallback = `Request failed with HTTP ${response.status}.`;

  try {
    const payload = await response.json();
    return normalizeErrorDetail(payload.detail ?? payload.error, fallback);
  } catch {
    return fallback;
  }
}

export async function getJson(path, { signal } = {}) {
  const response = await fetch(path, {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response));
  }

  return response.json();
}

export function buildQuery(parameters) {
  const query = new URLSearchParams();
  Object.entries(parameters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      query.set(key, String(value));
    }
  });
  const encoded = query.toString();
  return encoded ? `?${encoded}` : '';
}

export async function postJson(path, payload, { signal } = {}) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response));
  }

  return response.json();
}

export async function patchJson(path, payload, { signal } = {}) {
  const response = await fetch(path, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response));
  }

  return response.json();
}

export async function putJson(path, payload, { signal } = {}) {
  const response = await fetch(path, {
    method: 'PUT',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response));
  }

  return response.json();
}
